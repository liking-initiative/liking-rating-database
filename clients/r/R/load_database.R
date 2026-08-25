.db_cache <- new.env(parent = emptyenv())

#' The whole corpus in one call
#'
#' @param version Release version, or `"latest"`.
#' @return A list of tibbles: `ratings`, `studies`, `datasets`, `items`. Held
#'   in memory after the first call.
#' @examples
#' \donttest{
#' db <- load_database()
#' nrow(db$ratings)
#' }
#' @export
load_database <- function(version = "latest") {
  resolved <- resolve_version(version)
  if (!is.null(.db_cache[[resolved]])) return(.db_cache[[resolved]])

  ratings <- readr::read_tsv(
    asset_path("ratings.tsv.gz", version),
    col_types = readr::cols(
      dataset_code = readr::col_character(),
      study_id = readr::col_character(),
      subject_id = readr::col_character(),
      item_id = readr::col_character(),
      item_name = readr::col_character(),
      timepoint = readr::col_integer(),
      rating = readr::col_double(),
      normalized_rating = readr::col_double()
    )
  )
  out <- list(
    ratings = ratings,
    studies = list_studies(version),
    datasets = list_datasets(version),
    items = list_items(version)
  )
  .db_cache[[resolved]] <- out
  out
}
