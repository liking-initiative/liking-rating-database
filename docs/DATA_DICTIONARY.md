# Data Dictionary - Liking Rating Database

This document provides detailed descriptions of all database fields and their meanings in the Liking Rating Database.

## Database Schema Overview

The database consists of six main tables:
- **Studies**: Research study metadata
- **Datasets**: Individual datasets within studies
- **Items**: Food items being rated
- **Ratings**: Individual preference ratings
- **Download Logs**: Download tracking for analytics
- **Search Logs**: Search queries for analytics

---

## Table: Studies

Contains metadata about research studies that contributed data to the database.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | String (UUID) | Unique identifier for the study | `cd2fa20a-8121-4046-9656-a42a404c3343` |
| `name` | String (255) | Full study name or title | `"Bakkour, A., Botvinik-Nezer, R., Cohen, N., ..."` |
| `authors` | JSON Array | List of study authors | `["Bakkour, A.", "Botvinik-Nezer, R."]` |
| `year` | Integer | Publication year | `2018` |
| `doi` | String (255) | Digital Object Identifier (optional) | `"https://doi.org/10.1371/journal.pone.0201580"` |
| `description` | Text | Study description or abstract | `"Food preference study from bakbot dataset"` |
| `publication_title` | String (500) | Title of the published paper | `"Spacing of cue-approach training leads to..."` |
| `journal` | String (255) | Journal name | `"PLOS ONE"` |
| `osf_project_id` | String (50) | Open Science Framework project ID | `"xyz123"` |
| `created_at` | DateTime | Record creation timestamp | `2024-01-15T10:30:00Z` |
| `updated_at` | DateTime | Last update timestamp | `2024-01-15T10:30:00Z` |

---

## Table: Datasets

Contains information about individual datasets within studies. A study may contain multiple datasets.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | String (UUID) | Unique identifier for the dataset | `5b519977-e395-43c6-9aea-0aa6255ec4d4` |
| `study_id` | String (UUID) | Foreign key to Studies table | `cd2fa20a-8121-4046-9656-a42a404c3343` |
| `name` | String (255) | Dataset name | `"bakbot_BM2 Dataset"` |
| `description` | Text | Dataset description | `"Experimental dataset from spacing study"` |
| `n_subjects` | Integer | Number of participants | `45` |
| `n_items` | Integer | Number of food items rated | `120` |
| `rating_scale_min` | Float | Minimum value on rating scale | `0.0` |
| `rating_scale_max` | Float | Maximum value on rating scale | `3.0` |
| `rating_scale_type` | String (50) | Type of rating scale | `"likert"`, `"visual_analog"`, `"hedonic"` |
| `data_completeness` | Float | Percentage of complete responses | `95.5` |
| `file_format` | String (20) | Original data file format | `"csv"`, `"xlsx"`, `"sav"` |
| `file_size_mb` | Float | File size in megabytes | `2.3` |
| `osf_file_id` | String (50) | OSF file identifier | `"abc789"` |
| `created_at` | DateTime | Record creation timestamp | `2024-01-15T10:30:00Z` |
| `updated_at` | DateTime | Last update timestamp | `2024-01-15T10:30:00Z` |

---

## Table: Items

Contains information about food items that were rated across studies.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | String (UUID) | Unique identifier for the food item | `dcb33fdc-d03c-40ae-a218-5d93c2109a25` |
| `name` | String (255) | Original food item name | `"100grandsmall"`, `"chocolate chip cookies"` |
| `standardized_name` | String (255) | Normalized name for matching | `"100grandsmall"`, `"chocolate_chip_cookies"` |
| `category` | String (100) | Food category | `"sweets"`, `"chips"`, `"fruits"`, `"vegetables"` |
| `subcategory` | String (100) | Subcategory (optional) | `"candy_bars"`, `"salty_snacks"` |
| `description` | Text | Item description | `"Small 100 Grand candy bar"` |
| `image_available` | Boolean | Whether image is available | `true`, `false` |
| `image_url` | String (500) | URL to food item image | `"https://example.com/images/item123.jpg"` |
| `frequency` | Integer | Number of datasets including this item | `15` |
| `aliases` | JSON Array | Alternative names for the item | `["100 Grand", "hundred grand"]` |
| `nutritional_info` | Text | Nutritional information (JSON) | `{"calories": 190, "fat": 8}` |
| `created_at` | DateTime | Record creation timestamp | `2024-01-15T10:30:00Z` |
| `updated_at` | DateTime | Last update timestamp | `2024-01-15T10:30:00Z` |

### Food Categories

Common food categories used in the database:

- **sweets**: Candies, chocolate, desserts
- **chips**: Potato chips, corn chips, snack chips  
- **crackers**: Cheese crackers, graham crackers
- **fruits**: Fresh and processed fruits
- **vegetables**: Fresh and processed vegetables
- **beverages**: Soft drinks, juices, water
- **main_dishes**: Pizza, sandwiches, meals
- **frozen_desserts**: Ice cream, frozen yogurt
- **nuts**: Nuts, seeds, trail mix
- **other**: Items not fitting other categories

---

## Table: Ratings

Contains individual preference ratings from study participants.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | String (UUID) | Unique identifier for the rating | `a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6` |
| `dataset_id` | String (UUID) | Foreign key to Datasets table | `5b519977-e395-43c6-9aea-0aa6255ec4d4` |
| `item_id` | String (UUID) | Foreign key to Items table | `dcb33fdc-d03c-40ae-a218-5d93c2109a25` |
| `subject_id` | String | Participant identifier within dataset | `"654"`, `"subject_001"` |
| `rating` | Float | Original rating value | `2.5`, `7.3` |
| `normalized_rating` | Float | Rating normalized to 0-1 scale | `0.83`, `0.73` |
| `response_time` | Float | Response time in seconds (optional) | `2.3` |
| `session_id` | String (100) | Testing session identifier | `"session_2024_01_15"` |
| `order_presented` | Integer | Order item was presented | `5` |
| `demographic_data` | Text | Participant demographics (JSON) | `{"age": 25, "gender": "F"}` |
| `created_at` | DateTime | Record creation timestamp | `2024-01-15T10:30:00Z` |

### Rating Scale Normalization

All ratings are normalized to a 0-1 scale for cross-study comparisons:

- **Formula**: `normalized_rating = (rating - scale_min) / (scale_max - scale_min)`
- **0.0**: Lowest possible rating (strongly dislike)
- **1.0**: Highest possible rating (strongly like)
- **0.5**: Neutral/middle rating

### Original Rating Scales

The database includes data from various rating scales:

| Scale | Min | Max | Description |
|-------|-----|-----|-------------|
| `0_to_3` | 0 | 3 | 4-point Likert scale |
| `0_to_10` | 0 | 10 | 11-point scale |
| `1_to_4` | 1 | 4 | 4-point scale starting at 1 |
| `-10_to_10` | -10 | 10 | Bipolar 21-point scale |
| `1_to_9` | 1 | 9 | 9-point hedonic scale |

---

## Table: Download_Logs

Tracks data downloads for analytics and usage monitoring.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | String (UUID) | Unique identifier for download | `f1e2d3c4-b5a6-9c8d-7e6f-5a4b3c2d1e0f` |
| `dataset_ids` | JSON Array | List of downloaded dataset IDs | `["id1", "id2", "id3"]` |
| `download_format` | String (20) | Requested file format | `"csv"`, `"json"`, `"spss"`, `"excel"` |
| `file_size_mb` | Float | Download file size | `45.7` |
| `download_url` | String (500) | Temporary download URL | `"https://example.com/downloads/abc123"` |
| `expires_at` | DateTime | URL expiration time | `2024-01-16T10:30:00Z` |
| `user_ip` | String (45) | User IP address (anonymized) | `"192.168.1.xxx"` |
| `user_agent` | Text | Browser/client information | `"Mozilla/5.0 (Windows NT 10.0..."` |
| `created_at` | DateTime | Download timestamp | `2024-01-15T10:30:00Z` |

---

## Table: Search_Logs

Tracks search queries for improving search functionality.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | String (UUID) | Unique identifier for search | `9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d` |
| `query` | String (500) | Search query text | `"chocolate preferences"` |
| `filters` | Text | Applied filters (JSON) | `{"category": "sweets", "year": [2020, 2023]}` |
| `results_count` | Integer | Number of results returned | `127` |
| `user_ip` | String (45) | User IP address (anonymized) | `"192.168.1.xxx"` |
| `created_at` | DateTime | Search timestamp | `2024-01-15T10:30:00Z` |

---

## Data Quality and Completeness

### Data Validation

All imported data undergoes validation:

- **Rating values**: Must be within the specified scale range
- **Subject IDs**: Must be unique within each dataset
- **Item names**: Standardized and categorized
- **Duplicate detection**: Removes duplicate ratings

### Missing Data Handling

- **Empty ratings**: Excluded from import
- **Invalid scales**: Default to 0-10 scale if unspecified
- **Missing metadata**: Uses reasonable defaults

### Data Lineage

Each record includes:
- **Source tracking**: Original study and dataset
- **Import timestamp**: When data was added
- **Processing notes**: Any transformations applied

---

## Usage Notes

### For Researchers

1. **Cross-study comparisons**: Use `normalized_rating` for comparisons across different rating scales
2. **Study filtering**: Filter by `year`, `journal`, or `authors` to focus on specific research
3. **Item analysis**: Use `category` and `frequency` to analyze food preferences by type
4. **Sample sizes**: Check `n_subjects` and `n_items` for statistical power considerations

### For Developers

1. **Primary keys**: All tables use UUID primary keys
2. **Foreign keys**: Maintain referential integrity across tables
3. **Indexes**: Optimized for common query patterns
4. **JSON fields**: Use appropriate JSON parsing for `authors`, `aliases`, etc.

### Data Citation

When using this database, please cite:
- The original studies (available in `Studies.name` and `Studies.doi`)
- This database compilation
- Specific datasets used in your analysis

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-01-15 | Initial database schema and data import |
| 1.1 | 2024-02-01 | Added nutritional information fields |
| 1.2 | 2024-03-01 | Enhanced search and download tracking |

---

## Contact

For questions about the data dictionary or database schema:
- Email: support@likingdatabase.org
- GitHub Issues: [Project Issues](https://github.com/kiante-fernandez/liking-rating-database/issues)
- Documentation: [Development Guide](DEVELOPMENT.md)