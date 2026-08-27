#!/usr/bin/env Rscript
#
# Estimate a preference network per dataset with bootEGA (EGAnet).
#
# Why this is precomputed rather than fitted in the browser: bootEGA resamples
# the network hundreds of times, which is seconds of compute per dataset and
# not something to ask a visitor's laptop for. Results are written as JSON,
# served by the API, and drawn by the site's own network canvas.
#
# WHICH ITEMS. A Gaussian graphical model over items needs more subjects than
# items. In this database 41 of 55 datasets have the opposite -- more items
# than subjects -- so fitting every item is not possible and pretending
# otherwise would produce a network estimated from a singular correlation
# matrix. Each dataset is therefore reduced to the items that are
#
#   1. replicated across studies (present in >= MIN_ITEM_FREQ datasets), so
#      the networks mean the same thing from one dataset to the next, and
#   2. completely observed for the subjects retained, and
#   3. capped at n/SUBJECT_ITEM_RATIO items, most-replicated first.
#
# That is a real restriction on what the figure shows, and the JSON records
# it so the interface can say so.
#
# Usage:
#   Rscript scripts/estimate_networks.R [--out DIR] [--boot N] [--only CODE]

suppressMessages({
  library(EGAnet)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
get_arg <- function(flag, default) {
  i <- match(flag, args)
  if (is.na(i) || i == length(args)) default else args[i + 1]
}

OUT_DIR   <- get_arg("--out", "release/networks")
BOOT      <- as.integer(get_arg("--boot", "500"))
ONLY      <- get_arg("--only", NA)
MATRIX_DIR <- get_arg("--matrices", "build/ega-matrices")

MIN_ITEM_FREQ       <- 10   # item must appear in at least this many datasets
SUBJECT_ITEM_RATIO  <- 2    # keep subjects >= 2 x items
MIN_ITEMS           <- 5
MIN_SUBJECTS        <- 15
SEED                <- 42

dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

files <- list.files(MATRIX_DIR, pattern = "csv$", full.names = TRUE)
if (!length(files)) stop("no matrices in ", MATRIX_DIR, " -- run scripts/export_ega_matrices.py first")
if (!is.na(ONLY)) files <- files[basename(files) == paste0(ONLY, ".csv")]

summary_rows <- list()

for (f in files) {
  code <- sub(".csv$", "", basename(f))
  raw <- read.csv(f, check.names = FALSE)

  # Columns are named "<item_id>|<item_name>|<frequency>" by the exporter.
  meta <- do.call(rbind, strsplit(colnames(raw), "|", fixed = TRUE))
  item_id   <- meta[, 1]
  item_name <- meta[, 2]
  item_freq <- as.integer(meta[, 3])

  n_all <- nrow(raw); p_all <- ncol(raw)
  status <- NA_character_

  keep <- which(item_freq >= MIN_ITEM_FREQ)
  # most-replicated first, so the retained set is the most comparable one
  keep <- keep[order(item_freq[keep], decreasing = TRUE)]
  cap <- floor(n_all / SUBJECT_ITEM_RATIO)
  if (length(keep) > cap) keep <- keep[seq_len(cap)]

  if (length(keep) < MIN_ITEMS) {
    status <- sprintf("only %d items are replicated across >= %d datasets",
                      length(keep), MIN_ITEM_FREQ)
  } else {
    sub <- raw[, keep, drop = FALSE]
    sub <- sub[complete.cases(sub), , drop = FALSE]
    if (nrow(sub) < MIN_SUBJECTS) {
      status <- sprintf("only %d subjects rated all %d retained items",
                        nrow(sub), ncol(sub))
    } else if (nrow(sub) < SUBJECT_ITEM_RATIO * ncol(sub)) {
      # trim further so the ratio holds after dropping incomplete rows
      cap2 <- floor(nrow(sub) / SUBJECT_ITEM_RATIO)
      if (cap2 < MIN_ITEMS) {
        status <- sprintf("%d complete subjects cannot support %d items",
                          nrow(sub), MIN_ITEMS)
      } else {
        sub <- sub[, seq_len(cap2), drop = FALSE]
        sub <- sub[complete.cases(sub), , drop = FALSE]
      }
    }
  }

  if (!is.na(status)) {
    summary_rows[[code]] <- list(dataset_code = code, estimated = FALSE,
                                 reason = status, n_subjects = n_all, n_items_total = p_all)
    write_json(summary_rows[[code]], file.path(OUT_DIR, paste0(code, ".json")),
               auto_unbox = TRUE, digits = 6)
    cat(sprintf("%-22s skipped  %s\n", code, status))
    next
  }

  kept_idx <- keep[seq_len(ncol(sub))]
  fit <- try(suppressWarnings(
    bootEGA(data = sub, iter = BOOT, type = "resampling", seed = SEED,
            plot.itemStability = FALSE, plot.typicalStructure = FALSE,
            verbose = FALSE)
  ), silent = TRUE)

  if (inherits(fit, "try-error")) {
    reason <- trimws(gsub("\\s+", " ", as.character(fit)))
    summary_rows[[code]] <- list(dataset_code = code, estimated = FALSE,
                                 reason = paste("bootEGA failed:", substr(reason, 1, 160)),
                                 n_subjects = nrow(sub), n_items_total = p_all)
    write_json(summary_rows[[code]], file.path(OUT_DIR, paste0(code, ".json")),
               auto_unbox = TRUE, digits = 6)
    cat(sprintf("%-22s FAILED\n", code))
    next
  }

  # Empirical network and communities from the bootstrap object
  net <- fit$EGA$network
  wc  <- fit$EGA$wc
  stab <- try(suppressWarnings(itemStability(fit, plot.itemStability = FALSE)), silent = TRUE)
  item_stab <- rep(NA_real_, ncol(sub))
  if (!inherits(stab, "try-error")) {
    s <- stab$item.stability$empirical.dimensions
    if (!is.null(s)) item_stab <- as.numeric(s[colnames(sub)])
  }

  idx <- which(upper.tri(net) & net != 0, arr.ind = TRUE)
  edges <- if (nrow(idx)) lapply(seq_len(nrow(idx)), function(k) {
    list(source = unname(item_name[kept_idx[idx[k, 1]]]),
         target = unname(item_name[kept_idx[idx[k, 2]]]),
         weight = unname(net[idx[k, 1], idx[k, 2]]))
  }) else list()

  nodes <- lapply(seq_len(ncol(sub)), function(k) {
    list(id = unname(item_id[kept_idx[k]]),
         label = unname(item_name[kept_idx[k]]),
         community = unname(as.integer(wc[k])),
         stability = unname(item_stab[k]),
         mean_rating = unname(mean(sub[[k]], na.rm = TRUE)),
         n_datasets = unname(item_freq[kept_idx[k]]))
  })

  out <- list(
    dataset_code = code,
    estimated = TRUE,
    method = list(
      algorithm = "bootEGA (EGAnet)", model = "glasso", type = "resampling",
      iterations = BOOT, seed = SEED, community_detection = "walktrap"
    ),
    selection = list(
      min_item_frequency = MIN_ITEM_FREQ,
      subject_item_ratio = SUBJECT_ITEM_RATIO,
      items_in_dataset = p_all,
      items_estimated = ncol(sub),
      subjects_in_dataset = n_all,
      subjects_complete = nrow(sub)
    ),
    n_dimensions = unname(fit$EGA$n.dim),
    nodes = nodes,
    edges = edges
  )
  write_json(out, file.path(OUT_DIR, paste0(code, ".json")),
             auto_unbox = TRUE, digits = 6, na = "null")
  summary_rows[[code]] <- out
  cat(sprintf("%-22s ok  n=%-4d p=%-3d dims=%-3s edges=%-4d\n",
              code, nrow(sub), ncol(sub), fit$EGA$n.dim, length(edges)))
}

est <- sum(vapply(summary_rows, function(x) isTRUE(x$estimated), logical(1)))
cat(sprintf("\nestimated %d of %d datasets -> %s\n", est, length(summary_rows), OUT_DIR))
