#!/usr/bin/env Rscript
#
# Estimate a preference network per dataset with EGAnet.
#
# The workflow is EGAnet's own, in the order the package intends:
#
#   1. bootEGA() on the dataset
#   2. itemStability() -- how often each item returns to its empirical
#      dimension across bootstraps
#   3. keep only items at or above STABILITY_CUTOFF, drop the rest
#   4. bootEGA() again on the retained items
#   5. dimensionStability() on that refit, for structural consistency
#
# Selection is therefore made by the data, not by us: an item survives if its
# placement replicates, which is what "robust" means here.
#
# Precomputed rather than fitted in the browser: two rounds of several hundred
# bootstraps is seconds of compute per dataset, and all results together are
# well under a megabyte, so shipping them beats refitting on every page view.
#
# ONE THING THE WORKFLOW CANNOT FIX. A graphical model over items needs more
# subjects than items, and most datasets here have the opposite. Where that
# holds, step 1 cannot run at all, so there is no stability to measure. Those
# datasets are cut to their most completely observed items purely so a first
# fit exists -- a feasibility cap, recorded separately from the stability
# selection so the two are never confused.
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

OUT_DIR    <- get_arg("--out", "build/networks")
BOOT       <- as.integer(get_arg("--boot", "500"))
ONLY       <- get_arg("--only", NA)
MATRIX_DIR <- get_arg("--matrices", "build/ega-matrices")

STABILITY_CUTOFF   <- 0.45   # loosened from EGAnet's documented 0.70-0.75
                             # to give every dataset a chance at a network;
                             # the cutoff travels with the result so the
                             # page can say what it was.
SUBJECT_ITEM_RATIO <- 2      # feasibility only: subjects >= 2 x items
MIN_ITEMS          <- 5
MIN_SUBJECTS       <- 15
SEED               <- 42

dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

files <- list.files(MATRIX_DIR, pattern = "csv$", full.names = TRUE)
if (!length(files)) stop("no matrices in ", MATRIX_DIR)
if (!is.na(ONLY)) files <- files[basename(files) == paste0(ONLY, ".csv")]

write_skip <- function(code, reason, extra = list()) {
  out <- c(list(dataset_code = code, estimated = FALSE, reason = reason), extra)
  write_json(out, file.path(OUT_DIR, paste0(code, ".json")),
             auto_unbox = TRUE, digits = 6, na = "null")
  cat(sprintf("%-22s skipped  %s\n", code, reason))
}

run_boot <- function(d) {
  try(suppressWarnings(
    bootEGA(data = d, iter = BOOT, type = "resampling", seed = SEED,
            plot.itemStability = FALSE, plot.typicalStructure = FALSE,
            verbose = FALSE)
  ), silent = TRUE)
}

n_ok <- 0
for (f in files) {
  code <- sub(".csv$", "", basename(f))
  # Already estimated? leave it alone, so an interrupted sweep can resume.
  if (file.exists(file.path(OUT_DIR, paste0(code, ".json")))) {
    cat(sprintf("%-22s (already present)\n", code)); next
  }
  estimate_one <- function() {
  raw <- read.csv(f, check.names = FALSE)
  meta <- do.call(rbind, strsplit(colnames(raw), "|", fixed = TRUE))
  item_id <- meta[, 1]; item_name <- meta[, 2]; item_freq <- as.integer(meta[, 3])
  n_all <- nrow(raw); p_all <- ncol(raw)

  # Choose items and subjects together. Taking the most-complete items and
  # then dropping incomplete rows is the wrong order: it can leave a single
  # subject who happened to rate all of them. Instead grow the item set in
  # order of completeness and keep the largest block that still has twice as
  # many complete subjects as items. Adding an item can only reduce the
  # complete-case count, so the first infeasible size ends the search.
  cols <- seq_len(ncol(raw))
  feasibility_capped <- FALSE
  full_n <- sum(complete.cases(raw))

  if (ncol(raw) >= MIN_ITEMS && full_n >= SUBJECT_ITEM_RATIO * ncol(raw)) {
    d0 <- raw[complete.cases(raw), , drop = FALSE]
  } else {
    # Every extra item costs subjects, because a subject is only usable if
    # they rated all of the retained items. Rather than taking the largest
    # feasible item set -- which spends subjects freely -- take the one that
    # retains the most ratings overall (subjects x items), and break ties
    # toward more subjects. That keeps as many people in the estimate as the
    # data allows instead of trading them away for extra items.
    ordering <- order(colSums(!is.na(raw)), decreasing = TRUE)
    best <- NULL; best_score <- -1
    for (k in seq(MIN_ITEMS, ncol(raw))) {
      cand <- ordering[seq_len(k)]
      keep_rows <- complete.cases(raw[, cand, drop = FALSE])
      n_k <- sum(keep_rows)
      if (n_k < MIN_SUBJECTS) break          # only gets worse from here
      if (n_k >= SUBJECT_ITEM_RATIO * k) {
        score <- n_k * k
        if (score > best_score || (score == best_score && n_k > best$n)) {
          best <- list(cols = cand, rows = keep_rows, p = k, n = n_k)
          best_score <- score
        }
      }
    }
    if (is.null(best)) {
      d0 <- raw[complete.cases(raw), , drop = FALSE]
    } else {
      cols <- best$cols
      d0 <- raw[best$rows, best$cols, drop = FALSE]
      feasibility_capped <- TRUE
    }
  }

  if (ncol(d0) < MIN_ITEMS || nrow(d0) < MIN_SUBJECTS ||
      nrow(d0) < SUBJECT_ITEM_RATIO * ncol(d0)) {
    write_skip(code, sprintf(
      "a network over items needs more subjects than items; %d subjects rated %d items in common",
      nrow(d0), ncol(d0)),
      list(n_subjects = n_all, n_items_total = p_all))
    return(FALSE)
  }

  # --- step 1: bootEGA on everything estimable --------------------------
  first <- run_boot(d0)
  if (inherits(first, "try-error")) {
    write_skip(code, paste("bootEGA failed:", substr(trimws(gsub("\\s+", " ",
      as.character(first))), 1, 140)), list(n_subjects = nrow(d0), n_items_total = p_all))
    return(FALSE)
  }

  # --- step 2: how often each item returns to its dimension -------------
  is1 <- try(suppressWarnings(itemStability(first, plot.itemStability = FALSE)), silent = TRUE)
  if (inherits(is1, "try-error") || is.null(is1$item.stability$empirical.dimensions)) {
    write_skip(code, "item stability could not be computed (no dimensions were recovered)",
               list(n_subjects = nrow(d0), n_items_total = p_all))
    return(FALSE)
  }
  stab1 <- is1$item.stability$empirical.dimensions

  # --- step 3: keep only the stable items -------------------------------
  # itemStability can return NA for an item that never landed in a dimension;
  # NA here becomes an NA column name and takes the whole run down.
  stable <- names(stab1)[!is.na(stab1) & stab1 >= STABILITY_CUTOFF]
  stable <- intersect(stable, colnames(d0))
  dropped <- setdiff(colnames(d0), stable)
  if (length(stable) < MIN_ITEMS) {
    write_skip(code, sprintf(
      "only %d of %d items reached the %.2f stability cutoff",
      length(stable), ncol(d0), STABILITY_CUTOFF),
      list(n_subjects = nrow(d0), n_items_total = p_all,
           items_tested = ncol(d0), items_stable = length(stable)))
    return(FALSE)
  }
  d1 <- d0[, stable, drop = FALSE]

  # --- step 4: refit on the retained items ------------------------------
  final <- run_boot(d1)
  if (inherits(final, "try-error")) {
    write_skip(code, paste("refit on stable items failed:", substr(trimws(gsub("\\s+", " ",
      as.character(final))), 1, 120)), list(n_subjects = nrow(d1), n_items_total = p_all))
    return(FALSE)
  }
  is2 <- try(suppressWarnings(itemStability(final, plot.itemStability = FALSE)), silent = TRUE)
  stab2 <- if (!inherits(is2, "try-error")) is2$item.stability$empirical.dimensions else NULL

  # --- step 5: dimension stability on the refit -------------------------
  ds <- try(suppressWarnings(dimensionStability(final)), silent = TRUE)
  dims <- NULL
  if (!inherits(ds, "try-error")) {
    sc <- ds$dimension.stability$structural.consistency
    ai <- ds$dimension.stability$average.item.stability
    dims <- lapply(seq_along(sc), function(k) list(
      dimension = as.integer(names(sc)[k]),
      structural_consistency = unname(sc[k]),
      average_item_stability = unname(ai[names(sc)[k]])
    ))
  }

  net <- final$EGA$network
  wc  <- final$EGA$wc
  keep_idx <- cols[match(stable, colnames(d0))]

  idx <- which(upper.tri(net) & net != 0, arr.ind = TRUE)
  edges <- if (nrow(idx)) lapply(seq_len(nrow(idx)), function(k) list(
    source = unname(item_name[keep_idx[idx[k, 1]]]),
    target = unname(item_name[keep_idx[idx[k, 2]]]),
    weight = unname(net[idx[k, 1], idx[k, 2]]))) else list()

  nodes <- lapply(seq_along(stable), function(k) list(
    id = unname(item_id[keep_idx[k]]),
    label = unname(item_name[keep_idx[k]]),
    community = unname(as.integer(wc[k])),
    stability = if (is.null(stab2)) NA_real_ else unname(stab2[stable[k]]),
    stability_before_selection = unname(stab1[stable[k]]),
    mean_rating = unname(mean(d1[[k]], na.rm = TRUE)),
    n_datasets = unname(item_freq[keep_idx[k]])))

  out <- list(
    dataset_code = code,
    estimated = TRUE,
    method = list(
      algorithm = "bootEGA + itemStability (EGAnet)", model = "glasso",
      type = "resampling", iterations = BOOT, seed = SEED,
      community_detection = "walktrap", stability_cutoff = STABILITY_CUTOFF
    ),
    selection = list(
      rule = sprintf("items whose dimension placement replicated in >= %.0f%% of bootstraps",
                     100 * STABILITY_CUTOFF),
      items_in_dataset = p_all,
      items_tested = ncol(d0),
      items_retained = length(stable),
      items_dropped_unstable = length(dropped),
      subjects_in_dataset = n_all,
      subjects_complete = nrow(d1),
      subjects_retained_pct = round(100 * nrow(d1) / n_all, 1),
      feasibility_capped = feasibility_capped
    ),
    # I() keeps a length-1 vector an array; auto_unbox would make it a string
    # and change the shape of the field between datasets.
    dropped_items = I(unname(item_name[cols[match(dropped, colnames(d0))]])),
    n_dimensions = unname(final$EGA$n.dim),
    dimension_stability = dims,
    nodes = nodes,
    edges = edges
  )
  write_json(out, file.path(OUT_DIR, paste0(code, ".json")),
             auto_unbox = TRUE, digits = 6, na = "null")
  cat(sprintf("%-22s ok  tested=%-3d kept=%-3d dropped=%-3d dims=%-3s edges=%d\n",
              code, ncol(d0), length(stable), length(dropped),
              final$EGA$n.dim, length(edges)))
  TRUE
  }
  ok <- tryCatch(estimate_one(), error = function(e) {
    write_skip(code, paste("estimation error:",
      substr(trimws(gsub("\\s+", " ", conditionMessage(e))), 1, 140)))
    FALSE
  })
  if (isTRUE(ok)) n_ok <- n_ok + 1
}

cat(sprintf("\nestimated %d of %d datasets -> %s\n", n_ok, length(files), OUT_DIR))
