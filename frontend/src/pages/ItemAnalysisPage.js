import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Card, 
  Typography, 
  Row, 
  Col, 
  Button, 
  Space, 
  Spin,
  Alert,
  Statistic,
  Table,
  Select
} from 'antd';
import { ArrowLeftOutlined, LineChartOutlined } from '@ant-design/icons';
import Plot from 'react-plotly.js';
import { useQuery } from 'react-query';
import { getItem, getRatingAggregations, getRatings, getItemRatingsByDataset } from '../services/api';

const { Title, Text } = Typography;
const { Option } = Select;

const ItemAnalysisPage = () => {
  const { itemId } = useParams();
  const navigate = useNavigate();
  const [chartType, setChartType] = useState('distribution');

  // Validate item ID format (checked after the hooks below — an early return
  // here would skip hook calls and crash React when the URL param changes)
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
      staleTime: 5 * 60 * 1000
    }
  );

  // Fetch rating aggregations for this item by dataset
  const { data: ratings, isLoading: ratingsLoading, error: ratingsError } = useQuery(
    ['itemRatingsByDataset', itemId],
    () => getItemRatingsByDataset(itemId),
    {
      enabled: validId,
      retry: 3,
      staleTime: 5 * 60 * 1000,
    }
  );

  // Fetch individual ratings for detailed analysis
  const { data: individualRatings, isLoading: individualRatingsLoading } = useQuery(
    ['individualRatings', itemId],
    () => getRatings({ item_id: itemId, page_size: 1000 }),
    {
      enabled: validId,
      retry: 3,
      staleTime: 5 * 60 * 1000,
    }
  );

  // Aggregations behind the rank statistic. Ranking runs over every item in
  // the database rather than within a category: categories here are derived
  // from item names, not supplied by the source studies, so a "rank within
  // category" would report a number that depends on our own guess.
  const { data: allRatingAggregations } = useQuery(
    'allRatingAggregations',
    () => getRatingAggregations({ min_ratings: 1 }),
    { retry: 3, staleTime: 10 * 60 * 1000 }
  );

  const rankDataReady = !!allRatingAggregations;

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
        <div style={{ marginTop: 16 }}>Loading item analysis...</div>
      </div>
    );
  }

  if (itemError || !item) {
    const isNotFound = itemError?.response?.status === 404;
    const errorMessage = isNotFound 
      ? "The requested item could not be found. It may have been removed or the link is invalid."
      : "Failed to load item for analysis. There was a server error.";
    
    return (
      <div style={{ padding: '20px' }}>
        <Alert
          message={isNotFound ? "Item Not Found" : "Error"}
          description={errorMessage}
          type="error"
          showIcon
          action={
            <Space>
              <Button onClick={() => navigate('/items')}>
                Browse Items
              </Button>
              {isNotFound && (
                <Button type="primary" onClick={() => navigate('/items')}>
                  Find Similar Items
                </Button>
              )}
            </Space>
          }
        />
      </div>
    );
  }

  // Calculate analysis metrics. Pooled SD uses the law of total variance:
  // within-dataset variance plus the variance of the dataset means — omitting
  // the between-dataset term understates how much studies disagree.
  const totalRatings = ratings?.reduce((sum, r) => sum + r.n_ratings, 0) || 0;
  const overallMean = ratings?.length > 0 ?
    ratings.reduce((sum, r) => sum + r.mean_rating * r.n_ratings, 0) / totalRatings : 0;
  const withinVar = ratings?.length > 0 ?
    ratings.reduce((sum, r) => sum + Math.pow(r.std_rating || 0, 2) * r.n_ratings, 0) / totalRatings : 0;
  const betweenVar = ratings?.length > 0 ?
    ratings.reduce((sum, r) => sum + Math.pow(r.mean_rating - overallMean, 2) * r.n_ratings, 0) / totalRatings : 0;
  const overallStd = Math.sqrt(withinVar + betweenVar);

  // Rank by mean liking across every item with ratings.
  const otherItems = allRatingAggregations?.filter(r => r.item_id !== itemId) || [];
  const betterRatedItems = otherItems.filter(r => r.mean_rating > overallMean).length;
  const totalRankedItems = otherItems.length + 1; // +1 for the current item
  const overallRank = betterRatedItems + 1;

  // Prepare data for rating distribution table
  const ratingDistribution = ratings?.map((rating, index) => ({
    key: index,
    dataset: rating.study_name || rating.dataset_name || `Dataset ${index + 1}`,
    mean: rating.mean_rating,
    std: rating.std_rating,
    count: rating.n_ratings,
    min: rating.min_rating,
    max: rating.max_rating,
  })) || [];

  const columns = [
    {
      title: 'Dataset',
      dataIndex: 'dataset',
      key: 'dataset',
    },
    {
      title: 'Mean Rating',
      dataIndex: 'mean',
      key: 'mean',
      render: (value) => value?.toFixed(2) || 'N/A',
      sorter: (a, b) => (a.mean || 0) - (b.mean || 0),
    },
    {
      title: 'Std Dev',
      dataIndex: 'std',
      key: 'std',
      render: (value) => value?.toFixed(2) || 'N/A',
      sorter: (a, b) => (a.std || 0) - (b.std || 0),
    },
    {
      title: 'Count',
      dataIndex: 'count',
      key: 'count',
      sorter: (a, b) => a.count - b.count,
    },
    {
      title: 'Min',
      dataIndex: 'min',
      key: 'min',
      render: (value) => value != null ? value.toFixed(2) : 'N/A',
      sorter: (a, b) => {
        // Handle null values - put them at the end
        if (a.min == null && b.min == null) return 0;
        if (a.min == null) return 1;
        if (b.min == null) return -1;
        return a.min - b.min;
      },
    },
    {
      title: 'Max',
      dataIndex: 'max',
      key: 'max',
      render: (value) => value != null ? value.toFixed(2) : 'N/A',
      sorter: (a, b) => {
        // Handle null values - put them at the end
        if (a.max == null && b.max == null) return 0;
        if (a.max == null) return 1;
        if (b.max == null) return -1;
        return a.max - b.max;
      },
    },
  ];

  // Generate rating distribution histogram. An item's ratings span datasets
  // with different original scales (0–10, 1–5, −100..100, …), so the pooled
  // distribution uses normalized ratings and lets Plotly bin them.
  const generateDistributionChart = () => {
    if (!individualRatings?.items?.length) return [];

    return [{
      x: individualRatings.items
        .map(r => r.normalized_rating)
        .filter(v => v !== null && v !== undefined),
      type: 'histogram',
      name: 'Rating Frequency',
      marker: { color: '#085AB3' },
    }];
  };

  // Generate dataset comparison chart
  const generateDatasetChart = () => {
    if (!ratings?.length) return [];

    return [{
      x: ratings.map(r => r.study_name || r.dataset_name || 'Unknown Dataset'),
      y: ratings.map(r => r.mean_rating),
      error_y: {
        type: 'data',
        array: ratings.map(r => r.std_rating || 0),
        visible: true
      },
      type: 'bar',
      name: 'Mean Rating ± SD',
      marker: { color: '#52c41a' },
      text: ratings.map(r => `${r.mean_rating.toFixed(2)} (n=${r.n_ratings})`),
      textposition: 'auto',
    }];
  };

  const getChartData = () => {
    switch (chartType) {
      case 'distribution':
        return generateDistributionChart();
      case 'datasets':
        return generateDatasetChart();
      default:
        return [];
    }
  };

  const getChartLayout = () => {
    const baseLayout = {
      height: 400,
      margin: { t: 50, b: 80, l: 60, r: 50 },
      showlegend: false
    };

    switch (chartType) {
      case 'distribution': {
        const sampled = individualRatings?.total > (individualRatings?.items?.length || 0);
        return {
          ...baseLayout,
          title: `Rating Distribution for ${item?.name || 'Item'}`
            + (sampled ? ` (sample of ${individualRatings.items.length.toLocaleString()} of ${individualRatings.total.toLocaleString()})` : ''),
          xaxis: { title: 'Normalized rating (0–1)' },
          yaxis: { title: 'Count' }
        };
      }
      case 'datasets':
        return {
          ...baseLayout,
          title: `Mean Ratings Across Datasets`,
          xaxis: { title: 'Dataset' },
          yaxis: { title: 'Mean Rating' }
        };
      default:
        return baseLayout;
    }
  };

  return (
    <div>
      {/* Header */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Space>
            <Button 
              icon={<ArrowLeftOutlined />} 
              onClick={() => navigate(`/items/${itemId}`)}
            >
              Back to Item
            </Button>
            <Title level={2} style={{ margin: 0 }}>
              Analysis: {item.name}
            </Title>
          </Space>
        </Col>
        <Col>
          <Button
            type="primary"
            icon={<LineChartOutlined />}
            onClick={() => navigate(`/descriptives?item=${itemId}`)}
          >
            Descriptives
          </Button>
        </Col>
      </Row>

      {ratingsLoading || individualRatingsLoading ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>Loading rating analysis...</div>
        </div>
      ) : ratingsError ? (
        <Alert
          message="Error Loading Ratings"
          description="The rating data for this item could not be loaded. Please try again."
          type="error"
          showIcon
          style={{ marginBottom: 24 }}
        />
      ) : !ratings || ratings.length === 0 ? (
        <Alert
          message="No Rating Data"
          description="No rating data is available for this item. The item may not have been rated in any studies yet."
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
      ) : (
        <>
          {/* Summary Statistics */}
          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="Overall Rating (normalized)"
                  value={overallMean}
                  precision={2}
                  valueStyle={{ color: '#085AB3' }}
                  suffix="/ 1"
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="Total Ratings"
                  value={totalRatings}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="Datasets"
                  value={ratings.length}
                  valueStyle={{ color: '#E78A00' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="Rank by mean liking"
                  value={rankDataReady ? `#${overallRank}` : '—'}
                  valueStyle={{
                    color: !rankDataReady ? undefined
                      : overallRank <= 10 ? '#3f8600' : undefined
                  }}
                  suffix={rankDataReady ? `/ ${totalRankedItems}` : ''}
                />
              </Card>
            </Col>
          </Row>

          {/* Additional Statistics Row */}
          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="Std Deviation"
                  value={overallStd}
                  precision={2}
                  valueStyle={{ color: '#722ed1' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="Rating Range"
                  value={ratings?.length > 0 ? 
                    `${Math.min(...ratings.map(r => r.min_rating || 0)).toFixed(1)} - ${Math.max(...ratings.map(r => r.max_rating || 0)).toFixed(1)}` : 
                    'N/A'
                  }
                  valueStyle={{ color: '#13c2c2' }}
                />
              </Card>
            </Col>
          </Row>

          {/* Visualization Section */}
          <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
            <Col xs={24} md={8}>
              <Card title="Chart Options">
                <div style={{ marginBottom: 16 }}>
                  <Text strong>Visualization Type:</Text>
                </div>
                <Select
                  value={chartType}
                  onChange={setChartType}
                  style={{ width: '100%' }}
                  placeholder="Select chart type"
                >
                  <Option value="distribution">Rating Distribution</Option>
                  <Option value="datasets">Dataset Comparison</Option>
                </Select>
              </Card>
            </Col>
            
            <Col xs={24} md={16}>
              <Card title="Data Visualization">
                {individualRatingsLoading ? (
                  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
                    <Spin size="large" />
                  </div>
                ) : individualRatings?.items?.length > 0 || ratings?.length > 0 ? (
                  <Plot
                    data={getChartData()}
                    layout={getChartLayout()}
                    config={{ responsive: true }}
                    style={{ width: '100%', height: '100%' }}
                  />
                ) : (
                  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
                    <Text type="secondary">No data available for visualization</Text>
                  </div>
                )}
              </Card>
            </Col>
          </Row>

          {/* Rating Distribution */}
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={16}>
              <Card title="Rating Distribution by Dataset">
                <Table
                  columns={columns}
                  dataSource={ratingDistribution}
                  pagination={false}
                  size="small"
                />
              </Card>
            </Col>

            <Col xs={24} lg={8}>
              {/* image_available, aliases and nutritional_info are empty for
                  every item in the database, so only frequency is real here. */}
              <Card title="Item Properties">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Text strong>Appears in: </Text>
                    <Text>{item.frequency || 0} datasets</Text>
                  </div>
                </Space>
              </Card>
            </Col>
          </Row>

        </>
      )}
    </div>
  );
};

export default ItemAnalysisPage;
