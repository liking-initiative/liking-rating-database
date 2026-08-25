#' Download one or more datasets
#'
#' Reads a dataset's ratings from the release, with the metadata needed to
#' interpret them.
#'
#' Two datasets repeat their rating phase — `leeholyoak2021` (phases 1-3) and
#' `leehare2023exp2` (phases 1-2). For those, `subject_id` and `item_id`
#' together are **not** unique; include `timepoint`, or pass the `timepoint`
#' argument to take a single phase.
#'
#' @param dataset A dataset code (`"leeholyoak2021"`), a unique prefix, a
#'   dataset id, or a character vector of them.
#' @param version Release version, or `"latest"`.
#' @param timepoint Optional rating phase to keep.
#' @return An object of class `likingdb_dataset` with elements `data` (a
#'   tibble), `metadata`, `dataset_code` and `version`. For several datasets, a
#'   named list of them.
#' @examples
#' \donttest{
#' d <- get_dataset("leeholyoak2021")
#' head(d$data)
#' d$metadata$rating_scale_max
#' cite(d)
#' }
#' @export
get_dataset <- function(dataset, version = "latest", timepoint = NULL) {
  if (length(dataset) > 1) {
    out <- lapply(dataset, get_dataset, version = version, timepoint = timepoint)
    names(out) <- vapply(out, function(d) d$dataset_code, character(1))
    class(out) <- c("likingdb_dataset_list", "list")
    return(out)
  }

  entry <- dataset_entry(dataset, version)
  data <- readr::read_tsv(
    asset_path(entry$file, version),
    col_types = readr::cols(
      # subject_id is an identifier, not a number: read as numeric, "007"
      # becomes 7 and joins against the rest of the database break.
      subject_id = readr::col_character(),
      item_id = readr::col_character(),
      item_name = readr::col_character(),
      timepoint = readr::col_integer(),
      rating = readr::col_double(),
      normalized_rating = readr::col_double()
    )
  )
  if (!is.null(timepoint)) data <- data[data$timepoint %in% timepoint, ]

  structure(
    list(
      data = data,
      metadata = entry,
      dataset_code = entry$dataset_code,
      version = resolve_version(version)
    ),
    class = "likingdb_dataset"
  )
}

#' @export
print.likingdb_dataset <- function(x, ...) {
  m <- x$metadata
  phases <- length(m$timepoints)
  cli::cli_text("{.strong {m$dataset_code}} — {m$first_author} ({m$year})")
  cli::cli_text("{nrow(x$data)} ratings · {m$n_subjects} subjects · {m$n_items} items{if (phases > 1) paste0(' · ', phases, ' phases') else ''}")
  cli::cli_text("scale {m$rating_scale_min}–{m$rating_scale_max} ({m$rating_scale_type}) · release v{x$version}")
  invisible(x)
}
