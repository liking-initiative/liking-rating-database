import React from 'react';
import { Link } from 'react-router-dom';
import { Card, Typography, Table, Anchor, Row, Col, Tag, Space } from 'antd';
import { useQuery } from 'react-query';
import AccessCode from '../components/AccessCode';
import { getStatistics, getScaleTypes } from '../services/api';

const { Title, Paragraph, Text } = Typography;

// Edit this file to change the Documentation page. Prose lives in the JSX
// below; the two tables are the arrays that follow. Keep the numbers that
// come from the API (stats, scale types) as they are, so they stay current.

const REPO = 'https://github.com/liking-initiative/liking-rating-database';
const R_REPO = 'https://github.com/liking-initiative/likingInitiative-r';
const PY_REPO = 'https://github.com/liking-initiative/likingInitiative-py';
const DOI = 'https://doi.org/10.5281/zenodo.22216442';

const ratingsColumns = [
  { title: 'Column', dataIndex: 'col', key: 'col', render: (v) => <Text code>{v}</Text> },
  { title: 'Type', dataIndex: 'type', key: 'type' },
  { title: 'Description', dataIndex: 'desc', key: 'desc' },
];

const ratingsFields = [
  { key: 1, col: 'dataset_id', type: 'string', desc: 'The dataset the rating belongs to' },
  { key: 2, col: 'subject_id', type: 'string', desc: 'Participant identifier. Unique only within a dataset' },
  { key: 3, col: 'item_id', type: 'string', desc: 'The stimulus that was rated' },
  { key: 4, col: 'item_name', type: 'string', desc: 'Stimulus name, harmonized across studies' },
  { key: 5, col: 'timepoint', type: 'integer', desc: 'Rating phase. 1 is the first or only phase' },
  { key: 6, col: 'rating', type: 'float', desc: "The value in the study's own scale units" },
  { key: 7, col: 'normalized_rating', type: 'float', desc: '(rating - min) / (max - min), always between 0 and 1' },
];

const endpointColumns = [
  { title: 'Endpoint', dataIndex: 'ep', key: 'ep', render: (v) => <Text code>{v}</Text> },
  { title: 'Returns', dataIndex: 'ret', key: 'ret' },
];

const endpoints = [
  { key: 1, ep: 'GET /studies', ret: 'Studies, paginated' },
  { key: 2, ep: 'GET /studies/{id}', ret: 'One study and its datasets' },
  { key: 3, ep: 'GET /datasets', ret: 'Datasets, paginated' },
  { key: 4, ep: 'GET /datasets/{id}', ret: 'One dataset, its study, and its rating count' },
  { key: 5, ep: 'GET /items', ret: 'Stimuli, paginated and searchable by name' },
  { key: 6, ep: 'GET /items/{id}', ret: 'One stimulus' },
  { key: 7, ep: 'GET /items/{id}/ratings/by-dataset', ret: 'One stimulus summarised in each dataset that used it' },
  { key: 8, ep: 'GET /ratings', ret: 'Ratings, filterable by dataset and item' },
  { key: 9, ep: 'GET /ratings/aggregate', ret: 'Per-item means, standard deviations, and counts' },
  { key: 10, ep: 'POST /search', ret: 'Datasets matching a query and filters' },
  { key: 11, ep: 'GET /search/suggestions', ret: 'Name completions for the search box' },
  { key: 12, ep: 'GET /statistics', ret: 'Database-wide totals' },
  { key: 13, ep: 'GET /metadata/scale-types', ret: 'Response scale types in use (also /categories, /years)' },
  { key: 14, ep: 'GET /descriptives/index', ret: 'Which items have descriptives in which datasets' },
  { key: 15, ep: 'GET /descriptives/dataset-item', ret: 'Distribution of one item in one dataset' },
  { key: 16, ep: 'GET /descriptives/items/{id}', ret: 'One item across every dataset that used it' },
  { key: 17, ep: 'GET /descriptives/items/{id}/similar', ret: 'Items rated similarly by the same people' },
  { key: 18, ep: 'GET /analytics/item-network', ret: 'The item co-occurrence network with a layout' },
  { key: 19, ep: 'GET /analytics/dataset-network/{id}', ret: "One dataset's preference network" },
  { key: 20, ep: 'POST /download', ret: 'Build a csv, json, xlsx or spss export' },
  { key: 21, ep: 'GET /database/archive', ret: 'The whole database as one zip with a codebook' },
];

const pre = {
  margin: 0, padding: '12px 14px', background: '#f5f5f5',
  borderRadius: 6, fontSize: 13.5, whiteSpace: 'pre-wrap',
};

const DocumentationPage = () => {
  const { data: stats } = useQuery('statistics', getStatistics);
  const { data: scaleTypes } = useQuery('scale-types', getScaleTypes);

  return (
    <Row gutter={24}>
      <Col xs={24} lg={19}>
        <Title level={2}>Documentation</Title>
        <Paragraph type="secondary" style={{ maxWidth: 720 }}>
          What the database contains, how it is structured, what the columns
          mean, and how to get the data into R or Python.
        </Paragraph>

        <Card id="overview" title="What the Liking Initiative is" style={{ marginBottom: 24 }}>
          <Paragraph>
            The Liking Initiative is a database of subjective value ratings
            collected from value-based decision-making studies. Each study asked
            participants how much they liked, wanted, or would pay for
            individual items, on the scale that suited that study. The database
            keeps the ratings in their original units, records how each was
            elicited, and adds a normalized value so ratings from different
            studies can be compared.
          </Paragraph>
          <Paragraph>
            {stats ? (
              <>
                <strong>{stats.total_ratings.toLocaleString()}</strong> ratings
                from <strong>{stats.total_studies}</strong> studies (
                <strong>{stats.total_datasets}</strong> datasets) covering{' '}
                <strong>{stats.total_items.toLocaleString()}</strong> food and
                consumer-product stimuli, published{' '}
                {stats.year_range?.[0]} to {stats.year_range?.[1]}.
              </>
            ) : (
              'Loading database statistics.'
            )}
          </Paragraph>
          <Paragraph>
            A <strong>study</strong> is a publication or, for a few unpublished
            collections, a lab dataset with a citation. A study contributes one
            or more <strong>datasets</strong>, usually one per experiment or
            sample. Each dataset holds <strong>ratings</strong>: one row per
            participant, item, and rating phase. <strong>Items</strong> are the
            stimuli. The same food or product rated in several studies is one
            item, which is what allows a comparison across studies.
          </Paragraph>
          <Paragraph style={{ marginBottom: 0 }}>
            Response scale types in use:{' '}
            <Space size={4} wrap>
              {(scaleTypes?.scale_types ?? []).map((t) => (
                <Tag key={t} color="blue">{t}</Tag>
              ))}
            </Space>
          </Paragraph>
        </Card>

        <Card id="construct" title="What was measured" style={{ marginBottom: 24 }}>
          <Paragraph>
            Most datasets asked participants how much they liked or wanted
            each item. Willingness-to-pay datasets recorded a bid in currency
            instead, and their ratings are in dollars or pounds. Two datasets,{' '}
            <Text code>larlua</Text> and <Text code>xuefoe</Text>, asked about
            tastiness rather than liking.
          </Paragraph>
          <Paragraph style={{ marginBottom: 0 }}>
            The exact question and scale for every dataset, with the sentence
            from the paper or the raw data file that establishes it, is in{' '}
            <a href={`${REPO}/blob/main/docs/SCALE_VERIFICATION.md`} target="_blank" rel="noreferrer">
              docs/SCALE_VERIFICATION.md
            </a>
            . The same document ships inside every release, so a downloaded
            copy carries its own record. Read it before treating two datasets
            as measuring the same thing.
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
          <Paragraph style={{ marginTop: 16 }}>
            These are the columns the API returns for a rating. Exports and the
            packages add the dataset and study metadata alongside them.
          </Paragraph>
          <Title level={5} style={{ marginTop: 24 }}>Repeated rating phases</Title>
          <Paragraph>
            Most datasets hold one rating per participant and item, and every
            row has <Text code>timepoint = 1</Text>. Some datasets repeat the
            whole rating phase, so the same participants rated the same items
            more than once:
          </Paragraph>
          <ul>
            <li><Text code>leeholyoak2021</Text> and <Text code>crosswebb</Text>: three phases</li>
            <li>
              <Text code>leehare2023exp2</Text>, <Text code>hamesmcc</Text>,{' '}
              <Text code>chenhol1</Text> and <Text code>chenhol2</Text>: two phases
            </li>
          </ul>
          <Paragraph>
            For those six, <Text code>(dataset_id, subject_id, item_id)</Text>{' '}
            is <strong>not</strong> unique. Include <Text code>timepoint</Text>{' '}
            in your key, or take one phase. Every download format carries the
            column. Three further datasets (<Text code>toyam</Text>,{' '}
            <Text code>romfred</Text>, <Text code>sucro</Text>) had unstructured
            repeats in their source files and hold the per-participant mean at
            timepoint 1.
          </Paragraph>
          <Paragraph style={{ marginBottom: 0 }}>
            The <Link to="/descriptives">Descriptives</Link> page has a phase
            selector for any dataset with more than one phase.
          </Paragraph>
        </Card>

        <Card id="gotchas" title="Two things to get right" style={{ marginBottom: 24 }}>
          <Title level={5} style={{ marginTop: 0 }}>
            Cross-study comparisons must use <Text code>normalized_rating</Text>
          </Title>
          <Paragraph>
            Studies used different response scales: 0 to 4, 1 to 100, 1 to 870,
            willingness-to-pay in dollars. Raw <Text code>rating</Text> values
            are not comparable across datasets.{' '}
            <Text code>normalized_rating</Text> is{' '}
            <Text code>(rating - scale_min) / (scale_max - scale_min)</Text> and
            always lies between 0 and 1.
          </Paragraph>

          <Title level={5}>Subject IDs are unique only within a dataset</Title>
          <Paragraph style={{ marginBottom: 0 }}>
            Subject <Text code>&quot;12&quot;</Text> in one dataset and subject{' '}
            <Text code>&quot;12&quot;</Text> in another are different people.
            Always key on <Text code>(dataset_id, subject_id)</Text>. Reading
            subject IDs as numbers also drops leading zeros, so keep them as
            strings.
          </Paragraph>
        </Card>

        <Card id="provenance" title="Data provenance and quality" style={{ marginBottom: 24 }}>
          <Paragraph>
            The API is read-only. Every change to the data is a numbered
            migration that checks its own assumptions, records what it did, and
            can be read back. The migration log ships with each release, so a
            downloaded copy states which corrections it includes.
          </Paragraph>
          <Paragraph>
            Item names were harmonized, so that the same food
            under different spellings is one item. Names that appear together
            in the same dataset are kept distinct, because a study that rated
            both meant two things by them.
          </Paragraph>
          <Paragraph style={{ marginBottom: 0 }}>
            The per-dataset audit is{' '}
            <a href={`${REPO}/blob/main/docs/DATASET_AUDIT.md`} target="_blank" rel="noreferrer">
              docs/DATASET_AUDIT.md
            </a>
            . Datasets that exist in the source compilation but are not yet
            imported, and what would unblock each, are listed in{' '}
            <a href={`${REPO}/blob/main/ISSUES.md`} target="_blank" rel="noreferrer">ISSUES.md</a>.
          </Paragraph>
        </Card>

        <Card id="packages" title="The R and Python packages" style={{ marginBottom: 24 }}>
          <Paragraph>
            Two packages give the same access to the database from R and from
            Python. The Python package is on PyPI; the R package installs from
            GitHub until it is accepted on CRAN. They do not call this website. They download versioned
            release files from Zenodo, cache them locally, and read from the
            cache, so an analysis that pins a version returns the same rows
            whenever it is run, and keeps working if this site is down.
          </Paragraph>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Title level={5} style={{ marginTop: 0 }}>R</Title>
              <pre style={pre}>{`# install.packages("devtools")
devtools::install_github("liking-initiative/likingInitiative-r")
library(likingInitiative)

list_datasets()
d <- get_dataset("leeholyoak2021")
k <- get_item("kitkat")
db <- load_database()
cite(d); cite()`}</pre>
            </Col>
            <Col xs={24} md={12}>
              <Title level={5} style={{ marginTop: 0 }}>Python</Title>
              <pre style={pre}>{`pip install likingInitiative

import likingInitiative as lk
lk.list_datasets()
d = lk.get_dataset("leeholyoak2021")
k = lk.get_item("kitkat")
db = lk.load_database()
d.cite(); lk.cite()`}</pre>
            </Col>
          </Row>
          <Paragraph style={{ marginTop: 16 }}>
            Both packages accept a <Text code>version</Text> argument. Without
            it they use the newest published version.{' '}
            <Text code>release_info()</Text> reports the version in use, its
            counts, and the migrations it includes. Pin the version in any
            analysis you intend to publish.
          </Paragraph>
          <Paragraph style={{ marginBottom: 0 }}>
            Source, issues and contributing notes:{' '}
            <a href={R_REPO} target="_blank" rel="noreferrer">likingInitiative-r</a> and{' '}
            <a href={PY_REPO} target="_blank" rel="noreferrer">likingInitiative-py</a>.
          </Paragraph>
        </Card>

        <div id="access">
          <AccessCode title="Downloading the data" />
        </div>

        <Card id="api" title="REST API" style={{ marginBottom: 24 }}>
          <Paragraph>
            The API is read-only. Paths below are relative to{' '}
            <Text code>/api/v1</Text>. List endpoints return{' '}
            <Text code>{'{items, total, page, page_size, pages}'}</Text>.
            Interactive documentation is at <Text code>/api/v1/docs</Text>.
          </Paragraph>
          <Table
            size="small"
            pagination={false}
            columns={endpointColumns}
            dataSource={endpoints}
            scroll={{ x: 'max-content' }}
          />
        </Card>

        <Card id="descriptives" title="Descriptives" style={{ marginBottom: 24 }}>
          <Paragraph>
            The Descriptives page reports item-level distributional statistics:
            how one item was rated within a single dataset, and how that
            distribution varies across every dataset that used it.
          </Paragraph>
          <p className="page-note">
            <strong>Before reusing these numbers.</strong> They apply one fixed
            set of choices to every dataset: no exclusions, all available
            participants, and each dataset&apos;s first rating phase unless you
            pick another. Those choices may not match the preprocessing your
            question needs. Download the data and check before publishing.
          </p>
          <Paragraph>
            <strong>Inclusion.</strong> Nothing is filtered out. Every
            participant who rated the item contributes, with no outlier rule
            and no attention-check screen. The exclusions a study applied are
            not recorded here, and applying our own would change what each
            paper reported.
          </Paragraph>
          <Paragraph>
            <strong>Repeated phases.</strong> For the datasets with more
            than one rating phase, only the first phase counts unless you
            select another, so a participant who rated an item three times is
            one observation rather than three.
          </Paragraph>
          <Paragraph style={{ marginBottom: 0 }}>
            <strong>Which scale each statistic is on.</strong> Mean, SD, median,
            IQR and skewness are computed on{' '}
            <Text code>normalized_rating</Text>, so datasets on different
            response scales sit on a common 0 to 1 axis. Floor and ceiling
            proportions are read against each dataset&apos;s own scale, since
            reaching the end of a 1 to 9 Likert scale is a different event from
            reaching the end of a 0 to 870 slider. The Range column is also in
            the dataset&apos;s own units.
          </Paragraph>
        </Card>

        <Card id="similarity" title="Preference similarity" style={{ marginBottom: 24 }}>
          <Paragraph>
            The Descriptives page ranks items by preference similarity: two
            items are close when the people who rated both tended to like them
            together. The measure uses only the ratings, not the items&apos;
            names or descriptions.
          </Paragraph>
          <Paragraph>
            For each dataset containing the target item, ratings are
            person-centred (each participant&apos;s mean across the items they
            rated is subtracted), then Pearson correlated over the participants
            who rated both items. Per-dataset correlations are combined with
            Fisher&apos;s <Text code>z</Text>, weighted by{' '}
            <Text code>n - 3</Text>.
          </Paragraph>
        </Card>

        <Card id="networks" title="Networks" style={{ marginBottom: 24 }}>
          <Title level={5} style={{ marginTop: 0 }}>The item network on the home page</Title>
          <Paragraph>
            Nodes are items. Two items are linked when they were rated in the
            same dataset at least a chosen number of times: 12, 8 or 2 datasets,
            selectable on the page. The network shows which items the studies
            share, and therefore where cross-study comparison is possible. It
            says nothing about how the items were rated. The layout is computed
            once, when the data change, and ships with the database.
          </Paragraph>
          <Title level={5}>Per-dataset preference networks</Title>
          <Paragraph>
            Each dataset&apos;s visualization page can draw a preference
            network. Items are nodes, and an edge means the people who rated
            both tended to rate them alike. Edges are partial correlations, so a
            link survives only if it is not explained by the other items in the
            network. That separates a specific pairing from two items that
            share a general appetite.
          </Paragraph>
          <Paragraph>
            Networks are fitted in R with <Text code>EGAnet</Text>&apos;s{' '}
            <Text code>bootEGA</Text>: 500 resampling bootstraps, a graphical
            lasso model, and walktrap community detection, at a fixed seed.
            Fitting runs offline and the results ship with the database.
          </Paragraph>
          <Paragraph>
            The fit is then repeated on a subset. <Text code>itemStability</Text>{' '}
            reports how often each item returns to its own dimension across
            bootstraps. Items reaching 45% are kept and the model is refitted on
            those alone, so selection is made by the data, and the cutoff
            travels with each result so the page can state it. The published
            cutoff for this method is nearer 0.70. The looser 0.45 was chosen so
            that most datasets yield a network at all, which is why these
            figures are illustrative rather than confirmatory.
          </Paragraph>
        </Card>

        <Card id="citing" title="Citing" style={{ marginBottom: 24 }}>
          <Paragraph>
            Please cite both the database and the original studies whose data
            you use. Every study page carries its citation, DOI, and a BibTeX
            generator, and <Text code>studies.csv</Text> in the archive carries
            them for every study at once. In the packages,{' '}
            <Text code>cite()</Text> returns the database citation and{' '}
            <Text code>cite(d)</Text> a dataset&apos;s.
          </Paragraph>
          <pre style={pre}>
{`Fernandez, K., Goyal, S., & Krajbich, I. (2026). The Liking Initiative: a database of subjective
evaluation ratings for decision-making research [Data set]. Zenodo. https://doi.org/10.5281/zenodo.22216442`}
          </pre>
          <Paragraph style={{ marginTop: 12, marginBottom: 0 }}>
            That DOI always resolves to the newest version. To name the exact
            data an analysis used, cite the version DOI that{' '}
            <a href={DOI} target="_blank" rel="noreferrer">Zenodo</a> lists for
            the version <Text code>release_info()</Text> reports.
          </Paragraph>
        </Card>

        <Card id="contributing" title="Contributing a dataset" style={{ marginBottom: 24 }}>
          <Paragraph style={{ marginBottom: 0 }}>
            New datasets enter through a standardized ingestion script that
            records what it did in the migration log, so every row is traceable
            to a source file. The process, the required columns, and the
            metadata a submission needs are documented in{' '}
            <a href={`${REPO}/blob/main/docs/ADDING_DATASETS.md`} target="_blank" rel="noreferrer">
              docs/ADDING_DATASETS.md
            </a>
            . Open an issue in the{' '}
            <a href={REPO} target="_blank" rel="noreferrer">project repository</a>{' '}
            to propose a dataset.
          </Paragraph>
        </Card>
      </Col>

      <Col xs={0} lg={5}>
        <Anchor
          style={{ position: 'sticky', top: 24 }}
          items={[
            { key: 'overview', href: '#overview', title: 'What the Liking Initiative is' },
            { key: 'construct', href: '#construct', title: 'What was measured' },
            { key: 'ratings', href: '#ratings', title: 'The ratings table' },
            { key: 'gotchas', href: '#gotchas', title: 'Two things to get right' },
            { key: 'provenance', href: '#provenance', title: 'Provenance and quality' },
            { key: 'packages', href: '#packages', title: 'R and Python packages' },
            { key: 'access', href: '#access', title: 'Downloading the data' },
            { key: 'api', href: '#api', title: 'REST API' },
            { key: 'descriptives', href: '#descriptives', title: 'Descriptives' },
            { key: 'similarity', href: '#similarity', title: 'Preference similarity' },
            { key: 'networks', href: '#networks', title: 'Networks' },
            { key: 'citing', href: '#citing', title: 'Citing' },
            { key: 'contributing', href: '#contributing', title: 'Contributing' },
          ]}
        />
      </Col>
    </Row>
  );
};

export default DocumentationPage;
