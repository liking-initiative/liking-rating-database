import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Card, 
  Typography, 
  Row, 
  Col, 
  Tag, 
  Button, 
  Space, 
  Descriptions,
  Spin,
  Alert,
  Statistic,
  Divider
} from 'antd';
import { ArrowLeftOutlined, BarChartOutlined, TagOutlined } from '@ant-design/icons';
import { useQuery } from 'react-query';
import { getItem, getItemRatingsByDataset } from '../services/api';

const { Title, Text } = Typography;

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
          <Button 
            type="primary" 
            icon={<BarChartOutlined />}
            onClick={() => navigate(`/items/${itemId}/analyze`)}
          >
            Analyze Item
          </Button>
        </Col>
      </Row>

      <Row gutter={[24, 24]}>
        {/* Item Information */}
        <Col xs={24} lg={16}>
          <Card title="Item Information">
            <Descriptions column={1} bordered>
              <Descriptions.Item label="Name">
                <strong>{item.name}</strong>
              </Descriptions.Item>
              
              {item.standardized_name && item.standardized_name !== item.name && (
                <Descriptions.Item label="Standardized Name">
                  {item.standardized_name}
                </Descriptions.Item>
              )}
              
              <Descriptions.Item label="Category">
                {item.category ? (
                  <Tag icon={<TagOutlined />} color="blue">
                    {item.category}
                  </Tag>
                ) : (
                  <Text type="secondary">Not specified</Text>
                )}
              </Descriptions.Item>
              
              {item.subcategory && (
                <Descriptions.Item label="Subcategory">
                  <Tag color="geekblue">{item.subcategory}</Tag>
                </Descriptions.Item>
              )}
              
              <Descriptions.Item label="Description">
                {item.description || <Text type="secondary">No description available</Text>}
              </Descriptions.Item>
              
              <Descriptions.Item label="Image Available">
                <Tag color={item.image_available ? 'green' : 'default'}>
                  {item.image_available ? 'Yes' : 'No'}
                </Tag>
              </Descriptions.Item>
              
              {item.aliases && item.aliases.length > 0 && (
                <Descriptions.Item label="Aliases">
                  <Space wrap>
                    {item.aliases.map((alias, index) => (
                      <Tag key={index} color="purple">
                        {alias}
                      </Tag>
                    ))}
                  </Space>
                </Descriptions.Item>
              )}
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
              
              <Col span={24}>
                <Statistic
                  title="Total Occurrences"
                  value={item.frequency || 0}
                  suffix="ratings"
                  valueStyle={{ color: '#722ed1' }}
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

          {/* Nutritional Information */}
          {item.nutritional_info && (
            <Card title="Nutritional Information" style={{ marginTop: 16 }}>
              <Text type="secondary">
                Nutritional information is available for this item.
              </Text>
              {/* You can expand this to show detailed nutritional info */}
            </Card>
          )}
        </Col>
      </Row>

      {/* Rating Details */}
      {ratings && ratings.length > 0 && (
        <Card title="Rating Details" style={{ marginTop: 24 }}>
          <Row gutter={[16, 16]}>
            {ratings.map((rating, index) => (
              <Col key={index} xs={24} sm={12} md={8} lg={6}>
                <Card size="small">
                  <Statistic
                    title={rating.study_name || rating.dataset_name || `Dataset ${index + 1}`}
                    value={rating.mean_rating}
                    precision={2}
                    suffix={`(${rating.n_ratings} ratings)`}
                    valueStyle={{
                      // Ratings are normalized to 0-1, so threshold on that domain
                      color: rating.mean_rating > 0.6 ? '#52c41a' :
                             rating.mean_rating > 0.4 ? '#E78A00' : '#ff4d4f'
                    }}
                  />
                  <div style={{ fontSize: '13.5px', color: '#4a4a4a', marginTop: 8 }}>
                    Std Dev: {rating.std_rating?.toFixed(2) || 'N/A'}
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
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
