# Figures, Table 1, and the numbers cited in the data descriptor.
#
# Reads the database through the likingInitiative package from a local release
# directory, so the figures cannot drift from the data that ships:
#
#   LIKING_INITIATIVE_RELEASE_DIR=$PWD/release Rscript analysis/make_figures.R
#
# Without the variable the package resolves the newest published version from
# Zenodo instead, which is what a reader reproducing the figures would get.
#
# Writes analysis/figures/fig{1,2,3,4}_*.png, analysis/tables/table1_studies.csv,
# and analysis/tables/summary.txt (every number the text cites).

suppressPackageStartupMessages({
  library(likingInitiative)
  library(dplyr)
  library(ggplot2)
  library(patchwork)
  library(RColorBrewer)
})

root    <- normalizePath(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), ".."))
fig_dir <- file.path(root, "analysis", "figures")
tab_dir <- file.path(root, "analysis", "tables")
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)
dir.create(tab_dir, showWarnings = FALSE, recursive = TRUE)

# ---------------------------------------------------------------- style
# The publication theme used across the lab's figures, and the Set2 palette:
# one colour per panel, never cycled.
theme_pub <- theme_minimal(base_size = 11) +
  theme(
    panel.grid.minor = element_blank(),
    panel.grid.major = element_line(linewidth = 0.3, color = "gray90"),
    axis.line        = element_line(color = "black", linewidth = 0.4),
    axis.ticks       = element_line(color = "black", linewidth = 0.4),
    legend.position  = "right",
    legend.title     = element_text(size = 10, face = "bold"),
    legend.text      = element_text(size = 9),
    strip.background = element_rect(fill = "gray95", color = NA),
    strip.text       = element_text(face = "bold", size = 10),
    plot.title       = element_text(face = "bold", size = 11, hjust = 0),
    panel.border     = element_rect(color = "black", fill = NA, linewidth = 0.5)
  )
set2 <- brewer.pal(8, "Set2")

save_png <- function(p, name, width, height) {
  ggsave(file.path(fig_dir, paste0(name, ".png")), p, width = width, height = height, dpi = 300, bg = "white")
  cat(sprintf("%s written\n", name))
}

# ---------------------------------------------------------------- data
db       <- load_database()
info     <- release_info()
studies  <- db$studies
datasets <- db$datasets
ratings  <- db$ratings

# "Surname et al., Year"; the dataset code is appended wherever a bare label
# would repeat (a study with several datasets, or two studies sharing first
# author and year).
surnames <- function(authors) {
  vapply(strsplit(authors, ";\\s*"), function(a) {
    s <- trimws(sub(",.*$", "", a))
    if (length(s) == 1) s else if (length(s) == 2) paste(s[1], "&", s[2]) else paste(s[1], "et al.")
  }, character(1))
}
studies <- studies |> mutate(study_label = paste0(surnames(authors), ", ", year))

first_phase <- ratings |> filter(timepoint == 1)
per_ds <- first_phase |>
  group_by(dataset_code) |>
  summarise(n_participants = n_distinct(subject_id),
            n_items        = n_distinct(item_id),
            mean_normalized = mean(normalized_rating), .groups = "drop") |>
  left_join(ratings |> group_by(dataset_code) |>
              summarise(n_ratings_all_phases = n(), n_phases = n_distinct(timepoint), .groups = "drop"),
            by = "dataset_code") |>
  left_join(datasets |> select(dataset_code, rating_scale_min, rating_scale_max, rating_scale_type),
            by = "dataset_code") |>
  # the release's datasets table has no study id; ratings carry it
  left_join(ratings |> distinct(dataset_code, study_id), by = "dataset_code") |>
  left_join(studies |> select(study_id, study_label), by = "study_id") |>
  group_by(study_id) |> mutate(datasets_in_study = n()) |> ungroup() |>
  group_by(study_label) |> mutate(studies_with_label = n_distinct(study_id)) |> ungroup() |>
  mutate(label = if_else(datasets_in_study > 1 | studies_with_label > 1,
                         paste0(study_label, " (", dataset_code, ")"), study_label),
         scale_range = sprintf("[%g, %g]", rating_scale_min, rating_scale_max)) |>
  arrange(dataset_code)

presence <- ratings |> distinct(dataset_code, item_id)
per_item <- presence |> count(item_id, name = "n_datasets")

# ---------------------------------------------------------------- summary
summary_lines <- c(
  sprintf("release: %s (%d migrations)", info$version, length(info$schema_migrations)),
  "",
  sprintf("studies: %d", nrow(studies)),
  sprintf("datasets: %d", nrow(datasets)),
  sprintf("ratings: %s", format(nrow(ratings), big.mark = ",")),
  sprintf("participants (unique within dataset, summed): %s",
          format(sum(ratings |> distinct(dataset_code, subject_id) |> nrow()), big.mark = ",")),
  sprintf("items: %s", format(n_distinct(ratings$item_id), big.mark = ",")),
  sprintf("publication years: %d to %d", min(studies$year), max(studies$year)),
  sprintf("published studies with a DOI: %d", sum(!is.na(studies$doi) & nzchar(studies$doi))),
  "",
  sprintf("participants per dataset: median %d, range %d to %d",
          as.integer(median(per_ds$n_participants)), min(per_ds$n_participants), max(per_ds$n_participants)),
  sprintf("items per dataset: median %d, range %d to %d",
          as.integer(median(per_ds$n_items)), min(per_ds$n_items), max(per_ds$n_items)),
  sprintf("datasets with repeated rating phases: %d (%s)", sum(per_ds$n_phases > 1),
          paste(per_ds$dataset_code[per_ds$n_phases > 1], collapse = ", ")),
  "",
  "scale types (datasets):",
  sprintf("  %s: %d", names(table(per_ds$rating_scale_type)), as.integer(table(per_ds$rating_scale_type))),
  "",
  "scale ranges (datasets):",
  sprintf("  %s: %d", names(sort(table(per_ds$scale_range), decreasing = TRUE)),
          as.integer(sort(table(per_ds$scale_range), decreasing = TRUE))),
  "",
  sprintf("items rated in more than one dataset: %s of %s; most shared item appears in %d datasets",
          format(sum(per_item$n_datasets > 1), big.mark = ","), format(nrow(per_item), big.mark = ","),
          max(per_item$n_datasets))
)

# ---------------------------------------------------------------- table 1
table1 <- per_ds |>
  group_by(study_id) |>
  summarise(Datasets = paste(dataset_code, collapse = ", "),
            N        = sum(n_participants),
            Items    = max(n_items),
            Ratings  = sum(n_ratings_all_phases),
            Scale    = paste(sort(unique(sprintf("%g to %g (%s)", rating_scale_min, rating_scale_max, rating_scale_type))),
                             collapse = "; "),
            .groups = "drop") |>
  left_join(studies |> select(study_id, Study = study_label, Year = year, Journal = journal, DOI = doi), by = "study_id") |>
  mutate(Journal = if_else(is.na(Journal) | !nzchar(Journal) | Journal == "In preparation", "Unpublished", Journal),
         DOI = if_else(is.na(DOI), "", DOI)) |>
  select(Study, Year, Journal, Datasets, N, Items, Ratings, Scale, DOI) |>
  arrange(Study)
write.csv(table1, file.path(tab_dir, "table1_studies.csv"), row.names = FALSE)
cat(sprintf("table 1: %d studies\n", nrow(table1)))

# ---------------------------------------------------------------- figure 1
years <- studies |> count(year)
p_a <- ggplot(years, aes(factor(year), n)) +
  geom_col(fill = set2[1], width = 0.75) +
  geom_text(aes(label = n), vjust = -0.4, size = 3) +
  scale_y_continuous(breaks = scales::breaks_pretty(n = 5, min.n = 1), expand = expansion(mult = c(0, 0.12))) +
  labs(title = "(a) Publication Year", x = "Publication Year", y = "Number of Studies") +
  theme_pub + theme(axis.text.x = element_text(angle = 45, hjust = 1))

ranges <- per_ds |> count(scale_range) |> arrange(n, scale_range) |>
  mutate(scale_range = factor(scale_range, levels = scale_range))
p_b <- ggplot(ranges, aes(n, scale_range)) +
  geom_col(fill = set2[2], width = 0.75) +
  geom_text(aes(label = n), hjust = -0.4, size = 3) +
  scale_x_continuous(expand = expansion(mult = c(0, 0.12))) +
  labs(title = "(b) Rating Scale Ranges", x = "Number of Datasets", y = NULL) +
  theme_pub

hist_panel <- function(x, fill, title, xlab) {
  med <- median(x)
  ggplot(data.frame(x = x), aes(x)) +
    geom_histogram(binwidth = 50, boundary = 0, fill = fill, color = "white", linewidth = 0.3) +
    geom_vline(xintercept = med, linetype = "dashed", linewidth = 0.5) +
    annotate("label", x = Inf, y = Inf, hjust = 1.1, vjust = 1.5, size = 3.2,
             label = sprintf("Mdn = %d", as.integer(med))) +
    scale_y_continuous(breaks = scales::breaks_pretty(n = 5), expand = expansion(mult = c(0, 0.08))) +
    labs(title = title, x = xlab, y = "Number of Datasets") +
    theme_pub
}
p_c <- hist_panel(per_ds$n_participants, set2[3], "(c) Subjects per Dataset", "Number of Subjects")
p_d <- hist_panel(per_ds$n_items,        set2[4], "(d) Items per Dataset",    "Number of Items")

save_png((p_a | p_b) / (p_c | p_d), "fig1_database_overview", width = 12, height = 9)

# ---------------------------------------------------------------- figure 2
# Cross-study item coverage: the property that makes comparison across
# studies possible. (a) how many datasets each item was rated in; (b) the most
# widely rated items, with the range of their per-dataset means; (c) overlap
# between datasets as a Jaccard index over item sets.
item_names <- db$items |> select(item_id, item_name = standardized_name)

cov_counts <- per_item |> count(n_datasets, name = "n_items")
p2a <- ggplot(cov_counts, aes(n_datasets, n_items)) +
  geom_col(fill = set2[3], width = 0.8) +
  geom_text(data = cov_counts |> filter(n_items >= 100), aes(label = n_items), vjust = -0.4, size = 2.6) +
  scale_x_continuous(breaks = scales::breaks_pretty(n = 8)) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.1))) +
  labs(title = "(a) Datasets per Item",
       x = "Number of Datasets an Item Was Rated In", y = "Number of Items") +
  theme_pub

top <- first_phase |>
  group_by(item_id, dataset_code) |>
  summarise(m = mean(normalized_rating), .groups = "drop") |>
  group_by(item_id) |>
  summarise(n_datasets = n(), mean_of_means = mean(m), lo = min(m), hi = max(m), .groups = "drop") |>
  left_join(item_names, by = "item_id") |>
  arrange(desc(n_datasets), desc(mean_of_means)) |>
  slice_head(n = 25) |>
  mutate(item_name = factor(item_name, levels = rev(item_name)))
p2b <- ggplot(top, aes(y = item_name)) +
  geom_errorbar(aes(xmin = lo, xmax = hi), width = 0.3, linewidth = 0.4, color = "gray40", orientation = "y") +
  geom_point(aes(x = mean_of_means), shape = 18, size = 3, color = set2[3]) +
  geom_text(aes(x = 1.02, label = n_datasets), hjust = 0, size = 2.6, color = "gray30") +
  scale_x_continuous(limits = c(0, 1.12), breaks = seq(0, 1, 0.25)) +
  labs(title = "(b) Most Widely Rated Items",
       x = "Mean Normalized Rating (diamond: mean of dataset means; bar: range across datasets)",
       y = NULL) +
  scale_y_discrete(expand = expansion(add = c(0.6, 1.4))) +
  annotate("text", x = 1.02, y = nrow(top) + 1, label = "datasets", hjust = 0, size = 2.6, color = "gray30", fontface = "bold") +
  coord_cartesian(clip = "off") +
  theme_pub + theme(axis.text.y = element_text(size = 8), axis.title.x = element_text(size = 9))

codes <- sort(unique(presence$dataset_code))
sets  <- split(presence$item_id, presence$dataset_code)
jac   <- outer(codes, codes, Vectorize(function(a, b) {
  length(intersect(sets[[a]], sets[[b]])) / length(union(sets[[a]], sets[[b]]))
}))
dimnames(jac) <- list(codes, codes)
ord   <- codes[hclust(as.dist(1 - jac), method = "average")$order]
jac_long <- as.data.frame(as.table(jac)) |>
  setNames(c("a", "b", "jaccard")) |>
  mutate(a = factor(a, levels = ord), b = factor(b, levels = ord),
         jaccard = if_else(a == b, NA_real_, jaccard))
p2c <- ggplot(jac_long, aes(a, b, fill = jaccard)) +
  geom_tile(color = "white", linewidth = 0.2) +
  scale_fill_gradient(low = "#f7fbff", high = "#08306b", na.value = "gray92",
                      limits = c(0, 1), name = "Jaccard\nindex") +
  coord_equal() +
  labs(title = "(c) Item Overlap Between Datasets", x = NULL, y = NULL) +
  theme_pub +
  theme(axis.text.x = element_text(angle = 90, hjust = 1, vjust = 0.5, size = 6),
        axis.text.y = element_text(size = 6), panel.grid = element_blank(),
        legend.position = "right")

save_png((p2a | p2b) / p2c + plot_layout(heights = c(1, 2.1)), "fig2_cross_study_items", width = 12, height = 16)

# ---------------------------------------------------------------- figure 3
order <- per_ds |> arrange(mean_normalized) |> pull(dataset_code)
dist <- first_phase |>
  left_join(per_ds |> select(dataset_code, label), by = "dataset_code") |>
  mutate(label = factor(label, levels = per_ds$label[match(order, per_ds$dataset_code)]))

# Five quantiles per dataset, drawn with an identity stat so the whiskers are
# exactly the 5th and 95th percentiles rather than ggplot's 1.5 IQR rule.
bx <- dist |>
  group_by(label) |>
  summarise(q05 = quantile(normalized_rating, .05), q25 = quantile(normalized_rating, .25),
            q50 = median(normalized_rating), q75 = quantile(normalized_rating, .75),
            q95 = quantile(normalized_rating, .95), mean = mean(normalized_rating), .groups = "drop")

fig3 <- ggplot(bx, aes(y = label)) +
  geom_errorbar(aes(xmin = q05, xmax = q95), width = 0.35, linewidth = 0.4, color = "gray30", orientation = "y") +
  geom_boxplot(aes(xmin = q05, xlower = q25, xmiddle = q50, xupper = q75, xmax = q95),
               stat = "identity", orientation = "y", fill = set2[1], color = "gray30", width = 0.7, linewidth = 0.4) +
  geom_point(aes(x = mean), shape = 18, size = 3, color = "black") +
  scale_x_continuous(limits = c(0, 1), breaks = seq(0, 1, 0.2), expand = expansion(mult = 0.01)) +
  labs(title = "Normalized Rating Distributions per Dataset",
       x = "Normalized Rating (0 = lowest, 1 = highest)", y = NULL,
       caption = paste("Box: interquartile range; line: median; diamond: mean; whiskers: 5th to 95th percentile.",
                       "First rating phase only for datasets with repeated phases.")) +
  theme_pub + theme(axis.text.y = element_text(size = 8), plot.caption = element_text(size = 8, color = "gray30", hjust = 0))
save_png(fig3, "fig3_rating_distributions", width = 10, height = 0.28 * nrow(per_ds) + 1.5)

# ---------------------------------------------------------------- figure 4
# Do studies agree on which items are liked more? For every pair of datasets
# sharing at least 20 items, the Pearson correlation between their item means
# (normalized rating, first phase). Nothing is modelled.
item_means <- first_phase |>
  group_by(dataset_code, item_id) |>
  summarise(m = mean(normalized_rating), .groups = "drop")

pair_rows <- list()
for (i in seq_along(codes)) for (j in seq_along(codes)) if (i < j) {
  a <- item_means |> filter(dataset_code == codes[i])
  b <- item_means |> filter(dataset_code == codes[j])
  ab <- inner_join(a, b, by = "item_id", suffix = c("_a", "_b"))
  if (nrow(ab) >= 20) {
    pair_rows[[length(pair_rows) + 1]] <- data.frame(a = codes[i], b = codes[j],
                                                     shared_items = nrow(ab), r = cor(ab$m_a, ab$m_b))
  }
}
pairs <- bind_rows(pair_rows)

summary_lines <- c(summary_lines, "",
  sprintf("dataset pairs sharing >= 20 items: %d (of %d datasets)", nrow(pairs), n_distinct(c(pairs$a, pairs$b))),
  sprintf("item-mean correlation: median %.2f, IQR %.2f to %.2f, range %.2f to %.2f",
          median(pairs$r), quantile(pairs$r, .25), quantile(pairs$r, .75), min(pairs$r), max(pairs$r)),
  sprintf("pairs with r >= 0.5: %d (%.0f%%); r < 0: %d",
          sum(pairs$r >= 0.5), 100 * mean(pairs$r >= 0.5), sum(pairs$r < 0)))
writeLines(summary_lines, file.path(tab_dir, "summary.txt"))
cat(summary_lines, sep = "\n"); cat("\n")

p4a <- ggplot(pairs, aes(r)) +
  geom_histogram(binwidth = 0.05, boundary = 0, fill = set2[2], color = "white", linewidth = 0.3) +
  geom_vline(xintercept = median(pairs$r), linetype = "dashed", linewidth = 0.5) +
  annotate("label", x = -Inf, y = Inf, hjust = -0.1, vjust = 1.5, size = 3.2,
           label = sprintf("Mdn r = %.2f\n%d pairs", median(pairs$r), nrow(pairs))) +
  scale_x_continuous(limits = c(-0.4, 1), breaks = seq(-0.25, 1, 0.25)) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.08))) +
  labs(title = "(a) Agreement Between Datasets on Item Means",
       x = "Correlation of Item Means Between Two Datasets (Pearson r)", y = "Number of Dataset Pairs") +
  theme_pub

# The illustrative pair: the largest shared item set between datasets whose
# studies have different first authors.
author_of <- per_ds |> mutate(first = sub(",.*$", "", study_label)) |> select(dataset_code, first)
ex <- pairs |>
  left_join(author_of |> rename(a = dataset_code, first_a = first), by = "a") |>
  left_join(author_of |> rename(b = dataset_code, first_b = first), by = "b") |>
  filter(first_a != first_b) |> arrange(desc(shared_items), desc(r)) |> slice_head(n = 1)
ex_ab <- inner_join(item_means |> filter(dataset_code == ex$a), item_means |> filter(dataset_code == ex$b),
                    by = "item_id", suffix = c("_a", "_b"))
lab_a <- per_ds$label[per_ds$dataset_code == ex$a]; lab_b <- per_ds$label[per_ds$dataset_code == ex$b]
p4b <- ggplot(ex_ab, aes(m_a, m_b)) +
  geom_abline(slope = 1, intercept = 0, linetype = "dashed", color = "gray60") +
  geom_point(color = set2[2], alpha = 0.7, size = 1.8) +
  geom_smooth(method = "lm", se = FALSE, color = "black", linewidth = 0.6, formula = y ~ x) +
  annotate("label", x = Inf, y = -Inf, hjust = 1.1, vjust = -0.5, size = 3.2,
           label = sprintf("r = %.2f\n%d shared items", ex$r, ex$shared_items)) +
  scale_x_continuous(limits = c(0, 1), breaks = seq(0, 1, 0.25)) +
  scale_y_continuous(limits = c(0, 1), breaks = seq(0, 1, 0.25)) +
  coord_equal() +
  labs(title = "(b) One Pair of Datasets",
       x = paste("Item Mean,", lab_a), y = paste("Item Mean,", lab_b)) +
  theme_pub

save_png(p4a | p4b, "fig4_example_agreement", width = 12, height = 5.5)

cat("done\n")
