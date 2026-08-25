#' List the publications in the database
#'
#' @param version Release version, or `"latest"`.
#' @return A tibble with one row per study.
#' @examples
#' \donttest{
#' list_studies()
#' }
#' @export
list_studies <- function(version = "latest") {
  rows <- load_catalog(version)$studies
  tibble::as_tibble(do.call(rbind, lapply(rows, function(s) {
    data.frame(
      study_id = s$study_id, name = s$name, authors = s$authors,
      year = s$year %||% NA_integer_,
      doi = s$doi %||% NA_character_,
      journal = s$journal %||% NA_character_,
      citation = s$citation %||% NA_character_,
      stringsAsFactors = FALSE
    )
  })))
}

#' List the datasets in the database
#'
#' `timepoints` gives the rating phases a dataset holds. All but two datasets
#' have a single phase; see [get_dataset()].
#'
#' @param version Release version, or `"latest"`.
#' @return A tibble with one row per dataset.
#' @examples
#' \donttest{
#' list_datasets()
#' }
#' @export
list_datasets <- function(version = "latest") {
  rows <- load_catalog(version)$datasets
  tibble::as_tibble(do.call(rbind, lapply(rows, function(d) {
    data.frame(
      dataset_code = d$dataset_code,
      first_author = d$first_author %||% NA_character_,
      year = d$study_year %||% d$year %||% NA_integer_,
      study_name = d$study_name %||% NA_character_,
      n_subjects = d$n_subjects %||% NA_integer_,
      n_items = d$n_items %||% NA_integer_,
      n_ratings = d$n_ratings %||% NA_integer_,
      n_timepoints = length(d$timepoints),
      rating_scale_min = d$rating_scale_min %||% NA_real_,
      rating_scale_max = d$rating_scale_max %||% NA_real_,
      rating_scale_type = d$rating_scale_type %||% NA_character_,
      paper_doi = d$paper_doi %||% NA_character_,
      stringsAsFactors = FALSE
    )
  })))
}

#' List the stimuli in the database
#'
#' @param version Release version, or `"latest"`.
#' @return A tibble with one row per item.
#' @examples
#' \donttest{
#' list_items()
#' }
#' @export
list_items <- function(version = "latest") {
  readr::read_tsv(
    asset_path("items.tsv", version),
    col_types = readr::cols(
      item_id = readr::col_character(),
      name = readr::col_character(),
      standardized_name = readr::col_character(),
      n_datasets = readr::col_integer()
    )
  )
}

#' Look up one dataset's catalogue entry
#' @keywords internal
#' @noRd
dataset_entry <- function(code, version = "latest") {
  datasets <- load_catalog(version)$datasets
  codes <- vapply(datasets, function(d) d$dataset_code, character(1))
  ids <- vapply(datasets, function(d) d$dataset_id, character(1))

  hit <- which(tolower(codes) == tolower(code) | ids == code)
  if (length(hit) == 1) return(datasets[[hit]])

  prefix <- which(startsWith(tolower(codes), tolower(code)))
  if (length(prefix) == 1) return(datasets[[prefix]])
  if (length(prefix) > 1) {
    cli::cli_abort("{.val {code}} is ambiguous; matches {.val {sort(codes[prefix])}}.")
  }
  cli::cli_abort(c(
    "No dataset named {.val {code}}.",
    i = "Use {.code list_datasets()} to see the catalogue."
  ))
}

`%||%` <- function(x, y) if (is.null(x)) y else x
