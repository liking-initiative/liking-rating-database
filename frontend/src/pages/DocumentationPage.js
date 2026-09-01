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
  { key: 5, ep: 'GET /items', ret: 'Stimuli, paginated and searchable by name' },
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
          What the initiative collects, how the database is structured, what the
          columns mean, and how to get the data into R or Python.
        </Paragraph>

        <Card id="overview" title="What the Liking Initiative is" style={{ marginBottom: 24 }}>
          <Paragraph>
            The Liking Initiative is a database of subjective evaluations —
            how much people report liking individual items — collected from
            published decision-making studies and put on a common footing so
            they can be used together. Studies measured liking for their own
            purposes and on their own scales; the initiative gathers those
            ratings, records how each was elicited, and normalizes them so a
            question can be asked across studies rather than within one.
          </Paragraph>
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

        <Card id="descriptives" title="Descriptives" style={{ marginBottom: 24 }}>
          <Paragraph>
            The Descriptives page reports item-level distributional statistics:
            how one item was rated within a single study, and how that
            distribution varies across every study that used it.
          </Paragraph>
          <p className="page-note">
            <strong>Before reusing these numbers.</strong> They apply one fixed
            set of choices to every dataset — no exclusions, all available
            subjects, and each dataset&apos;s first rating phase unless you pick
            another. Those choices may not match the preprocessing your question
            needs. Download the data and verify before publishing.
          </p>
          <Paragraph>
            <strong>Inclusion.</strong> Nothing is filtered out. Every subject
            who rated the item contributes, with no outlier rule and no
            attention-check screen, because the exclusions a study applied are
            not recorded here and inventing our own would silently change what
            each paper reported.
          </Paragraph>
          <Paragraph>
            <strong>Repeated phases.</strong> Two datasets rate the same items
            more than once (<Text code>leeholyoak2021</Text>, three phases, and{' '}
            <Text code>leehare2023exp2</Text>, two). Only the first phase counts
            unless you select another, so a subject who rated an item three
            times is one observation rather than three.
          </Paragraph>
          <Paragraph style={{ marginBottom: 0 }}>
            <strong>Which scale each statistic is on.</strong> Location and
            spread — mean, SD, median, IQR, skewness — are computed on{' '}
            <Text code>normalized_rating</Text>, so studies on different
            response scales sit on a common 0–1 axis and the cross-study panels
            are comparable. Floor and ceiling proportions are read against each
            study&apos;s <em>own</em> scale, since hitting the end of a 1–9
            Likert is a different event from hitting the end of a 0–870 slider.
            The Range column is likewise in the study&apos;s own units.
          </Paragraph>
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
            −0.02 at the item counts typical here, but exactly −1 at{' '}
            <Text code>k = 2</Text>, so datasets with fewer than 20 items are
            skipped. And a pair needs at least 10 shared raters within a
            dataset to contribute at all, so a high{' '}
            <Text code>r</Text> on few raters never outranks a solid one on
            many.
          </Paragraph>
        </Card>


        <Card id="networks" title="Preference networks" style={{ marginBottom: 24 }}>
          <Paragraph>
            Each dataset&apos;s visualization page can draw a{' '}
            <strong>preference network</strong>: items are nodes, and an edge
            means the people who rated both tended to rate them alike. Edges are{' '}
            <strong>partial</strong> correlations, so a link survives only if it
            is not explained by the other items in the network — which is what
            separates a real pairing from two items that merely ride the same
            general appetite.
          </Paragraph>
          <Paragraph>
            Networks are fitted in R with{' '}
            <Text code>EGAnet</Text>&apos;s <Text code>bootEGA</Text>: 500
            resampling bootstraps, a graphical lasso model, and walktrap
            community detection, at a fixed seed. Fitting runs offline and the
            results ship with the database — bootstrapping a graphical model
            several hundred times is not something to ask a visitor&apos;s
            browser for.
          </Paragraph>
          <Paragraph>
            The fit is then repeated on a subset. <Text code>itemStability</Text>{' '}
            reports how often each item returns to its own dimension across
            bootstraps; items reaching{' '}
            <strong>45%</strong> are kept and the model is refitted on those
            alone. Selection is therefore made by the data rather than by us,
            and the cutoff travels with each result so the page can state it.
            The published cutoff for this method is nearer 0.70 — 0.45 is
            deliberately loose, chosen so that most datasets yield a network at
            all, and it is the reason the figures are illustrative rather than
            confirmatory.
          </Paragraph>
          <p className="page-note">
            <strong>Why most datasets are capped first.</strong> A graphical
            model over items needs more subjects than items, and most datasets
            here have the opposite. Where that holds, the first fit is
            restricted to the most completely observed items — enough to make
            an estimate possible at all. That cap is a feasibility limit, and it
            is recorded separately from the stability selection so the two are
            never read as the same thing. It applies to almost every dataset
            that yields a network; the rest cannot clear even this bar, get no
            network, and say why. Each dataset&apos;s own figure states which
            case it is.
          </p>
          <Paragraph style={{ marginBottom: 0 }}>
            Each network also reports{' '}
            <strong>structural consistency</strong> per dimension: how often
            that dimension reappears intact across bootstraps. Low values mean
            the grouping is unstable — read the communities on such a plot as a
            suggestion, not a finding.
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
            borderRadius: 6, fontSize: 13.5, whiteSpace: 'pre-wrap',
          }}>
{`Fernandez, K., Goyal, S., & Krajbich, I. (2026). The Liking Initiative: a database of subjective
evaluation ratings for decision-making research [Data set]. Zenodo. https://doi.org/10.5281/zenodo.22216442`}
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
            { key: 'overview', href: '#overview', title: 'What the Liking Initiative is' },
            { key: 'ratings', href: '#ratings', title: 'The ratings table' },
            { key: 'gotchas', href: '#gotchas', title: 'Two things to get right' },
            { key: 'access', href: '#access', title: 'Downloading the data' },
            { key: 'api', href: '#api', title: 'REST API' },
            { key: 'descriptives', href: '#descriptives', title: 'Descriptives' },
            { key: 'similarity', href: '#similarity', title: 'Preference similarity' },
            { key: 'networks', href: '#networks', title: 'Preference networks' },
            { key: 'citing', href: '#citing', title: 'Citing' },
            { key: 'contributing', href: '#contributing', title: 'Contributing' },
          ]}
        />
      </Col>
    </Row>
  );
};

export default DocumentationPage;
