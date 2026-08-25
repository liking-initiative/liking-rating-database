DATABASE_CITATION <- paste(
  "Fernandez, K., Goyal, S., & Krajbich, I. A database of subjective",
  "evaluation ratings for decision-making research. (In preparation.)"
)

#' Citation text
#'
#' Please cite both the database and the study whose data you used.
#'
#' @param x A dataset or item from [get_dataset()] / [get_item()]. With no
#'   argument, returns the citation for the database itself.
#' @param ... Unused.
#' @return A character string.
#' @examples
#' cite()
#' @export
cite <- function(x, ...) UseMethod("cite")

#' @export
cite.default <- function(x, ...) DATABASE_CITATION

#' @export
cite.likingInitiative_dataset <- function(x, ...) {
  m <- x$metadata
  citation <- m$citation %||% m$study_name %||% ""
  if (!is.null(m$paper_doi)) {
    citation <- paste0(citation, " https://doi.org/", m$paper_doi)
  }
  paste0(citation, "\n\nPlease also cite the database:\n", DATABASE_CITATION)
}

#' @export
cite.likingInitiative_item <- function(x, ...) {
  refs <- unique(vapply(x$datasets, function(d) d$citation %||% d$study_name %||% "",
                        character(1)))
  refs <- sort(refs[nzchar(refs)])
  paste0("Ratings of this item come from:\n  - ", paste(refs, collapse = "\n  - "),
         "\n\nPlease also cite the database:\n", DATABASE_CITATION)
}

#' BibTeX for a dataset's source publication
#'
#' @param x A dataset from [get_dataset()].
#' @param ... Unused.
#' @return A character string holding a BibTeX entry.
#' @examples
#' \donttest{
#' bibtex(get_dataset("leeholyoak2021"))
#' }
#' @export
bibtex <- function(x, ...) UseMethod("bibtex")

#' @export
bibtex.likingInitiative_dataset <- function(x, ...) {
  m <- x$metadata
  authors <- paste(trimws(strsplit(m$authors %||% "", ";")[[1]]), collapse = " and ")
  key <- paste0(tolower(gsub("[^A-Za-z]", "", m$first_author %||% "study")), m$year %||% "")
  fields <- c(
    sprintf("  author  = {%s}", authors),
    sprintf("  title   = {%s}", m$study_name %||% ""),
    sprintf("  year    = {%s}", m$year %||% "")
  )
  if (!is.null(m$journal)) fields <- c(fields, sprintf("  journal = {%s}", m$journal))
  if (!is.null(m$paper_doi)) fields <- c(fields, sprintf("  doi     = {%s}", m$paper_doi))
  paste0("@article{", key, ",\n", paste(fields, collapse = ",\n"), "\n}")
}
