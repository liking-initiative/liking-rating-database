import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Typography, Row, Col, Spin, Button, Select, Alert } from 'antd';
import { ArrowLeftOutlined, BarChartOutlined } from '@ant-design/icons';
import Plot from 'react-plotly.js';
import { useQuery } from 'react-query';
import { getDataset, getRatings } from '../services/api';

const { Title, Text } = Typography;
const { Option } = Select;

const DatasetVisualizationPage = () => {
  const { datasetId } = useParams();
  const navigate = useNavigate();
  const [chartType, setChartType] = useState('histogram');

  // Fetch dataset details and ratings
  const { data: dataset, isLoading: datasetLoading, error: datasetError } = useQuery(
    ['dataset', datasetId],
    () => getDataset(datasetId),
    { enabled: !!datasetId }
  );

  const { data: ratings, isLoading: ratingsLoading, error: ratingsError } = useQuery(
    ['ratings', datasetId],
    () => getRatings({ dataset_id: datasetId }),
    { enabled: !!datasetId }
  );

  const isLoading = datasetLoading || ratingsLoading;
  const hasError = datasetError || ratingsError;

  // Generate rating distribution histogram.
  // Ratings are passed raw and binned by Plotly — rounding to integers would
  // destroy continuous scales (e.g. −870..870 sliders or 0–10 analog scales).
  const generateHistogramData = () => {
    if (!ratings?.items?.length) return [];

    return [{
      x: ratings.items.map(r => r.rating),
      type: 'histogram',
      name: 'Rating Frequency',
      marker: { color: '#085AB3' },
    }];
  };

  // Generate top items bar chart
  const generateTopItemsData = () => {
    if (!ratings?.items?.length) return [];

    const itemRatings = {};
    ratings.items.forEach(rating => {
      const itemName = rating.item_name || `Item ${rating.item_id}`;
      if (!itemRatings[itemName]) {
        itemRatings[itemName] = { total: 0, count: 0 };
      }
      itemRatings[itemName].total += rating.rating;
      itemRatings[itemName].count += 1;
    });

    const itemAverages = Object.entries(itemRatings)
      .map(([name, data]) => ({
        name,
        average: data.total / data.count,
        count: data.count
      }))
      .sort((a, b) => b.average - a.average)
      .slice(0, 20); // Top 20 items

    return [{
      x: itemAverages.map(item => item.name.length > 15 ? item.name.substring(0, 15) + '...' : item.name),
      y: itemAverages.map(item => item.average),
      type: 'bar',
      name: 'Average Rating',
      marker: { color: '#52c41a' },
      text: itemAverages.map(item => `${item.average.toFixed(2)} (n=${item.count})`),
      textposition: 'auto',
    }];
  };

  // Generate rating variability scatter plot
  const generateVariabilityData = () => {
    if (!ratings?.items?.length) return [];

    const itemStats = {};
    ratings.items.forEach(rating => {
      const itemName = rating.item_name || `Item ${rating.item_id}`;
      if (!itemStats[itemName]) {
        itemStats[itemName] = [];
      }
      itemStats[itemName].push(rating.rating);
    });

    const variabilityData = Object.entries(itemStats)
      .map(([name, ratingList]) => {
        const mean = ratingList.reduce((a, b) => a + b, 0) / ratingList.length;
        const variance = ratingList.reduce((acc, rating) => acc + Math.pow(rating - mean, 2), 0) / ratingList.length;
        const std = Math.sqrt(variance);
        return {
          name,
          mean,
          std,
          count: ratingList.length
        };
      })
      .filter(item => item.count >= 5); // Only items with at least 5 ratings

    return [{
      x: variabilityData.map(item => item.mean),
      y: variabilityData.map(item => item.std),
      mode: 'markers',
      type: 'scatter',
      name: 'Items',
      marker: {
        size: variabilityData.map(item => Math.min(item.count / 2 + 5, 20)),
        color: variabilityData.map(item => item.mean),
        colorscale: 'Viridis',
        showscale: true,
        colorbar: { title: 'Mean Rating' }
      },
      text: variabilityData.map(item => 
        `${item.name}<br>Mean: ${item.mean.toFixed(2)}<br>SD: ${item.std.toFixed(2)}<br>Count: ${item.count}`
      ),
      hovertemplate: '%{text}<extra></extra>'
    }];
  };

  const getChartData = () => {
    switch (chartType) {
      case 'histogram':
        return generateHistogramData();
      case 'topItems':
        return generateTopItemsData();
      case 'variability':
        return generateVariabilityData();
      default:
        return [];
    }
  };

  const getChartLayout = () => {
    const baseLayout = {
      height: 500,
      margin: { t: 50, b: 100, l: 60, r: 50 },
      showlegend: false
    };

    switch (chartType) {
      case 'histogram':
        return {
          ...baseLayout,
          title: 'Rating Distribution (original scale)',
          xaxis: { title: 'Rating Value' },
          yaxis: { title: 'Count' }
        };
      case 'topItems':
        return {
          ...baseLayout,
          title: 'Top Rated Items',
          xaxis: { title: 'Food Items', tickangle: -45 },
          yaxis: { title: 'Average Rating' }
        };
      case 'variability':
        return {
          ...baseLayout,
          title: 'Rating Variability vs Mean Rating',
          xaxis: { title: 'Mean Rating' },
          yaxis: { title: 'Standard Deviation' }
        };
      default:
        return baseLayout;
    }
  };

  if (hasError) {
    return (
      <div>
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={() => navigate(-1)}
          style={{ marginBottom: 16 }}
        >
          Back
        </Button>
        <Alert
          message="Error Loading Data"
          description="Unable to load dataset or rating data for visualization."
          type="error"
          showIcon
        />
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={() => navigate(-1)}
            style={{ marginBottom: 16 }}
          >
            Back
          </Button>
          <Title level={2}>
            <BarChartOutlined style={{ marginRight: 8 }} />
            Dataset Visualization
          </Title>
          {dataset && (
            <Text type="secondary" style={{ fontSize: '16px' }}>
              {dataset.name} - {dataset.description}
            </Text>
          )}
        </div>
      </div>

      <Row gutter={[24, 24]}>
        <Col xs={24} md={8}>
          <Card title="Chart Options">
            <div style={{ marginBottom: 16 }}>
              <Text strong>Chart Type:</Text>
            </div>
            <Select
              value={chartType}
              onChange={setChartType}
              style={{ width: '100%' }}
              placeholder="Select chart type"
            >
              <Option value="histogram">Rating Distribution</Option>
              <Option value="topItems">Top Rated Items</Option>
              <Option value="variability">Rating Variability</Option>
            </Select>
            
            {dataset && (
              <div style={{ marginTop: 20 }}>
                <Title level={4}>Dataset Info</Title>
                <Text><strong>Study:</strong> {dataset.study?.name}</Text><br />
                <Text><strong>Year:</strong> {dataset.study?.year}</Text><br />
                <Text><strong>Total Ratings:</strong> {
                  (dataset.n_ratings ?? ratings?.items?.length ?? 0).toLocaleString()
                }</Text><br />
                <Text><strong>Unique Items:</strong> {
                  dataset.n_items ?? (ratings?.items ? new Set(ratings.items.map(r => r.item_id)).size : 0)
                }</Text>
              </div>
            )}
          </Card>
        </Col>
        
        <Col xs={24} md={16}>
          <Card title="Visualization">
            {isLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 500 }}>
                <Spin size="large" />
              </div>
            ) : ratings?.items?.length > 0 ? (
              <>
                {dataset?.n_ratings > ratings.items.length && (
                  <p className="page-caption">
                    {`Charts are computed from a sample of ${ratings.items.length.toLocaleString()} of ${dataset.n_ratings.toLocaleString()} ratings.`}
                  </p>
                )}
                <Plot
                  data={getChartData()}
                  layout={getChartLayout()}
                  config={{ responsive: true }}
                  style={{ width: '100%', height: '100%' }}
                />
              </>
            ) : (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 500 }}>
                <Text type="secondary">No rating data available for visualization</Text>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default DatasetVisualizationPage;
