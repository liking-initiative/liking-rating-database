# Every test runs against a release directory built by
# scripts/build_release.py, so nothing here touches the network.
release_dir <- function() {
  # LIKING_INITIATIVE_RELEASE_DIR wins, which is how docs/RELEASING.md says to run
  # these. The relative path is the monorepo layout, kept so a checkout inside
  # liking-rating-database still finds its own build.
  env <- Sys.getenv("LIKING_INITIATIVE_RELEASE_DIR", "")
  if (nzchar(env) && file.exists(file.path(env, "catalog.json"))) return(env)
  rel <- file.path("..", "..", "..", "..", "release")
  if (file.exists(file.path(rel, "catalog.json"))) return(normalizePath(rel))
  NULL
}

skip_without_release <- function() {
  dir <- release_dir()
  if (!file.exists(file.path(dir, "catalog.json"))) {
    testthat::skip("no local release; build one with scripts/build_release.py")
  }
  options(likingInitiative.release_dir = dir)
}
