#' Resolving a release version and fetching its assets
#'
#' The package reads versioned release files rather than a live service, so a
#' pinned version returns the same rows however long from now, and analyses
#' keep working when the web service does not.
#'
#' Assets come from Zenodo, which needs no credentials and mints a permanent
#' DOI per version. The package resolves the *concept* record -- what Zenodo
#' calls "all versions" -- so `latest` follows new releases without the
#' package itself needing an update.
#'
#' Set the `likingInitiative.release_dir` option (or the `LIKING_INITIATIVE_RELEASE_DIR`
#' environment variable) to a directory built by `scripts/build_release.py` to
#' work against an unreleased build. The test suite uses this, so tests never
#' touch the network.
#'
#' @keywords internal
#' @name release
NULL

.zenodo_api <- function() {
  Sys.getenv("LIKING_INITIATIVE_ZENODO_API", "https://zenodo.org/api")
}

# Zenodo's concept record always resolves to the newest published version.
.concept_rec <- function() {
  Sys.getenv("LIKING_INITIATIVE_CONCEPT_REC", "22216442")
}

.record_cache <- new.env(parent = emptyenv())

# One GET against Zenodo's API, retried on the statuses it returns when it is
# struggling (502/504 under load are common enough that a single attempt
# strands a user with an error that has nothing to do with their request).
.zenodo_get <- function(url) {
  tryCatch(
    httr2::req_perform(
      httr2::req_retry(
        httr2::req_error(httr2::req_timeout(httr2::request(url), 60),
                         is_error = function(...) FALSE),
        max_tries = 5,
        is_transient = function(resp) httr2::resp_status(resp) %in% c(429, 500, 502, 503, 504)
      )
    ),
    error = function(e) cli::cli_abort("Could not reach Zenodo: {conditionMessage(e)}")
  )
}

# The newest published version's Zenodo record, fetched once per session.
.fetch_record <- function() {
  if (!is.null(.record_cache$record)) return(.record_cache$record)
  response <- .zenodo_get(sprintf("%s/records/%s", .zenodo_api(), .concept_rec()))
  status <- httr2::resp_status(response)
  if (status == 404) {
    cli::cli_abort(c(
      "Zenodo has no record {.val {.concept_rec()}}.",
      i = "Build a release with {.code scripts/build_release.py} and set {.envvar LIKING_INITIATIVE_RELEASE_DIR}."
    ))
  }
  if (status != 200) {
    cli::cli_abort("Zenodo returned {status} resolving the latest version.")
  }
  record <- httr2::resp_body_json(response)
  .record_cache$record <- record
  .record_cache[[paste0("v", record$metadata$version)]] <- record
  record
}

# The Zenodo record that holds one version's files. The concept record only
# ever describes the newest version, so a pinned version is found in the
# concept's version listing; otherwise version = "1.6.1" would label the cache
# 1.6.1 but download whatever is newest -- the drift pinning exists to prevent.
.record_for <- function(version) {
  key <- paste0("v", version)
  if (!is.null(.record_cache[[key]])) return(.record_cache[[key]])
  url <- sprintf("%s/records?q=conceptrecid:%s&all_versions=true&size=25",
                 .zenodo_api(), .concept_rec())
  published <- character()
  while (!is.null(url)) {
    response <- .zenodo_get(url)
    if (httr2::resp_status(response) != 200) {
      cli::cli_abort("Zenodo returned {httr2::resp_status(response)} listing release versions.")
    }
    page <- httr2::resp_body_json(response)
    for (hit in page$hits$hits) {
      found <- hit$metadata$version
      if (!is.null(found)) {
        published <- c(published, found)
        .record_cache[[paste0("v", found)]] <- hit
      }
      if (identical(found, version)) return(hit)
    }
    url <- page$links[["next"]]
  }
  cli::cli_abort(c(
    "Release v{version} is not on Zenodo.",
    i = "Published versions: {.val {sort(published)}}."
  ))
}

.catalog_file <- "catalog.json"

# cache -------------------------------------------------------------------

#' Path to the package's asset cache
#'
#' Honours `options(likingInitiative.cache_dir = )` so `R CMD check` and tests never
#' write into a real user cache.
#' @keywords internal
#' @noRd
get_cache_dir <- function(version = NULL, create = TRUE) {
  base <- getOption(
    "likingInitiative.cache_dir",
    Sys.getenv("LIKING_INITIATIVE_CACHE_DIR", unset = tools::R_user_dir("likingInitiative", "cache"))
  )
  path <- if (is.null(version)) base else fs::path(base, version)
  if (create && !fs::dir_exists(path)) fs::dir_create(path, recurse = TRUE)
  path
}

#' Report on the local asset cache
#'
#' Shows where downloaded release files are kept, how much space they use, and
#' which versions are present.
#'
#' @return A list, invisibly, with `path`, `bytes` and `versions`.
#' @examples
#' cache_info()
#' @export
cache_info <- function() {
  base <- get_cache_dir(create = FALSE)
  if (!fs::dir_exists(base)) {
    cli::cli_alert_info("No cache yet. It will be created at {.path {base}}.")
    return(invisible(list(path = base, bytes = 0, versions = character())))
  }
  contents <- fs::dir_info(base, recurse = TRUE)
  files <- contents[contents$type == "file", ]
  versions <- basename(fs::dir_ls(base, type = "directory"))
  cli::cli_alert_info("Cache: {.path {base}}")
  cli::cli_alert_info("Size: {.val {fs::fs_bytes(sum(files$size))}} across {nrow(files)} file{?s}")
  if (length(versions)) cli::cli_alert_info("Versions: {.val {versions}}")
  invisible(list(path = base, bytes = sum(files$size), versions = versions))
}

#' Delete cached release files
#'
#' @param version Version to remove. `NULL` (default) clears every version.
#' @return Invisibly, the number of bytes freed.
#' @examples
#' \donttest{
#' clear_cache()
#' }
#' @export
clear_cache <- function(version = NULL) {
  target <- get_cache_dir(version, create = FALSE)
  if (!fs::dir_exists(target)) {
    cli::cli_alert_info("Nothing cached at {.path {target}}.")
    return(invisible(0))
  }
  contents <- fs::dir_info(target, recurse = TRUE)
  freed <- sum(contents[contents$type == "file", ]$size)
  fs::dir_delete(target)
  cli::cli_alert_success("Freed {.val {fs::fs_bytes(freed)}}.")
  invisible(freed)
}

# resolution --------------------------------------------------------------

#' A locally built release directory, if one is configured
#' @keywords internal
#' @noRd
local_release_dir <- function() {
  raw <- getOption("likingInitiative.release_dir", Sys.getenv("LIKING_INITIATIVE_RELEASE_DIR", ""))
  if (!nzchar(raw)) return(NULL)
  path <- fs::path_expand(raw)
  if (!fs::file_exists(fs::path(path, .catalog_file))) {
    cli::cli_abort(c(
      "{.path {path}} has no {.file {.catalog_file}}.",
      i = "Build one with {.code scripts/build_release.py}."
    ))
  }
  path
}

#' Turn "latest" into a concrete version
#' @keywords internal
#' @noRd
resolve_version <- function(version = "latest") {
  local <- local_release_dir()
  if (!is.null(local)) {
    return(jsonlite::fromJSON(fs::path(local, .catalog_file))$release$version)
  }
  if (!identical(version, "latest")) return(version)

  record <- .fetch_record()
  resolved <- record$metadata$version
  if (is.null(resolved) || !nzchar(resolved)) {
    cli::cli_abort("The Zenodo record carries no version.")
  }
  resolved
}

#' Local path to one release asset, downloading and caching if needed
#' @keywords internal
#' @noRd
asset_path <- function(name, version = "latest", force = FALSE) {
  local <- local_release_dir()
  if (!is.null(local)) {
    path <- fs::path(local, name)
    if (!fs::file_exists(path)) cli::cli_abort("{.file {name}} is not in {.path {local}}.")
    return(path)
  }

  resolved <- resolve_version(version)
  cached <- fs::path(get_cache_dir(resolved), name)
  if (fs::file_exists(cached) && !force) return(cached)

  # Zenodo's file store is flat, so a nested path is flattened in the name.
  asset <- gsub("/", "__", name, fixed = TRUE)
  record <- .record_for(resolved)
  url <- sprintf("%s/records/%s/files/%s/content", .zenodo_api(), record$id, asset)

  if (!fs::dir_exists(fs::path_dir(cached))) {
    fs::dir_create(fs::path_dir(cached), recurse = TRUE)
  }
  response <- httr2::req_perform(
    httr2::req_retry(
      httr2::req_error(httr2::req_timeout(httr2::request(url), 300),
                       is_error = function(...) FALSE),
      max_tries = 5,
      is_transient = function(resp) httr2::resp_status(resp) %in% c(429, 500, 502, 503, 504)
    ),
    path = cached
  )
  if (httr2::resp_status(response) != 200) {
    fs::file_delete(cached)
    cli::cli_abort("{.file {name}} is not in release v{resolved} on Zenodo.")
  }
  cached
}

#' The release catalog
#' @keywords internal
#' @noRd
load_catalog <- function(version = "latest") {
  jsonlite::fromJSON(asset_path(.catalog_file, version), simplifyVector = FALSE)
}

#' Version, date and headline counts for the release in use
#'
#' @param version Release version, or `"latest"`.
#' @return A list describing the release.
#' @examples
#' \donttest{
#' release_info()
#' }
#' @export
release_info <- function(version = "latest") {
  load_catalog(version)$release
}
