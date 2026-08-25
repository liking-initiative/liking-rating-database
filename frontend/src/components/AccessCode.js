import React, { useState } from 'react';
import { Card, Tabs, Button, message, Typography } from 'antd';
import { CopyOutlined } from '@ant-design/icons';

const { Text } = Typography;

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
 * uses. Both go through the `likingInitiative` packages, which read versioned
 * release files rather than this API — so an analysis pins a version and
 * keeps working whether or not this service is up.
 *
 * Pass a `dataset` ({ id, name }) for dataset-scoped code, or nothing for
 * whole-database code.
 */
const AccessCode = ({ dataset, title = 'Get this data in R or Python' }) => {
  // Dataset names are stored as "leeholyoak2021 Dataset"; the client resolves
  // either the code or the UUID, and the code reads better in an example.
  const code = dataset ? String(dataset.name).replace(/\s+Dataset$/i, '') : null;

  const python = dataset
    ? `# pip install likingInitiative
import likingInitiative as lk

d = lk.get_dataset("${code}")
d.data                     # polars DataFrame
d.scale, d.timepoints      # response scale, rating phases

# Cross-study comparisons must use normalized_rating, not rating
d.data.group_by("item_name").agg(
    pl.col("normalized_rating").mean()
).sort("normalized_rating", descending=True).head(10)

print(d.cite())`
    : `# pip install likingInitiative
import likingInitiative as lk

db = lk.load_database()    # the whole corpus, one download
db["ratings"]              # 700,943 rows

# One item across every study that used it
lk.get_item("kitkat").by_dataset()

# Cross-study comparisons must use normalized_rating, not rating`;

  const r = dataset
    ? `# devtools::install_github(
#   "kiante-fernandez/liking-rating-database", subdir = "clients/r")
library(likingInitiative)

d <- get_dataset("${code}")
head(d$data)
d$metadata$rating_scale_max

# Cross-study comparisons must use normalized_rating, not rating
aggregate(normalized_rating ~ item_name, d$data, mean)

cite(d)`
    : `# devtools::install_github(
#   "kiante-fernandez/liking-rating-database", subdir = "clients/r")
library(likingInitiative)

db <- load_database()      # the whole corpus, one download
nrow(db$ratings)           # 700943

# One item across every study that used it
k <- get_item("kitkat")
aggregate(normalized_rating ~ dataset_code, k$data, mean)`;

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
