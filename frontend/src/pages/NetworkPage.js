import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Typography, Row, Col, Slider, Select, Spin, Alert, AutoComplete, Tag } from 'antd';
import Plot from 'react-plotly.js';
import { useQuery } from 'react-query';
import { getItemNetwork, getCategories } from '../services/api';

const { Title, Text } = Typography;
const { Option } = Select;

// Node ↔ dataset co-occurrence network over the whole database. Nodes are
// items grouped by standardized name; an edge means the two items were rated
// in at least `minShared` of the same datasets.
const NetworkPage = () => {
  const navigate = useNavigate();
  const [minShared, setMinShared] = useState(2);
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [highlight, setHighlight] = useState(null);

  const { data: categoriesData } = useQuery('categories', getCategories);
  const { data: net, isLoading, error } = useQuery(
    ['item-network', minShared, selectedCategories],
    () => getItemNetwork({
      min_shared: minShared,
      ...(selectedCategories.length && { categories: selectedCategories }),
    }),
    { keepPreviousData: true, staleTime: 10 * 60 * 1000, refetchOnWindowFocus: false }
  );

  const traces = useMemo(() => {
    if (!net?.nodes?.length) return [];
    const byId = Object.fromEntries(net.nodes.map(n => [n.id, n]));
    // Edges reference nodes by their group LABEL, not by item id
    const byLabel = Object.fromEntries(net.nodes.map(n => [n.label, n]));

    // Edge segments in two weight tiers. Plain SVG scatter, not scattergl:
    // WebGL line rendering drops null-separated segments in some builds,
    // which makes every edge silently disappear.
    const tiers = [
      { test: w => w < 8, color: 'rgba(140,140,140,0.35)', width: 0.8 },
      { test: w => w >= 8, color: 'rgba(80,80,80,0.55)', width: 1.6 },
    ];
    const edgeTraces = tiers.map(tier => {
      const xs = [], ys = [];
      net.edges.forEach(e => {
        if (!tier.test(e.weight)) return;
        const a = byLabel[e.source], b = byLabel[e.target];
        if (!a || !b) return;
        xs.push(a.x, b.x, null);
        ys.push(a.y, b.y, null);
      });
      return {
        x: xs, y: ys, mode: 'lines', type: 'scatter', hoverinfo: 'skip',
        line: { color: tier.color, width: tier.width }, showlegend: false,
      };
    });

    // One node trace per category → free legend with per-category toggling
    const byCategory = {};
    net.nodes.forEach(n => {
      (byCategory[n.category || 'unknown'] ||= []).push(n);
    });
    const nodeTraces = Object.entries(byCategory)
      .sort((a, b) => b[1].length - a[1].length)
      .map(([category, nodes]) => ({
        x: nodes.map(n => n.x),
        y: nodes.map(n => n.y),
        customdata: nodes.map(n => n.id),
        text: nodes.map(n =>
          `${n.label}<br>category: ${category}<br>datasets: ${n.frequency}` +
          `<br>mean rating: ${n.mean_rating ?? '—'}`),
        hovertemplate: '%{text}<extra></extra>',
        mode: 'markers', type: 'scattergl', name: category,
        marker: {
          size: nodes.map(n => 5 + 1.8 * Math.sqrt(n.frequency)),
          opacity: 0.9, line: { color: 'white', width: 0.5 },
        },
      }));

    const overlay = [];
    if (highlight && byId[highlight]) {
      const n = byId[highlight];
      overlay.push({
        x: [n.x], y: [n.y], mode: 'markers+text', type: 'scattergl',
        text: [n.label], textposition: 'top center', showlegend: false,
        textfont: { size: 14 },
        marker: { size: 22, symbol: 'circle-open', line: { color: '#ff4d4f', width: 3 } },
        hoverinfo: 'skip',
      });
    }
    return [...edgeTraces, ...nodeTraces, ...overlay];
  }, [net, highlight]);

  const highlightOptions = useMemo(() =>
    (net?.nodes || [])
      .slice()
      .sort((a, b) => a.label.localeCompare(b.label))
      .map(n => ({ value: n.id, label: n.label })), [net]);

  return (
    <div>
      <Title level={2}>Item Network</Title>
      <Text type="secondary">
        Items rated in the same datasets, across the whole database. Node size
        = number of datasets; an edge means two items co-occur in at least the
        chosen number of datasets. Click a node to open the item.
      </Text>

      <Card style={{ marginTop: 16, marginBottom: 16 }}>
        <Row gutter={[24, 8]} align="middle">
          <Col xs={24} md={8}>
            <Text strong>Min shared datasets: {minShared}</Text>
            <Slider min={2} max={20} value={minShared} onChange={setMinShared} />
          </Col>
          <Col xs={24} md={8}>
            <Text strong>Categories</Text>
            <Select
              mode="multiple"
              allowClear
              placeholder="All categories"
              style={{ width: '100%' }}
              value={selectedCategories}
              onChange={setSelectedCategories}
            >
              {categoriesData?.categories?.map(c => (
                <Option key={c} value={c}>{c.replace(/_/g, ' ')}</Option>
              ))}
            </Select>
          </Col>
          <Col xs={24} md={8}>
            <Text strong>Find an item</Text>
            <AutoComplete
              allowClear
              style={{ width: '100%' }}
              options={highlightOptions}
              placeholder="Type an item name…"
              onSelect={setHighlight}
              onClear={() => setHighlight(null)}
              filterOption={(input, option) =>
                option.label.toLowerCase().includes(input.toLowerCase())}
            />
          </Col>
        </Row>
      </Card>

      <Card>
        {error ? (
          <Alert type="error" showIcon message="The network could not be loaded."
            description="Please try again." />
        ) : isLoading && !net ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 600 }}>
            <Spin size="large" tip="Computing network…" />
          </div>
        ) : net?.nodes?.length ? (
          <>
            <div style={{ marginBottom: 8 }}>
              <Tag>{net.meta.node_count} items</Tag>
              <Tag>{net.meta.edge_count.toLocaleString()} connections</Tag>
              <Tag>{net.meta.components} component{net.meta.components === 1 ? '' : 's'}</Tag>
              {net.meta.edges_truncated && (
                <Tag color="orange">showing strongest {net.meta.edge_count.toLocaleString()} edges</Tag>
              )}
              {isLoading && <Spin size="small" style={{ marginLeft: 8 }} />}
            </div>
            <Plot
              data={traces}
              layout={{
                height: 700,
                hovermode: 'closest',
                dragmode: 'pan',
                margin: { t: 10, b: 10, l: 10, r: 10 },
                xaxis: { visible: false },
                yaxis: { visible: false, scaleanchor: 'x' },
                legend: { orientation: 'h', y: -0.02 },
              }}
              config={{ responsive: true, scrollZoom: true }}
              style={{ width: '100%' }}
              onClick={(ev) => {
                const id = ev?.points?.[0]?.customdata;
                if (id) navigate(`/items/${id}`);
              }}
            />
          </>
        ) : (
          <Alert type="info" showIcon message="No connections at this threshold"
            description="Lower the minimum shared datasets or widen the category filter." />
        )}
      </Card>
    </div>
  );
};

export default NetworkPage;
