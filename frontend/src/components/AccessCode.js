import React, { useState } from 'react';
import { Card, Tabs, Button, message, Typography } from 'antd';
import { CopyOutlined } from '@ant-design/icons';

const { Text } = Typography;

// The API base the generated snippets should point at. Snippets are meant to
// be pasted into a terminal, so they need an absolute URL — the relative
// '/api/v1' the app itself uses would not resolve outside the browser.
const apiBase = () => {
  const configured = process.env.REACT_APP_API_URL;
  if (configured && /^https?:\/\//i.test(configured)) return configured;
  return `${window.location.origin}/api/v1`;
};

const codeStyle = {
  margin: 0,
  padding: '12px 14px',
  background: '#f5f5f5',
  borderRadius: 6,
  fontSize: 13.5,
  lineHeight: 1.55,
  overflowX: 'auto',
  fontFamily: "source-code-pro, Menlo, Monaco, Consolas, 'Courier New', monospace",
};

const CodeBlock = ({ code }) => {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      message.success('Copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      message.error('Could not copy — select the text and copy manually');
    }
  };

  return (
    <div style={{ position: 'relative' }}>
      <Button
        size="small"
        icon={<CopyOutlined />}
        onClick={copy}
        style={{ position: 'absolute', top: 8, right: 8, zIndex: 1 }}
      >
        {copied ? 'Copied' : 'Copy'}
      </Button>
      <pre style={codeStyle}>{code}</pre>
    </div>
  );
};

/**
 * Copy-paste code to pull data, in the two languages this field actually
 * uses. Every snippet runs against the live read-only API — the Python one
 * through the `likingdb` client in clients/python, the R one through plain
 * jsonlite, since there is no R package yet.
 *
 * Pass a `dataset` ({ id, name }) for dataset-scoped code, or nothing for
 * whole-database code.
 */
const AccessCode = ({ dataset, title = 'Get this data in R or Python' }) => {
  const base = apiBase();
  // Dataset names are stored as "leeholyoak2021 Dataset"; the client resolves
  // either the code or the UUID, and the code reads better in an example.
  const code = dataset ? String(dataset.name).replace(/\s+Dataset$/i, '') : null;

  const python = dataset
    ? `# pip install -e clients/python
import likingdb
likingdb.set_base_url("${base}")

ratings = likingdb.load_ratings("${code}")
print(ratings.shape)
print(ratings.head())

# Cross-study comparisons must use normalized_rating (0-1), not rating
print(ratings.groupby("item_name").normalized_rating.mean().nlargest(10))

print(likingdb.cite("${code}"))`
    : `# pip install -e clients/python
import likingdb
likingdb.set_base_url("${base}")

db = likingdb.load_database()          # one request, the whole corpus
ratings = db["ratings"]                # 700,943 rows
print(ratings.shape)
print(db["codebook"])

# Cross-study comparisons must use normalized_rating (0-1), not rating
print(ratings.groupby("item_name").normalized_rating.mean().nlargest(10))`;

  const r = dataset
    ? `library(jsonlite)
base <- "${base}"

# Page through this dataset's ratings
page <- fromJSON(paste0(base, "/ratings?dataset_id=${dataset.id}&page_size=1000"))
ratings <- page$items
while (page$page < page$pages) {
  page <- fromJSON(paste0(base, "/ratings?dataset_id=${dataset.id}",
                          "&page_size=1000&page=", page$page + 1))
  ratings <- rbind(ratings, page$items)
}
nrow(ratings)

# Cross-study comparisons must use normalized_rating (0-1), not rating
aggregate(normalized_rating ~ item_name, ratings, mean)`
    : `library(jsonlite)
base <- "${base}"

# The whole database in one download: ratings + metadata + codebook
tmp <- tempfile(fileext = ".zip")
download.file(paste0(base, "/database/archive"), tmp, mode = "wb")
dir <- tempfile(); dir.create(dir); unzip(tmp, exdir = dir)

ratings <- read.csv(file.path(dir, "liking_rating_database", "ratings.csv"),
                    colClasses = c(subject_id = "character"))
nrow(ratings)   # 700943

# Cross-study comparisons must use normalized_rating (0-1), not rating
aggregate(normalized_rating ~ item_name, ratings, mean)`;

  return (
    <Card title={title} size="small" style={{ marginBottom: 24 }}>
      <Tabs
        size="small"
        items={[
          { key: 'python', label: 'Python', children: <CodeBlock code={python} /> },
          { key: 'r', label: 'R', children: <CodeBlock code={r} /> },
        ]}
      />
      <Text type="secondary" style={{ fontSize: 12 }}>
        Subject IDs are unique only within a dataset — key on{' '}
        <Text code>(dataset_id, subject_id)</Text>. Please cite the source
        study alongside the database.
      </Text>
    </Card>
  );
};

export default AccessCode;
