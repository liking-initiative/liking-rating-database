import React, { useState, useEffect } from 'react';
import { Card, Typography, Row, Col, Empty, Spin, Select, Alert } from 'antd';
import { BarChartOutlined } from '@ant-design/icons';
import Plot from 'react-plotly.js';
import { useQuery } from 'react-query';
import { getDatasets, getItems, getRatingAggregations, getStatistics } from '../services/api';

const { Title } = Typography;
const { Option } = Select;

const VisualizationsPage = () => {
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('all');

  // Data queries
  const { data: datasets, isLoading: datasetsLoading } = useQuery('datasets', getDatasets);
  const { data: items, isLoading: itemsLoading } = useQuery('items', getItems);
  const { data: statistics, isLoading: statsLoading } = useQuery('statistics', getStatistics);
  const { data: aggregations, isLoading: aggregationsLoading } = useQuery(
    'ratingAggregations', 
    () => getRatingAggregations({ min_ratings: 10 })
  );
  
  // Real data for rating distributions
  const generateRatingDistributionData = () => {
    if (!aggregations?.length) return [];
    
    // Create rating distribution from actual data
    const ratingCounts = {};
    aggregations.forEach(item => {
      if (item.mean_rating) {
        const bin = Math.floor(item.mean_rating);
        ratingCounts[bin] = (ratingCounts[bin] || 0) + 1;
      }
    });
    
    const bins = Object.keys(ratingCounts).map(Number).sort((a, b) => a - b);
    const counts = bins.map(bin => ratingCounts[bin]);
    
    return {
      x: bins,
      y: counts,
      type: 'bar',
      name: 'Rating Frequency',
      marker: { color: '#1890ff' }
    };
  };

  const generateCategoryData = () => {
    if (!aggregations?.length) return [];
    
    // Group by category and calculate average ratings
    const categoryData = {};
    aggregations.forEach(item => {
      if (item.category && item.mean_rating) {
        if (!categoryData[item.category]) {
          categoryData[item.category] = { sum: 0, count: 0 };
        }
        categoryData[item.category].sum += item.mean_rating;
        categoryData[item.category].count += 1;
      }
    });
    
    const categories = Object.keys(categoryData);
    const ratings = categories.map(cat => categoryData[cat].sum / categoryData[cat].count);
    
    return {
      x: categories,
      y: ratings,
      type: 'bar',
      name: 'Average Rating',
      marker: { color: '#52c41a' }
    };
  };

  const generateStudyComparisonData = () => {
    if (!datasets?.length) return [];
    
    const studyData = datasets.slice(0, 10).map(dataset => ({
      name: dataset.name.length > 20 ? dataset.name.substring(0, 20) + '...' : dataset.name,
      subjects: dataset.n_subjects || 0,
      items: dataset.n_items || 0
    }));
    
    return {
      x: studyData.map(s => s.name),
      y: studyData.map(s => s.subjects),
      type: 'bar',
      name: 'Number of Subjects',
      marker: { color: '#fa8c16' }
    };
  };

  const generateTimeSeriesData = () => {
    if (!datasets?.length) return [];
    
    // Since datasets don't have years, let's group by study and count datasets per study
    const studyCounts = {};
    datasets.forEach(dataset => {
      const studyName = dataset.name.split(' ')[0]; // Get first word as study identifier
      studyCounts[studyName] = (studyCounts[studyName] || 0) + 1;
    });
    
    const studies = Object.keys(studyCounts).slice(0, 10); // Top 10 studies by dataset count
    const counts = studies.map(study => studyCounts[study]);
    
    return {
      x: studies,
      y: counts,
      type: 'bar',
      name: 'Datasets per Study',
      marker: { color: '#722ed1' }
    };
  };

  return (
    <div>
      <Title level={2}>Data Visualizations</Title>
      
      <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
        <Col xs={24} md={12}>
          <Select
            placeholder="Select a dataset"
            style={{ width: '100%' }}
            value={selectedDataset}
            onChange={setSelectedDataset}
            loading={datasetsLoading}
          >
            <Option value={null}>All Datasets</Option>
            {datasets?.map(dataset => (
              <Option key={dataset.id} value={dataset.id}>
                {dataset.name}
              </Option>
            ))}
          </Select>
        </Col>
        <Col xs={24} md={12}>
          <Select
            placeholder="Select food category"
            style={{ width: '100%' }}
            value={selectedCategory}
            onChange={setSelectedCategory}
          >
            <Option value="all">All Categories</Option>
            <Option value="sweets">Sweets</Option>
            <Option value="chips">Chips</Option>
            <Option value="fruits">Fruits</Option>
            <Option value="vegetables">Vegetables</Option>
          </Select>
        </Col>
      </Row>
      
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={12}>
          <Card title="Rating Distributions" style={{ height: 500 }}>
            {datasetsLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
                <Spin size="large" />
              </div>
            ) : (
              <Plot
                data={[generateRatingDistributionData()]}
                layout={{
                  title: 'Distribution of Ratings',
                  xaxis: { title: 'Rating Value' },
                  yaxis: { title: 'Frequency' },
                  height: 400,
                  margin: { t: 50, b: 50, l: 50, r: 50 }
                }}
                config={{ responsive: true }}
                style={{ width: '100%', height: '100%' }}
              />
            )}
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="Food Category Analysis" style={{ height: 500 }}>
            {itemsLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
                <Spin size="large" />
              </div>
            ) : (
              <Plot
                data={[generateCategoryData()]}
                layout={{
                  title: 'Average Ratings by Food Category',
                  xaxis: { title: 'Food Category' },
                  yaxis: { title: 'Average Rating' },
                  height: 400,
                  margin: { t: 50, b: 50, l: 50, r: 50 }
                }}
                config={{ responsive: true }}
                style={{ width: '100%', height: '100%' }}
              />
            )}
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="Cross-Study Comparisons" style={{ height: 500 }}>
            {datasets?.length > 0 ? (
              <Plot
                data={[generateStudyComparisonData()]}
                layout={{
                  title: 'Number of Subjects Across Studies',
                  xaxis: { title: 'Study', tickangle: -45 },
                  yaxis: { title: 'Number of Subjects' },
                  height: 400,
                  margin: { t: 50, b: 80, l: 50, r: 50 }
                }}
                config={{ responsive: true }}
                style={{ width: '100%', height: '100%' }}
              />
            ) : (
              <Alert 
                message="No study data available" 
                description="Study comparison will appear when data is loaded."
                type="info" 
              />
            )}
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card             title="Dataset Distribution by Study" style={{ height: 500 }}>
            {datasets?.length > 0 ? (
              <Plot
                data={[generateTimeSeriesData()]}
                layout={{
                  title: 'Research Activity Over Time',
                  xaxis: { title: 'Year' },
                  yaxis: { title: 'Number of Studies' },
                  height: 400,
                  margin: { t: 50, b: 50, l: 50, r: 50 }
                }}
                config={{ responsive: true }}
                style={{ width: '100%', height: '100%' }}
              />
            ) : (
              <Alert 
                message="No timeline data available" 
                description="Research timeline will appear when data is loaded."
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
