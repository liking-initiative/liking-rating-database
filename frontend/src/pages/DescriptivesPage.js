import React, { useMemo, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Card, Typography, Row, Col, Select, Alert, Spin, Table, Tag, Radio, Space, Empty,
} from 'antd';
import Plot from 'react-plotly.js';
import { useQuery } from 'react-query';
import {
  getDescriptivesIndex,
  getDescriptivesDatasetItems,
  getDescriptivesDatasetItem,
  getDescriptivesItem,
  getSimilarItems,
} from '../services/api';

const { Title, Text, Paragraph } = Typography;

// Palette shared with styles/main.css so figures and chrome stay in one system.
const BLUE = '#085AB3';
const ORANGE = '#E78A00';

const PANEL_ORDER = ['mean', 'sd', 'skewness', 'prop_floor', 'prop_ceil'];

const fmt = (v, digits = 3) =>
  v === null || v === undefined || !Number.isFinite(v) ? '—' : v.toFixed(digits);

// Deterministic jitter: the same item always renders the same dot scatter,
// so the figure doesn't reshuffle on every re-render.
const seededJitter = (seed, amplitude, count) => {
  let s = seed >>> 0;
  const out = [];
  for (let i = 0; i < count; i += 1) {
    s = (s * 1664525 + 1013904223) >>> 0;
    out.push(((s / 4294967296) - 0.5) * 2 * amplitude);
  }
  return out;
};

const hashString = (str) => {
  let h = 0;
  for (let i = 0; i < str.length; i += 1) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return h;
};

/**
 * One raincloud panel: KDE area + outline, a dashed median rule, and the raw
 * observations jittered underneath, so the density and the actual sample
 * behind it are legible in the same figure.
 */
const RainCloud = ({ panel, title, height = 170, hoverLabels, scaleRange }) => {
  const figure = useMemo(() => {
    // Read inside the memo: `?? []` would allocate a fresh array each render
    // and defeat the memoisation.
    const kde = panel?.kde ?? [];
    const dots = panel?.dots ?? [];
    if (kde.length < 3) return null;

    const maxDensity = Math.max(...kde.map((p) => p.y), 1e-9);
    const yPad = maxDensity * 0.4;
    const yDotCenter = -yPad * 0.55;
    const jitter = seededJitter(hashString(title), yPad * 0.3, dots.length);

    const traces = [
      {
        x: kde.map((p) => p.x),
        y: kde.map((p) => p.y),
        type: 'scatter',
        mode: 'lines',
        fill: 'tozeroy',
        fillcolor: 'rgba(8, 90, 179, 0.18)',
        line: { color: BLUE, width: 1.5 },
        hoverinfo: 'skip',
        showlegend: false,
      },
      {
        x: dots,
        y: dots.map((_, i) => yDotCenter + jitter[i]),
        type: 'scatter',
        mode: 'markers',
        marker: { color: ORANGE, size: 5, opacity: 0.55 },
        text: hoverLabels,
        hovertemplate: hoverLabels
          ? '%{text}<br>%{x:.3f}<extra></extra>'
          : '%{x:.3f}<extra></extra>',
        showlegend: false,
      },
    ];

    let xRange = null;
    if (scaleRange && scaleRange.every((v) => Number.isFinite(v))) {
      const [lo, hi] = scaleRange;
      const pad = (hi - lo) * 0.02;
      xRange = [lo - pad, hi + pad];
    }

    const shapes = [];
    if (Number.isFinite(panel.median)) {
      shapes.push({
        type: 'line',
        x0: panel.median,
        x1: panel.median,
        y0: yDotCenter - yPad * 0.15,
        y1: maxDensity * 1.05,
        line: { color: ORANGE, width: 2, dash: 'dash' },
      });
    }
    // On the mean panel, mark where the response scale actually ends.
    if (scaleRange) {
      scaleRange.forEach((v) => {
        if (!Number.isFinite(v)) return;
        shapes.push({
          type: 'line',
          x0: v,
          x1: v,
          y0: yDotCenter - yPad * 0.15,
          y1: maxDensity * 1.05,
          line: { color: '#d0d0d0', width: 1, dash: 'dot' },
        });
      });
    }

    return {
      data: traces,
      layout: {
        height,
        margin: { l: 8, r: 8, t: 4, b: 26 },
        xaxis: {
          zeroline: false,
          showgrid: false,
          ticks: 'outside',
          ticklen: 3,
          tickfont: { size: 10 },
          linecolor: '#e0e0e0',
          // A Gaussian kernel spreads density past the ends of a bounded
          // rating scale; don't draw range the data could never occupy.
          ...(xRange ? { range: xRange } : {}),
        },
        yaxis: {
          visible: false,
          range: [yDotCenter - yPad * 0.5, maxDensity * 1.15],
        },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        shapes,
        hovermode: 'closest',
        font: { size: 11 },
      },
      config: { displayModeBar: false, responsive: true },
    };
  }, [panel, title, height, hoverLabels, scaleRange]);

  return (
    <div className="desc-plot-panel">
      <p className="desc-plot-title">{title}</p>
      {figure ? (
        <Plot
          data={figure.data}
          layout={figure.layout}
          config={figure.config}
          style={{ width: '100%' }}
          useResizeHandler
        />
      ) : (
        <p className="desc-plot-empty">Insufficient data</p>
      )}
    </div>
  );
};

/** Neighbour list for preference similarity. r is bounded, so a bar reads
 *  faster than the number alone; the number stays for anyone who needs it. */
const SimilarityTable = ({ rows, itemId }) => (
  <Table
    size="small"
    rowKey="item_id"
    dataSource={rows}
    pagination={false}
    scroll={{ x: 'max-content' }}
    columns={[
      {
        title: 'Item',
        dataIndex: 'item_name',
        key: 'item_name',
        render: (name, row) => (
          <Link to={`/items/${row.item_id}`} title={`compare with ${itemId}`}>
            {name}
          </Link>
        ),
      },
      {
        title: 'Category',
        dataIndex: 'category',
        key: 'category',
        render: (c) => (c ? <Tag>{c}</Tag> : '—'),
      },
      {
        title: 'r',
        dataIndex: 'r',
        key: 'r',
        align: 'right',
        render: (r) => (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <span
              aria-hidden
              style={{
                display: 'inline-block',
                width: Math.max(2, Math.abs(r) * 44),
                height: 8,
                borderRadius: 2,
                background: r >= 0 ? BLUE : ORANGE,
                opacity: 0.55,
              }}
            />
            {fmt(r, 2)}
          </span>
        ),
      },
      {
        // One column, not two: side by side these tables are too narrow to
        // show a fifth column without clipping it.
        title: 'Raters',
        dataIndex: 'n_subjects',
        key: 'n_subjects',
        align: 'right',
        render: (n, row) => (
          <span title={`${n} shared raters across ${row.n_datasets} dataset(s)`}>
            {n}
            <Text type="secondary" style={{ fontSize: 11 }}>
              {` / ${row.n_datasets} ds`}
            </Text>
          </span>
        ),
      },
    ]}
  />
);

const DescriptivesPage = () => {
  const [params, setParams] = useSearchParams();
  const datasetId = params.get('dataset') || undefined;
  const itemId = params.get('item') || undefined;
  const timepointParam = params.get('timepoint');
  const timepoint = timepointParam ? Number(timepointParam) : undefined;

  const { data: index, isLoading: indexLoading } = useQuery(
    'descriptives-index',
    getDescriptivesIndex,
    { staleTime: 30 * 60 * 1000 }
  );

  const { data: items, isLoading: itemsLoading } = useQuery(
    ['descriptives-items', datasetId],
    () => getDescriptivesDatasetItems(datasetId),
    { enabled: !!datasetId, staleTime: 30 * 60 * 1000 }
  );

  const { data: detail, isLoading: detailLoading, error: detailError } = useQuery(
    ['descriptives-detail', datasetId, itemId, timepoint],
    () => getDescriptivesDatasetItem({ datasetId, itemId, timepoint }),
    { enabled: !!datasetId && !!itemId, keepPreviousData: true }
  );

  const { data: across, isLoading: acrossLoading } = useQuery(
    ['descriptives-across', itemId],
    () => getDescriptivesItem(itemId),
    { enabled: !!itemId, keepPreviousData: true }
  );

  const { data: similar, isLoading: similarLoading } = useQuery(
    ['descriptives-similar', itemId],
    () => getSimilarItems(itemId, { limit: 12 }),
    { enabled: !!itemId, keepPreviousData: true, retry: false }
  );

  const selectedDataset = useMemo(
    () => index?.find((d) => d.dataset_id === datasetId),
    [index, datasetId]
  );

  // If the chosen item isn't in the newly chosen dataset, drop it rather than
  // leaving the page requesting a pair that cannot resolve.
  useEffect(() => {
    if (!items || !itemId) return;
    if (!items.some((i) => i.item_id === itemId)) {
      const next = new URLSearchParams(params);
      next.delete('item');
      next.delete('timepoint');
      setParams(next, { replace: true });
    }
  }, [items, itemId, params, setParams]);

  const update = (patch) => {
    const next = new URLSearchParams(params);
    Object.entries(patch).forEach(([k, v]) => {
      if (v === undefined || v === null || v === '') next.delete(k);
      else next.set(k, v);
    });
    setParams(next);
  };

  const statsRows = useMemo(() => {
    if (!detail?.stats) return [];
    const s = detail.stats;
    return [
      { key: 'mean', label: 'Mean', value: fmt(s.mean) },
      { key: 'sd', label: 'SD', value: fmt(s.sd) },
      { key: 'median', label: 'Median', value: fmt(s.median) },
      { key: 'iqr', label: 'IQR', value: fmt(s.iqr) },
      { key: 'skewness', label: 'Skewness', value: fmt(s.skewness) },
      { key: 'prop_floor', label: 'Prop. Floor', value: fmt(s.prop_floor) },
      { key: 'prop_ceil', label: 'Prop. Ceiling', value: fmt(s.prop_ceil) },
    ];
  }, [detail]);

  const acrossHoverLabels = useMemo(
    () => across?.datasets?.map((d) => d.label) ?? null,
    [across]
  );

  const datasetTableColumns = [
    {
      title: 'Study',
      dataIndex: 'label',
      key: 'label',
      render: (label, row) => (
        <Link to={`/descriptives?dataset=${row.dataset_id}&item=${itemId}`}>{label}</Link>
      ),
    },
    { title: 'Dataset', dataIndex: 'dataset_name', key: 'dataset_name' },
    { title: 'n', dataIndex: 'n', key: 'n', sorter: (a, b) => a.n - b.n },
    {
      title: 'Mean (0–1)',
      dataIndex: 'mean',
      key: 'mean',
      render: (v) => fmt(v),
      sorter: (a, b) => (a.mean ?? 0) - (b.mean ?? 0),
    },
    { title: 'SD', dataIndex: 'sd', key: 'sd', render: (v) => fmt(v) },
    { title: 'Skew', dataIndex: 'skewness', key: 'skewness', render: (v) => fmt(v, 2) },
    { title: 'Floor', dataIndex: 'prop_floor', key: 'prop_floor', render: (v) => fmt(v, 3) },
    { title: 'Ceiling', dataIndex: 'prop_ceil', key: 'prop_ceil', render: (v) => fmt(v, 3) },
    {
      title: 'Scale',
      key: 'scale',
      render: (_, r) => `${r.scale_min}–${r.scale_max}`,
    },
  ];

  return (
    <div>
      <Title level={2}>Descriptives</Title>
      <Paragraph type="secondary" style={{ maxWidth: 720 }}>
        Item-level distributional statistics computed from the ratings in this
        database. Choose a dataset and item to see how that item was rated
        within one study, and how its distribution varies across every study
        that used it.
      </Paragraph>

      <p className="page-note">
        <strong>Before reusing these numbers:</strong> they apply one fixed set
        of choices to every dataset — no exclusions, all available subjects,
        and each dataset&apos;s first rating phase unless you pick another.
        Cross-study panels use <Text code>normalized_rating</Text> so different
        response scales are comparable. Those choices may not match the
        preprocessing your question needs; download the data and verify before
        publishing.
      </p>

      <Card style={{ marginBottom: 24 }}>
        <Row gutter={[16, 16]} align="bottom">
          <Col xs={24} md={9}>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>Dataset</Text>
            <Select
              showSearch
              style={{ width: '100%' }}
              placeholder="Select a dataset"
              loading={indexLoading}
              value={datasetId}
              optionFilterProp="children"
              onChange={(v) => update({ dataset: v, item: null, timepoint: null })}
            >
              {index?.map((d) => (
                <Select.Option key={d.dataset_id} value={d.dataset_id}>
                  {`${d.label} — ${d.dataset_name}`}
                </Select.Option>
              ))}
            </Select>
          </Col>

          <Col xs={24} md={9}>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>Item</Text>
            <Select
              showSearch
              style={{ width: '100%' }}
              placeholder={datasetId ? 'Select an item' : 'Select a dataset first'}
              loading={itemsLoading}
              disabled={!datasetId}
              value={itemId}
              optionFilterProp="children"
              onChange={(v) => update({ item: v, timepoint: null })}
            >
              {items?.map((i) => (
                <Select.Option key={i.item_id} value={i.item_id}>
                  {i.item_name}
                </Select.Option>
              ))}
            </Select>
          </Col>

          {/* Phase selector appears only for the datasets that have repeats. */}
          {selectedDataset?.timepoints?.length > 1 && (
            <Col xs={24} md={6}>
              <Text strong style={{ display: 'block', marginBottom: 4 }}>
                Rating phase
              </Text>
              <Radio.Group
                buttonStyle="solid"
                value={detail?.timepoint ?? selectedDataset.timepoints[0]}
                onChange={(e) => update({ timepoint: e.target.value })}
              >
                {selectedDataset.timepoints.map((t) => (
                  <Radio.Button key={t} value={t}>{t}</Radio.Button>
                ))}
              </Radio.Group>
            </Col>
          )}
        </Row>
      </Card>

      {!datasetId || !itemId ? (
        <Card>
          <Empty description="Select a dataset and item above to view distributional statistics." />
        </Card>
      ) : detailError ? (
        <Alert type="error" showIcon message="No ratings for that dataset and item." />
      ) : (
        <>
          <Card
            style={{ marginBottom: 24 }}
            title={
              <Space wrap>
                <span>
                  {detail?.item_name} in {detail?.dataset_name}
                </span>
                {detail?.category && <Tag color="blue">{detail.category}</Tag>}
                {detail?.available_timepoints?.length > 1 && (
                  <Tag color="orange">phase {detail.timepoint}</Tag>
                )}
              </Space>
            }
          >
            {detailLoading && !detail ? (
              <Spin />
            ) : (
              <Row gutter={[24, 24]}>
                <Col xs={24} lg={15}>
                  <Text type="secondary" style={{ fontSize: 13 }}>
                    Distribution across {detail?.n_subjects} subjects, in the
                    study&apos;s original scale units ({detail?.scale?.min}–
                    {detail?.scale?.max}, {detail?.scale?.type}). Each dot is
                    one subject; the dashed rule is the median.
                  </Text>
                  <div style={{ marginTop: 12 }}>
                    <RainCloud
                      panel={detail?.distribution}
                      title={`${detail?.item_name} — rating`}
                      height={260}
                      scaleRange={[detail?.scale?.min, detail?.scale?.max]}
                    />
                  </div>
                </Col>
                <Col xs={24} lg={9}>
                  <Table
                    size="small"
                    pagination={false}
                    dataSource={statsRows}
                    columns={[
                      { title: 'Statistic', dataIndex: 'label', key: 'label' },
                      { title: 'Value', dataIndex: 'value', key: 'value', align: 'right' },
                    ]}
                  />
                  <div style={{ marginTop: 12, fontSize: 13.5, color: '#4a4a4a' }}>
                    <div>
                      Observed range: {fmt(detail?.stats?.min, 2)} –{' '}
                      {fmt(detail?.stats?.max, 2)}
                    </div>
                    <div>
                      Study:{' '}
                      <Link to={`/datasets/${detail?.dataset_id}`}>
                        {detail?.study_name}
                      </Link>{' '}
                      ({detail?.study_year})
                    </div>
                  </div>
                </Col>
              </Row>
            )}
          </Card>

          <Card
            title={
              <Space wrap>
                <span>{detail?.item_name} across datasets</span>
                {across && <Tag color="blue">{across.n_datasets} datasets</Tag>}
                {across && (
                  <Tag>{across.n_ratings.toLocaleString()} ratings</Tag>
                )}
              </Space>
            }
          >
            {acrossLoading && !across ? (
              <Spin />
            ) : !across || across.n_datasets < 2 ? (
              <Empty description="This item appears in only one dataset, so there is no cross-study distribution to show." />
            ) : (
              <>
                <Text type="secondary" style={{ fontSize: 13 }}>
                  Each panel shows how one summary statistic varies across the{' '}
                  {across.n_datasets} datasets containing this item — one dot
                  per dataset, dashed rule at the median. Location and spread
                  are computed on normalized ratings (0–1); floor and ceiling
                  proportions use each study&apos;s own scale endpoints.
                </Text>
                <div className="desc-plot-grid" style={{ marginTop: 16 }}>
                  {PANEL_ORDER.map((key) => (
                    <RainCloud
                      key={key}
                      panel={across.stats[key]}
                      title={across.stats[key]?.label ?? key}
                      hoverLabels={acrossHoverLabels}
                    />
                  ))}
                </div>

                <Title level={5} style={{ marginTop: 28 }}>
                  Per-dataset summaries
                </Title>
                <Table
                  size="small"
                  rowKey="dataset_id"
                  dataSource={across.datasets}
                  columns={datasetTableColumns}
                  pagination={{ pageSize: 10, hideOnSinglePage: true }}
                  scroll={{ x: 'max-content' }}
                />
              </>
            )}
          </Card>

          <Card
            style={{ marginTop: 24 }}
            title={
              <Space wrap>
                <span>Items with similar preference</span>
                {similar && (
                  <Tag color="blue">{similar.n_candidates} compared</Tag>
                )}
              </Space>
            }
          >
            {similarLoading && !similar ? (
              <Spin />
            ) : !similar ? (
              <Empty description="No other item shares enough raters with this one to compare." />
            ) : (
              <>
                <Text type="secondary" style={{ fontSize: 13 }}>
                  Similarity by <strong>preference</strong>, not by name: two
                  items are close when the people who rated both tended to like
                  them together. Correlations are computed within each dataset
                  on person-centred ratings — otherwise items would look alike
                  merely because some people rate everything highly — then
                  combined across datasets with Fisher&apos;s z, weighted by
                  the number of shared raters. Pairs need at least{' '}
                  {similar.min_shared_subjects} shared raters in a dataset to
                  count.
                </Text>
                <Row gutter={[24, 24]} style={{ marginTop: 16 }}>
                  <Col xs={24} lg={12}>
                    <Title level={5} style={{ marginTop: 0 }}>
                      Liked by the same people
                    </Title>
                    <SimilarityTable rows={similar.most_similar} itemId={itemId} />
                  </Col>
                  <Col xs={24} lg={12}>
                    <Title level={5} style={{ marginTop: 0 }}>
                      Liked by opposite people
                    </Title>
                    <SimilarityTable rows={similar.most_dissimilar} itemId={itemId} />
                  </Col>
                </Row>
              </>
            )}
          </Card>
        </>
      )}
    </div>
  );
};

export default DescriptivesPage;
