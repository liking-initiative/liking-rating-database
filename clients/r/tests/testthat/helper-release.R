# Every test runs against a release directory built by
# scripts/build_release.py, so nothing here touches the network.
release_dir <- function() {
  normalizePath(file.path(testthat::test_path(), "..", "..", "..", "..", "release"),
                mustWork = FALSE)
}

skip_without_release <- function() {
  dir <- release_dir()
  if (!file.exists(file.path(dir, "catalog.json"))) {
    testthat::skip("no local release; build one with scripts/build_release.py")
  }
  options(likingInitiative.release_dir = dir)
}
