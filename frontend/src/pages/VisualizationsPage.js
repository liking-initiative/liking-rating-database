import React, { useState } from 'react';
import { Card, Typography, Row, Col, Spin, Select, Alert } from 'antd';
import Plot from 'react-plotly.js';
import { useQuery } from 'react-query';
import { getDatasets, getRatings } from '../services/api';

const { Title } = Typography;
const { Option } = Select;

const RATINGS_SAMPLE_SIZE = 1000;

const VisualizationsPage = () => {
  const [selectedDataset, setSelectedDataset] = useState(null);

  // Data queries
  const { data: datasetsData, isLoading: datasetsLoading } = useQuery('datasets', () => getDatasets());

  // /datasets returns a paginated envelope: { items, total, page, page_size, pages }
  const datasets = datasetsData?.items;

  // Individual ratings for the distribution chart (a sample, for performance)
  const { data: ratingsData, isLoading: ratingsLoading, error: ratingsError } = useQuery(
    ['ratings-sample', selectedDataset, RATINGS_SAMPLE_SIZE],
    () => getRatings({
      page: 1,
      page_size: RATINGS_SAMPLE_SIZE,
      ...(selectedDataset && { dataset_id: selectedDataset })
    }),
    {
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 2,
    }
  );

  
  // Rating distribution over the sample. Across datasets scales differ
  // (-870..870 sliders next to 1..5 likerts), so the pooled view uses
  // normalized ratings; a single dataset shows its original scale.
  const generateRatingDistributionData = () => {
    if (!ratingsData?.items?.length) return [];

    const values = ratingsData.items
      .map(r => (selectedDataset ? r.rating : r.normalized_rating))
      .filter(r => r !== null && r !== undefined);
    if (values.length === 0) return [];

    return {
      x: values,
      type: 'histogram',
      name: 'Rating Frequency',
      marker: { color: '#085AB3' },
      opacity: 0.7
    };
  };

  return (
    <div>
      <Title level={2}>Data Visualizations</Title>
      
      <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
        <Col xs={24} md={16}>
          <Select
            placeholder="Select a dataset"
            style={{ width: '100%' }}
            value={selectedDataset}
            onChange={setSelectedDataset}
            loading={datasetsLoading}
            allowClear
          >
            <Option value={null}>All Datasets</Option>
            {datasets?.map(dataset => (
              <Option key={dataset.id} value={dataset.id}>
                {dataset.name.length > 50 ? dataset.name.substring(0, 50) + '...' : dataset.name}
              </Option>
            ))}
          </Select>
        </Col>
      </Row>
      
      <Row gutter={[24, 24]}>
        <Col xs={24}>
          <Card title="Rating Distributions" style={{ height: 500 }}>
            {ratingsLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
                <Spin size="large" />
              </div>
            ) : ratingsError ? (
              <Alert 
                message="Error loading ratings data" 
                description={`Failed to load ratings: ${ratingsError.message}`}
                type="error" 
              />
            ) : ratingsData?.items?.length > 0 ? (
              <Plot
                data={[generateRatingDistributionData()]}
                layout={{
                  title: `Sample of ${ratingsData.items.length.toLocaleString()} of ${(ratingsData.total || 0).toLocaleString()} ratings`,
                  xaxis: { title: selectedDataset ? 'Rating (original scale)' : 'Normalized rating (0–1)' },
                  yaxis: { title: 'Count' },
                  height: 400,
                  margin: { t: 50, b: 50, l: 50, r: 50 }
                }}
                config={{ responsive: true }}
                style={{ width: '100%', height: '100%' }}
              />
            ) : (
              <Alert 
                message="No rating data available" 
                description={`Rating distribution will appear when data is loaded. Status: ${ratingsData ? 'Data loaded but empty' : 'No data'}`}
                type="info" 
              />
            )}
          </Card>
        </Col>
        
        
      </Row>
    </div>
  );
};

export default VisualizationsPage;
