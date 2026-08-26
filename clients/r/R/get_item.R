#' One stimulus across every study that used it
#'
#' The cross-study view. Because the underlying studies use different response
#' scales, compare on `normalized_rating`, not `rating`.
#'
#' Only the first rating phase of a repeated-phase dataset is included, so
#' those studies do not carry extra weight in a cross-study comparison.
#'
#' @param item An item name, e.g. `"kitkat"`.
#' @param version Release version, or `"latest"`.
#' @return An object of class `likingInitiative_item` with `data`, `datasets` and
#'   `version`.
#' @examples
#' \donttest{
#' k <- get_item("kitkat")
#' k$data
#' }
#' @export
get_item <- function(item, version = "latest") {
  db <- load_database(version)
  ratings <- db$ratings
  matched <- ratings[tolower(ratings$item_name) == tolower(item), ]
  if (nrow(matched) == 0) {
    cli::cli_abort(c(
      "No item named {.val {item}}.",
      i = "Use {.code list_items()} to see the stimuli."
    ))
  }

  # keep each dataset's earliest phase only
  first <- stats::aggregate(timepoint ~ dataset_code, data = matched, FUN = min)
  names(first)[2] <- ".first"
  matched <- merge(matched, first, by = "dataset_code")
  matched <- matched[matched$timepoint == matched$.first, ]
  matched$.first <- NULL

  codes <- unique(matched$dataset_code)
  entries <- Filter(function(d) d$dataset_code %in% codes, load_catalog(version)$datasets)

  structure(
    list(
      name = item,
      data = tibble::as_tibble(matched),
      datasets = entries,
      version = resolve_version(version)
    ),
    class = "likingInitiative_item"
  )
}

#' @export
print.likingInitiative_item <- function(x, ...) {
  cli::cli_text("{.strong {x$name}} \u2014 {nrow(x$data)} ratings across {length(x$datasets)} datasets")
  cli::cli_text("compare on {.field normalized_rating} \u00b7 release v{x$version}")
  invisible(x)
}
