import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Card, 
  Typography, 
  Row, 
  Col, 
  Button, 
  Space, 
  Descriptions,
  Table,
  Spin,
  Alert,
  Statistic,
  Divider
} from 'antd';
import { ArrowLeftOutlined, LineChartOutlined } from '@ant-design/icons';
import { useQuery } from 'react-query';
import { getItem, getItemRatingsByDataset } from '../services/api';

const { Title } = Typography;

const ItemDetailPage = () => {
  const { itemId } = useParams();
  const navigate = useNavigate();

  // Validate item ID format (checked after the hooks — an early return here
  // would skip hook calls and crash React when the URL param changes)
  const isValidUUID = (id) => {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(id);
  };
  const validId = isValidUUID(itemId);

  // Fetch item details
  const { data: item, isLoading: itemLoading, error: itemError } = useQuery(
    ['item', itemId],
    () => getItem(itemId),
    {
      enabled: validId,
      retry: 3,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );

  // Fetch rating aggregations for this item by dataset
  const { data: ratings, isLoading: ratingsLoading } = useQuery(
    ['itemRatingsByDataset', itemId],
    () => getItemRatingsByDataset(itemId),
    {
      enabled: validId,
      retry: 3,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );

  if (!validId) {
    return (
      <div style={{ padding: '20px' }}>
        <Alert
          message="Invalid Item ID"
          description="The item ID in the URL is not in a valid format. Please check the link and try again."
          type="error"
          showIcon
          action={
            <Space>
              <Button onClick={() => navigate('/items')}>
                Browse Items
              </Button>
            </Space>
          }
        />
      </div>
    );
  }

  if (itemLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>Loading item details...</div>
      </div>
    );
  }

  if (itemError || !item) {
    return (
      <div style={{ padding: '20px' }}>
        <Alert
          message="Error"
          description="Failed to load item details. The item may not exist or there was a server error."
          type="error"
          showIcon
          action={
            <Button onClick={() => navigate('/items')}>
              Back to Items
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Space>
            <Button 
              icon={<ArrowLeftOutlined />} 
              onClick={() => navigate('/items')}
            >
              Back to Items
            </Button>
            <Title level={2} style={{ margin: 0 }}>
              {item.name}
            </Title>
          </Space>
        </Col>
        <Col>
          <Space>
            <Button
              type="primary"
              icon={<LineChartOutlined />}
              onClick={() => navigate(`/descriptives?item=${itemId}`)}
            >
              Descriptives
            </Button>
          </Space>
        </Col>
      </Row>

      <Row gutter={[24, 24]}>
        {/* Only `name` and `standardized_name` hold real values; every other
            item column is empty for every row. */}
        <Col xs={24} lg={16}>
          <Card title="Item">
            <Descriptions column={1} bordered>
              <Descriptions.Item label="Name">
                <strong>{item.name}</strong>
              </Descriptions.Item>
              {item.standardized_name && item.standardized_name !== item.name && (
                <Descriptions.Item label="Grouped under">
                  {item.standardized_name}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="Appears in">
                {item.frequency || 0} datasets
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        {/* Statistics */}
        <Col xs={24} lg={8}>
          <Card title="Statistics">
            <Row gutter={[16, 16]}>
              <Col span={24}>
                <Statistic
                  title="Appears in Datasets"
                  value={ratings ? ratings.length : 0}
                  suffix="datasets"
                  valueStyle={{ color: '#085AB3' }}
                />
              </Col>
              
              {ratings && ratings.length > 0 && (
                <>
                  <Col span={24}>
                    <Divider />
                  </Col>
                  <Col span={24}>
                    <Statistic
                      title="Total Ratings"
                      value={ratings.reduce((sum, r) => sum + r.n_ratings, 0)}
                      valueStyle={{ color: '#52c41a' }}
                    />
                  </Col>
                  <Col span={24}>
                    <Statistic
                      title="Average Rating"
                      value={ratings.length > 0 ? 
                        (ratings.reduce((sum, r) => sum + r.mean_rating * r.n_ratings, 0) / 
                         ratings.reduce((sum, r) => sum + r.n_ratings, 0)).toFixed(2) : 0
                      }
                      precision={2}
                      valueStyle={{ color: '#E78A00' }}
                    />
                  </Col>
                </>
              )}
            </Row>
          </Card>

        </Col>
      </Row>

      {/* Per-dataset breakdown */}
      {ratings && ratings.length > 0 && (
        <Card
          title={`Rated in ${ratings.length} datasets`}
          style={{ marginTop: 24 }}
          extra={
            <Button
              type="link"
              onClick={() => navigate(`/descriptives?item=${itemId}`)}
            >
              See the distributions →
            </Button>
          }
        >
          <p className="page-caption">
            Means are on the normalized 0–1 scale, so they are comparable
            across studies that used different response scales.
          </p>
          <Table
            size="small"
            rowKey={(r) => r.dataset_id || r.dataset_name}
            dataSource={ratings}
            pagination={{ pageSize: 12, hideOnSinglePage: true }}
            scroll={{ x: 'max-content' }}
            columns={[
              {
                title: 'Study',
                dataIndex: 'study_name',
                key: 'study_name',
                render: (v, r) => v || r.dataset_name || '—',
              },
              {
                title: 'Dataset',
                dataIndex: 'dataset_name',
                key: 'dataset_name',
                render: (v) => (v ? String(v).replace(/\s+Dataset$/i, '') : '—'),
              },
              {
                title: 'Mean (0–1)',
                dataIndex: 'mean_rating',
                key: 'mean_rating',
                align: 'right',
                defaultSortOrder: 'descend',
                sorter: (a, b) => (a.mean_rating ?? 0) - (b.mean_rating ?? 0),
                render: (v) => (Number.isFinite(v) ? v.toFixed(3) : '—'),
              },
              {
                title: 'SD',
                dataIndex: 'std_rating',
                key: 'std_rating',
                align: 'right',
                render: (v) => (Number.isFinite(v) ? v.toFixed(3) : '—'),
              },
              {
                title: 'Ratings',
                dataIndex: 'n_ratings',
                key: 'n_ratings',
                align: 'right',
                sorter: (a, b) => (a.n_ratings ?? 0) - (b.n_ratings ?? 0),
              },
            ]}
          />
        </Card>
      )}

      {ratingsLoading && (
        <Card style={{ marginTop: 24, textAlign: 'center' }}>
          <Spin />
          <div style={{ marginTop: 8 }}>Loading rating data...</div>
        </Card>
      )}
    </div>
  );
};

export default ItemDetailPage;
