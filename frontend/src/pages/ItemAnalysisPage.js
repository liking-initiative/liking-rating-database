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
  Progress,
  Table,
  Tag,
  Select
} from 'antd';
import { ArrowLeftOutlined, BarChartOutlined, LineChartOutlined } from '@ant-design/icons';
import Plot from 'react-plotly.js';
import { useQuery } from 'react-query';
import { getItem, getRatingAggregations, getRatings, getItemRatingsByDataset } from '../services/api';

const { Title, Text } = Typography;
const { Option } = Select;

const ItemAnalysisPage = () => {
  const { itemId } = useParams();
  const navigate = useNavigate();
  const [chartType, setChartType] = useState('distribution');

  // Validate item ID format
  const isValidUUID = (id) => {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(id);
  };

  // If item ID is invalid format, show error immediately
  if (!isValidUUID(itemId)) {
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

  // Fetch item details
  const { data: item, isLoading: itemLoading, error: itemError } = useQuery(
    ['item', itemId],
    () => getItem(itemId),
    {
      enabled: !!itemId,
      retry: 3,
      staleTime: 5 * 60 * 1000
    }
  );

  // Fetch rating aggregations for this item by dataset
  const { data: ratings, isLoading: ratingsLoading } = useQuery(
    ['itemRatingsByDataset', itemId],
    () => getItemRatingsByDataset(itemId),
    {
      enabled: !!itemId,
      retry: 3,
      staleTime: 5 * 60 * 1000,
    }
  );

  // Fetch individual ratings for detailed analysis
  const { data: individualRatings, isLoading: individualRatingsLoading } = useQuery(
    ['individualRatings', itemId],
    () => getRatings({ item_id: itemId, page_size: 1000 }),
    {
      enabled: !!itemId,
      retry: 3,
      staleTime: 5 * 60 * 1000,
    }
  );

  // Fetch category comparison data
  const { data: categoryRatings, isLoading: categoryLoading } = useQuery(
    ['categoryRatings', item?.category],
    () => getRatingAggregations({ min_ratings: 1 }),
    {
      enabled: !!item?.category,
      retry: 3,
      staleTime: 10 * 60 * 1000,
    }
  );

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

  // Calculate analysis metrics
  const totalRatings = ratings?.reduce((sum, r) => sum + r.n_ratings, 0) || 0;
  const overallMean = ratings?.length > 0 ? 
    ratings.reduce((sum, r) => sum + r.mean_rating * r.n_ratings, 0) / totalRatings : 0;
  const overallStd = ratings?.length > 0 ?
    Math.sqrt(ratings.reduce((sum, r) => sum + Math.pow(r.std_rating || 0, 2) * r.n_ratings, 0) / totalRatings) : 0;

  // Calculate category ranking
  const categoryItems = categoryRatings?.filter(r => r.item_name !== item?.name) || [];
  const betterRatedItems = categoryItems.filter(r => {
    const itemMean = r.mean_rating;
    return itemMean > overallMean;
  }).length;
  const totalCategoryItems = categoryItems.length + 1; // +1 for current item
  const categoryRank = betterRatedItems + 1;

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

  // Generate rating distribution histogram
  const generateDistributionChart = () => {
    if (!individualRatings?.items?.length) return [];

    const ratingCounts = {};
    individualRatings.items.forEach(rating => {
      const score = Math.round(rating.rating);
      ratingCounts[score] = (ratingCounts[score] || 0) + 1;
    });

    const scores = Object.keys(ratingCounts).map(Number).sort((a, b) => a - b);
    const counts = scores.map(score => ratingCounts[score]);

    return [{
      x: scores,
      y: counts,
      type: 'bar',
      name: 'Rating Frequency',
      marker: { color: '#1890ff' },
      text: counts.map(c => c.toString()),
      textposition: 'auto',
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

  // Generate competitive comparison chart
  const generateComparisonChart = () => {
    if (!categoryRatings?.length || !item?.category) return [];

    const categoryItems = categoryRatings
      .filter(r => r.item_name !== item?.name)
      .sort((a, b) => b.mean_rating - a.mean_rating)
      .slice(0, 10); // Top 10 in category

    const currentItemData = ratings?.length > 0 ? {
      item_name: item.name,
      mean_rating: overallMean,
      n_ratings: totalRatings
    } : null;

    const allItems = currentItemData ? [...categoryItems, currentItemData] : categoryItems;
    allItems.sort((a, b) => b.mean_rating - a.mean_rating);

    return [{
      x: allItems.map(r => r.item_name.length > 15 ? r.item_name.substring(0, 15) + '...' : r.item_name),
      y: allItems.map(r => r.mean_rating),
      type: 'bar',
      name: 'Mean Rating',
      marker: {
        color: allItems.map(r => r.item_name === item?.name ? '#ff4d4f' : '#1890ff')
      },
      text: allItems.map(r => `${r.mean_rating.toFixed(2)} (n=${r.n_ratings || 0})`),
      textposition: 'auto',
    }];
  };

  // Generate rating trend over time (dataset trend)
  const generateTrendChart = () => {
    if (!ratings?.length) return [];

    return [{
      x: ratings.map((r, i) => i + 1),
      y: ratings.map(r => r.mean_rating),
      mode: 'lines+markers',
      type: 'scatter',
      name: 'Rating Trend',
      line: { color: '#722ed1', width: 3 },
      marker: { size: 8, color: '#722ed1' }
    }];
  };

  const getChartData = () => {
    switch (chartType) {
      case 'distribution':
        return generateDistributionChart();
      case 'datasets':
        return generateDatasetChart();
      case 'trend':
        return generateTrendChart();
      case 'comparison':
        return generateComparisonChart();
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
      case 'distribution':
        return {
          ...baseLayout,
          title: `Rating Distribution for ${item?.name || 'Item'}`,
          xaxis: { title: 'Rating Value' },
          yaxis: { title: 'Frequency' }
        };
      case 'datasets':
        return {
          ...baseLayout,
          title: `Mean Ratings Across Datasets`,
          xaxis: { title: 'Dataset' },
          yaxis: { title: 'Mean Rating' }
        };
      case 'trend':
        return {
          ...baseLayout,
          title: `Rating Trend Across Studies`,
          xaxis: { title: 'Study Order' },
          yaxis: { title: 'Mean Rating' }
        };
      case 'comparison':
        return {
          ...baseLayout,
          title: `Competitive Analysis - ${item?.category || 'Category'} Items`,
          xaxis: { title: 'Food Items', tickangle: -45 },
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
      </Row>

      {ratingsLoading || individualRatingsLoading ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>Loading rating analysis...</div>
        </div>
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
                  title="Overall Rating"
                  value={overallMean}
                  precision={2}
                  valueStyle={{ color: '#1890ff' }}
                  suffix="/ 10"
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
                  valueStyle={{ color: '#faad14' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title={item?.category ? `Rank in ${item.category}` : "Category Rank"}
                  value={`#${categoryRank}`}
                  valueStyle={{ 
                    color: categoryRank <= 3 ? '#52c41a' : categoryRank <= 10 ? '#faad14' : '#ff4d4f' 
                  }}
                  suffix={`/ ${totalCategoryItems}`}
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
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="Consistency Score"
                  value={Math.max(0, 100 - (overallStd * 20))}
                  precision={0}
                  valueStyle={{
                    color: overallStd < 1 ? '#52c41a' : overallStd < 2 ? '#faad14' : '#ff4d4f'
                  }}
                  suffix="/ 100"
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="Data Quality"
                  value={Math.min(100, (totalRatings / 100) * 100)}
                  precision={0}
                  valueStyle={{ 
                    color: totalRatings >= 100 ? '#52c41a' : totalRatings >= 20 ? '#faad14' : '#ff4d4f' 
                  }}
                  suffix="/ 100"
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
                  <Option value="trend">Rating Trend</Option>
                  <Option value="comparison" disabled={!item?.category || !categoryRatings?.length}>
                    Competitive Analysis
                  </Option>
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

            {/* Rating Quality Indicators */}
            <Col xs={24} lg={8}>
              <Card title="Rating Quality">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Text>Data Completeness</Text>
                    <Progress 
                      percent={Math.min(100, (totalRatings / 1000) * 100)}
                      status="active"
                      strokeColor={{
                        from: '#108ee9',
                        to: '#87d068',
                      }}
                    />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      Based on {totalRatings} total ratings
                    </Text>
                  </div>

                  <div style={{ marginTop: 16 }}>
                    <Text>Rating Consistency</Text>
                    <Progress 
                      percent={Math.max(0, 100 - (overallStd * 20))}
                      strokeColor={{
                        from: '#ff6b6b',
                        to: '#4ecdc4',
                      }}
                    />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      Lower std dev = higher consistency
                    </Text>
                  </div>

                  <div style={{ marginTop: 16 }}>
                    <Text>Dataset Coverage</Text>
                    <Progress 
                      percent={Math.min(100, (ratings.length / 10) * 100)}
                      strokeColor={{
                        from: '#ffd93d',
                        to: '#6bcf7f',
                      }}
                    />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      Item appears in {ratings.length} datasets
                    </Text>
                  </div>
                </Space>
              </Card>

              {/* Item Properties */}
              <Card title="Item Properties" style={{ marginTop: 16 }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Text strong>Category: </Text>
                    {item.category ? (
                      <Tag color="blue">{item.category}</Tag>
                    ) : (
                      <Text type="secondary">Not categorized</Text>
                    )}
                  </div>
                  
                  <div>
                    <Text strong>Frequency: </Text>
                    <Text>{item.frequency || 0} datasets</Text>
                  </div>
                  
                  <div>
                    <Text strong>Image Available: </Text>
                    <Tag color={item.image_available ? 'green' : 'default'}>
                      {item.image_available ? 'Yes' : 'No'}
                    </Tag>
                  </div>
                  
                  {item.aliases && item.aliases.length > 0 && (
                    <div>
                      <Text strong>Aliases: </Text>
                      <div style={{ marginTop: 4 }}>
                        {item.aliases.map((alias, index) => (
                          <Tag key={index} size="small" style={{ marginBottom: 4 }}>
                            {alias}
                          </Tag>
                        ))}
                      </div>
                    </div>
                  )}
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
