import React from 'react';
import { Link } from 'react-router-dom';
import { Card, Typography, Table, Anchor, Row, Col, Tag, Space } from 'antd';
import { useQuery } from 'react-query';
import AccessCode from '../components/AccessCode';
import { getStatistics, getScaleTypes } from '../services/api';

const { Title, Paragraph, Text } = Typography;

const ratingsColumns = [
  { title: 'Column', dataIndex: 'col', key: 'col', render: (v) => <Text code>{v}</Text> },
  { title: 'Type', dataIndex: 'type', key: 'type' },
  { title: 'Description', dataIndex: 'desc', key: 'desc' },
];

const ratingsFields = [
  { key: 1, col: 'dataset_id', type: 'string', desc: 'Which dataset the rating belongs to' },
  { key: 2, col: 'study_id', type: 'string', desc: 'Which publication the dataset came from' },
  { key: 3, col: 'subject_id', type: 'string', desc: 'Subject identifier — unique only within a dataset' },
  { key: 4, col: 'item_id', type: 'string', desc: 'Which stimulus was rated' },
  { key: 5, col: 'item_name', type: 'string', desc: 'Stimulus name, harmonized across studies' },
  { key: 6, col: 'timepoint', type: 'integer', desc: 'Repeated rating phase (1 = first or only)' },
  { key: 7, col: 'rating', type: 'float', desc: "Value in the study's own scale units" },
  { key: 8, col: 'normalized_rating', type: 'float', desc: '(rating − min) / (max − min), always 0–1' },
];

const endpointColumns = [
  { title: 'Endpoint', dataIndex: 'ep', key: 'ep', render: (v) => <Text code>{v}</Text> },
  { title: 'Returns', dataIndex: 'ret', key: 'ret' },
];

const endpoints = [
  { key: 1, ep: 'GET /studies', ret: 'Publications, paginated' },
  { key: 2, ep: 'GET /studies/{id}', ret: 'One publication and its datasets' },
  { key: 3, ep: 'GET /datasets', ret: 'Datasets, paginated' },
  { key: 4, ep: 'GET /datasets/{id}', ret: 'One dataset, its study, and its rating count' },
  { key: 5, ep: 'GET /items', ret: 'Stimuli, paginated and filterable by category' },
  { key: 6, ep: 'GET /ratings', ret: 'Ratings, filterable by dataset and item' },
  { key: 7, ep: 'GET /ratings/aggregate', ret: 'Per-item means, SDs, and counts' },
  { key: 8, ep: 'POST /search', ret: 'Datasets matching a query and filters' },
  { key: 9, ep: 'GET /statistics', ret: 'Database-wide totals' },
  { key: 10, ep: 'GET /descriptives/dataset-item', ret: 'Distribution of one item in one dataset' },
  { key: 11, ep: 'GET /descriptives/items/{id}', ret: 'One item summarised across every dataset' },
  { key: 15, ep: 'GET /descriptives/items/{id}/similar', ret: 'Items rated similarly by the same people' },
  { key: 12, ep: 'GET /analytics/item-network', ret: 'Item co-occurrence network with a layout' },
  { key: 13, ep: 'POST /download', ret: 'Build a csv/json/xlsx/spss export' },
  { key: 14, ep: 'GET /database/archive', ret: 'The whole database as one ZIP + codebook' },
];

const DocumentationPage = () => {
  const { data: stats } = useQuery('statistics', getStatistics);
  const { data: scaleTypes } = useQuery('scale-types', getScaleTypes);

  return (
    <Row gutter={24}>
      <Col xs={24} lg={19}>
        <Title level={2}>Documentation</Title>
        <Paragraph type="secondary" style={{ maxWidth: 720 }}>
          How the database is structured, what the columns mean, and how to get
          the data into R or Python.
        </Paragraph>

        <Card id="overview" title="What's in the database" style={{ marginBottom: 24 }}>
          <Paragraph>
            {stats ? (
              <>
                <strong>{stats.total_ratings.toLocaleString()}</strong> liking
                ratings from <strong>{stats.total_studies}</strong> studies (
                <strong>{stats.total_datasets}</strong> datasets) covering{' '}
                <strong>{stats.total_items.toLocaleString()}</strong> food and
                consumer-product stimuli, published{' '}
                {stats.year_range?.[0]}–{stats.year_range?.[1]}.
              </>
            ) : (
              'Loading database statistics…'
            )}
          </Paragraph>
          <Paragraph>
            A <strong>study</strong> is a publication. A study contributes one
            or more <strong>datasets</strong> (experiments or samples). Each
            dataset holds <strong>ratings</strong>: one row per subject × item
            × timepoint. <strong>Items</strong> are stimuli, shared across
            studies wherever the same food or product was rated — that sharing
            is what makes cross-study comparison possible.
          </Paragraph>
          <Paragraph style={{ marginBottom: 0 }}>
            Response scales in use:{' '}
            <Space size={4} wrap>
              {(scaleTypes?.scale_types ?? []).map((t) => (
                <Tag key={t} color="blue">{t}</Tag>
              ))}
            </Space>
          </Paragraph>
        </Card>

        <Card id="ratings" title="The ratings table" style={{ marginBottom: 24 }}>
          <Table
            size="small"
            pagination={false}
            columns={ratingsColumns}
            dataSource={ratingsFields}
            scroll={{ x: 'max-content' }}
          />
          <Title level={5} style={{ marginTop: 24 }}>Repeated rating phases</Title>
          <Paragraph>
            Most datasets hold one rating per (subject, item) and every row is{' '}
            <Text code>timepoint = 1</Text>. Two datasets repeat the whole
            rating phase, so the same subjects rate the same items more than
            once:
          </Paragraph>
          <ul>
            <li><Text code>leeholyoak2021</Text> — phases 1, 2, 3</li>
            <li><Text code>leehare2023exp2</Text> — phases 1, 2</li>
          </ul>
          <Paragraph>
            For those, <Text code>(dataset_id, subject_id, item_id)</Text> is{' '}
            <strong>not</strong> unique — include{' '}
            <Text code>timepoint</Text> in your key. Every download format
            carries the column. Three further datasets (
            <Text code>toyam</Text>, <Text code>romfred</Text>,{' '}
            <Text code>brusaeb</Text>) had unstructured repeats in their source
            files and store the per-subject mean at timepoint 1.
          </Paragraph>
          <Paragraph style={{ marginBottom: 0 }}>
            You can see the effect of the phases on the{' '}
            <Link to="/descriptives">Descriptives</Link> page, which has a
            phase selector for those two datasets.
          </Paragraph>
        </Card>

        <Card id="gotchas" title="Two things to get right" style={{ marginBottom: 24 }}>
          <Title level={5} style={{ marginTop: 0 }}>
            Cross-study comparisons must use <Text code>normalized_rating</Text>
          </Title>
          <Paragraph>
            Studies use different response scales — 0–4, 1–100, 1–870,
            willingness-to-pay in dollars. Raw <Text code>rating</Text> values
            are not comparable across datasets.{' '}
            <Text code>normalized_rating</Text> is{' '}
            <Text code>(rating − scale_min) / (scale_max − scale_min)</Text> and
            always lies in 0–1.
          </Paragraph>

          <Title level={5}>Subject IDs are unique only within a dataset</Title>
          <Paragraph style={{ marginBottom: 0 }}>
            Subject <Text code>&quot;12&quot;</Text> in one dataset and subject{' '}
            <Text code>&quot;12&quot;</Text> in another are different people.
            Always key on <Text code>(dataset_id, subject_id)</Text>. Reading
            subject IDs as numbers will also drop leading zeros — keep them as
            strings.
          </Paragraph>
        </Card>

        <div id="access">
          <AccessCode title="Downloading the data" />
        </div>

        <Card id="api" title="REST API" style={{ marginBottom: 24 }}>
          <Paragraph>
            The API is <strong>read-only by design</strong> — all data changes
            go through versioned migrations. List endpoints return{' '}
            <Text code>{'{items, total, page, page_size, pages}'}</Text>.
            Interactive docs live at <Text code>/api/v1/docs</Text>.
          </Paragraph>
          <Table
            size="small"
            pagination={false}
            columns={endpointColumns}
            dataSource={endpoints}
            scroll={{ x: 'max-content' }}
          />
        </Card>

        <Card id="similarity" title="Preference similarity" style={{ marginBottom: 24 }}>
          <Paragraph>
            The Descriptives page ranks items by <strong>preference</strong>{' '}
            similarity: two items are close when the people who rated both
            tended to like them together. It says nothing about the items&apos;
            names or descriptions — only about how they were rated.
          </Paragraph>
          <Paragraph>
            For each dataset containing the target item, ratings are{' '}
            <strong>person-centred</strong> (each subject&apos;s mean across
            the items they rated is subtracted), then Pearson correlated over
            the subjects who rated both items. Per-dataset correlations are
            combined with Fisher&apos;s <Text code>z</Text>, weighted by{' '}
            <Text code>n − 3</Text>.
          </Paragraph>
          <p className="page-note">
            <strong>Why person-centring is not optional here.</strong> Without
            it, two items correlate merely because some people rate everything
            highly and others rate everything low — a response-style effect,
            not shared preference. In <Text code>foljac2</Text> that artifact
            is total: each subject&apos;s ratings span about 0.006 while
            subject means span about 0.6, so uncentred, every pair of items in
            that dataset correlates at r = 1.00.
          </p>
          <Paragraph style={{ marginBottom: 0 }}>
            Two consequences worth knowing. Centring makes each subject&apos;s
            row sum to zero, which biases correlations down by roughly{' '}
            <Text code>−1/(k − 1)</Text> for <Text code>k</Text> items — under
            −0.02 at the 60–144 items typical here, but exactly −1 at{' '}
            <Text code>k = 2</Text>, so datasets with fewer than 20 items are
            skipped. And a pair needs at least 10 shared raters within a
            dataset to contribute at all, so a high{' '}
            <Text code>r</Text> on few raters never outranks a solid one on
            many.
          </Paragraph>
        </Card>

        <Card id="categories" title="Item categories" style={{ marginBottom: 24 }}>
          <Paragraph style={{ marginBottom: 0 }}>
            Item categories are derived from item names by a curated lexicon —
            they are not author-assigned ground truth. They are good enough to
            filter and group by, but check them before treating them as data.
            178 items whose source files carried opaque codes (
            <Text code>0488</Text>, <Text code>mh0021</Text>) are categorised{' '}
            <Text code>unknown</Text>.
          </Paragraph>
        </Card>

        <Card id="citing" title="Citing" style={{ marginBottom: 24 }}>
          <Paragraph>
            Please cite both the database and the original studies whose data
            you use. Every study page carries its citation, DOI, and a BibTeX
            generator; <Text code>studies.csv</Text> in the archive carries
            them for every study at once.
          </Paragraph>
          <pre style={{
            margin: 0, padding: '12px 14px', background: '#f5f5f5',
            borderRadius: 6, fontSize: 12.5, whiteSpace: 'pre-wrap',
          }}>
{`Fernandez, K., Goyal, S., & Krajbich, I. A database of subjective
evaluation ratings for decision-making research. (In preparation.)`}
          </pre>
        </Card>

        <Card id="contributing" title="Contributing a dataset" style={{ marginBottom: 24 }}>
          <Paragraph style={{ marginBottom: 0 }}>
            New datasets enter through a standardized ingestion script that
            records what it did in the database's migration log, so every row
            is traceable to a source file. The process, the required columns,
            and the metadata a submission needs are documented in{' '}
            <Text code>docs/ADDING_DATASETS.md</Text> in the project
            repository. Open an issue there to propose a dataset.
          </Paragraph>
        </Card>
      </Col>

      <Col xs={0} lg={5}>
        <Anchor
          style={{ position: 'sticky', top: 24 }}
          items={[
            { key: 'overview', href: '#overview', title: "What's in the database" },
            { key: 'ratings', href: '#ratings', title: 'The ratings table' },
            { key: 'gotchas', href: '#gotchas', title: 'Two things to get right' },
            { key: 'access', href: '#access', title: 'Downloading the data' },
            { key: 'api', href: '#api', title: 'REST API' },
            { key: 'similarity', href: '#similarity', title: 'Preference similarity' },
            { key: 'categories', href: '#categories', title: 'Item categories' },
            { key: 'citing', href: '#citing', title: 'Citing' },
            { key: 'contributing', href: '#contributing', title: 'Contributing' },
          ]}
        />
      </Col>
    </Row>
  );
};

export default DocumentationPage;
