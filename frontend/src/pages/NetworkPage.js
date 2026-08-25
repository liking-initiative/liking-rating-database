import React, { useMemo, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Typography, Spin, Segmented, AutoComplete, Tag, Space, Button } from 'antd';
import { useQuery } from 'react-query';
import ItemNetworkCanvas from '../components/ItemNetworkCanvas';
import { getItemNetwork } from '../services/api';

const { Title, Text } = Typography;

// One control, three stops. The raw min-shared threshold is the wrong thing to
// put in front of someone -- what they actually want is "show me more".
const DENSITY = [
  { label: 'Core', value: 12 },
  { label: 'Wider', value: 8 },
  { label: 'Everything', value: 2 },
];

const NetworkPage = () => {
  const navigate = useNavigate();
  const [minShared, setMinShared] = useState(12);
  const [selected, setSelected] = useState(null);
  const [hovered, setHovered] = useState(null);
  const [search, setSearch] = useState('');

  const { data: net, isLoading, error } = useQuery(
    ['item-network', minShared],
    () => getItemNetwork({ min_shared: minShared }),
    { keepPreviousData: true, staleTime: 10 * 60 * 1000, refetchOnWindowFocus: false }
  );

  const options = useMemo(
    () =>
      (net?.nodes ?? [])
        .map((n) => ({ value: n.label, id: n.id }))
        .sort((a, b) => a.value.localeCompare(b.value)),
    [net]
  );

  const focusId = useMemo(() => {
    if (selected) return selected.id;
    if (!search) return null;
    return options.find((o) => o.value === search)?.id ?? null;
  }, [selected, search, options]);

  const onSelect = useCallback((node) => {
    setSelected(node);
    setSearch(node.label);
  }, []);

  const detail = hovered || selected;

  return (
    <div>
      <Title level={2}>Item Network</Title>
      <Text type="secondary">
        Items that get rated in the same studies. Drag a node, scroll to zoom,
        and hover or click to lift out one item&apos;s neighbourhood.
      </Text>

      <Card
        style={{ marginTop: 20 }}
        styles={{ body: { padding: 16 } }}
        title={
          <Space wrap size={16} style={{ padding: '4px 0' }}>
            <AutoComplete
              style={{ width: 260 }}
              options={options}
              value={search}
              placeholder="Find an item…"
              allowClear
              filterOption={(input, option) =>
                option.value.toLowerCase().includes(input.toLowerCase())
              }
              onChange={(v) => {
                setSearch(v);
                if (!v) setSelected(null);
              }}
              onSelect={(v) => {
                const hit = (net?.nodes ?? []).find((n) => n.label === v);
                if (hit) setSelected(hit);
              }}
            />
            <Segmented
              options={DENSITY}
              value={minShared}
              onChange={(v) => {
                setMinShared(v);
                setSelected(null);
              }}
            />
          </Space>
        }
        extra={
          net && (
            <Space size={4}>
              <Tag>{net.meta.node_count} items</Tag>
              <Tag>{net.meta.edge_count.toLocaleString()} links</Tag>
            </Space>
          )
        }
      >
        {error ? (
          <Text type="danger">The network could not be loaded.</Text>
        ) : isLoading && !net ? (
          <div style={{ height: 640, display: 'grid', placeItems: 'center' }}>
            <Spin size="large" />
          </div>
        ) : !net?.nodes?.length ? (
          <div style={{ height: 640, display: 'grid', placeItems: 'center' }}>
            <Text type="secondary">No connections at this density.</Text>
          </div>
        ) : (
          <ItemNetworkCanvas
            data={net}
            height={640}
            focusId={focusId}
            onSelect={onSelect}
            onHoverChange={setHovered}
          />
        )}

        {detail && (
          <div
            style={{
              marginTop: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 16,
              flexWrap: 'wrap',
              borderTop: '1px solid var(--border-gray)',
              paddingTop: 12,
            }}
          >
            <strong style={{ fontSize: 15 }}>{detail.label}</strong>
            <Text type="secondary" style={{ fontSize: 13 }}>
              {detail.frequency} studies
            </Text>
            <Text type="secondary" style={{ fontSize: 13 }}>
              mean liking{' '}
              {Number.isFinite(detail.mean_rating)
                ? detail.mean_rating.toFixed(2)
                : '—'}
            </Text>
            <Button size="small" onClick={() => navigate(`/items/${detail.id}`)}>
              Open item →
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
};

export default NetworkPage;
