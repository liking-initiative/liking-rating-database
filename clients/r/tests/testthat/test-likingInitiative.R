test_that("release_info reports the pinned version and counts", {
  skip_without_release()
  info <- release_info()
  expect_true(nzchar(info$version))
  expect_gt(info$n_ratings, 0)
  # the migration log travels with the release, so a user can tell which data
  # corrections their copy includes
  expect_gt(length(info$schema_migrations), 0)
})

test_that("catalogue listings match the release header", {
  skip_without_release()
  info <- release_info()
  expect_equal(nrow(list_datasets()), info$n_datasets)
  expect_equal(nrow(list_studies()), info$n_studies)
  expect_equal(nrow(list_items()), info$n_items)
})

test_that("exactly the two repeated-phase datasets report multiple phases", {
  skip_without_release()
  ds <- list_datasets()
  repeated <- sort(ds$dataset_code[ds$n_timepoints > 1])
  # Keep in step with the repeats table in docs/RELEASE_CODEBOOK.md: for
  # these, (subject_id, item_id) is not a unique key.
  expect_equal(repeated, c("chenhol1", "chenhol2", "crosswebb", "hamesmcc", "leehare2023exp2", "leeholyoak2021"))
})

test_that("get_dataset returns data with its metadata", {
  skip_without_release()
  d <- get_dataset("leeholyoak2021")
  expect_s3_class(d, "likingInitiative_dataset")
  expect_equal(nrow(d$data), d$metadata$n_ratings)
  expect_equal(d$metadata$rating_scale_max, 100)
})

test_that("identifier columns stay character", {
  # read as numeric, "007" becomes 7 and joins silently break
  skip_without_release()
  d <- get_dataset("leeholyoak2021")
  expect_type(d$data$subject_id, "character")
  expect_type(d$data$item_id, "character")
})

test_that("repeated phases are distinguishable", {
  skip_without_release()
  d <- get_dataset("leeholyoak2021")
  full <- unique(d$data[, c("subject_id", "item_id", "timepoint")])
  expect_equal(nrow(full), nrow(d$data))
  without <- unique(d$data[, c("subject_id", "item_id")])
  expect_lt(nrow(without), nrow(d$data))
})

test_that("timepoint filter keeps one phase", {
  skip_without_release()
  d <- get_dataset("leeholyoak2021", timepoint = 2)
  expect_equal(unique(d$data$timepoint), 2L)
})

test_that("several datasets come back named", {
  skip_without_release()
  m <- get_dataset(c("leeholyoak2021", "leehare2023exp2"))
  expect_named(m, c("leeholyoak2021", "leehare2023exp2"))
})

test_that("an unknown dataset is a clear error", {
  skip_without_release()
  expect_error(get_dataset("definitely-not-a-dataset"), "No dataset named")
})

test_that("get_item pools an item across datasets, first phase only", {
  skip_without_release()
  k <- get_item("kitkat")
  expect_s3_class(k, "likingInitiative_item")
  expect_gt(length(k$datasets), 1)
  phases <- tapply(k$data$timepoint, k$data$dataset_code,
                   function(x) length(unique(x)))
  expect_equal(max(phases), 1)
})

test_that("an unknown item is a clear error", {
  skip_without_release()
  expect_error(get_item("not-a-real-food"), "No item named")
})

test_that("load_database is complete and uniquely keyed", {
  skip_without_release()
  db <- load_database()
  expect_named(db, c("ratings", "studies", "datasets", "items"))
  r <- db$ratings
  expect_equal(nrow(r), release_info()$n_ratings)
  key <- unique(r[, c("dataset_code", "subject_id", "item_id", "timepoint")])
  expect_equal(nrow(key), nrow(r))
  expect_gte(min(r$normalized_rating), 0)
  expect_lte(max(r$normalized_rating), 1)
})

test_that("per-dataset files agree with the bulk file", {
  skip_without_release()
  db <- load_database()
  counts <- table(db$ratings$dataset_code)
  ds <- list_datasets()
  for (i in seq_len(nrow(ds))) {
    expect_equal(as.integer(counts[[ds$dataset_code[i]]]), ds$n_ratings[i],
                 info = ds$dataset_code[i])
  }
})

test_that("cite() returns the study only, and cite() alone returns ours", {
  # Appending the database citation to every call would be noise in a loop;
  # the web UI bundles both on copy instead.
  skip_without_release()
  txt <- cite(get_dataset("leeholyoak2021"))
  expect_match(txt, "Holyoak")
  expect_false(grepl("Fernandez", txt))
  expect_match(cite(), "Fernandez")
})

test_that("bibtex is well formed", {
  skip_without_release()
  entry <- bibtex(get_dataset("leeholyoak2021"))
  expect_match(entry, "^@article\\{")
  expect_match(entry, "doi")
})
