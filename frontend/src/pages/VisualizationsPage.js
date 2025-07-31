import React, { useState, useEffect } from 'react';
import { Card, Typography, Row, Col, Empty, Spin, Select } from 'antd';
import { BarChartOutlined } from '@ant-design/icons';
import Plot from 'react-plotly.js';
import { useQuery } from 'react-query';
import { getDatasets, getItems, getRatingAggregations } from '../services/api';

const { Title } = Typography;
const { Option } = Select;

const VisualizationsPage = () => {
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('all');

  // Data queries
  const { data: datasets, isLoading: datasetsLoading } = useQuery('datasets', getDatasets);
  const { data: items, isLoading: itemsLoading } = useQuery('items', getItems);
  
  // Mock data for rating distributions - in real app this would come from API
  const generateRatingDistributionData = () => {
    const ratings = [];
    const bins = [];
    
    // Generate sample data for demonstration
    for (let i = 0; i <= 10; i++) {
      bins.push(i);
      ratings.push(Math.floor(Math.random() * 1000) + 100);
    }
    
    return {
      x: bins,
      y: ratings,
      type: 'bar',
      name: 'Rating Frequency',
      marker: { color: '#1890ff' }
    };
  };

  const generateCategoryData = () => {
    const categories = ['Sweets', 'Chips', 'Fruits', 'Vegetables', 'Crackers', 'Other'];
    const ratings = categories.map(() => Math.random() * 10);
    
    return {
      x: categories,
      y: ratings,
      type: 'bar',
      name: 'Average Rating',
      marker: { color: '#52c41a' }
    };
  };

  const generateStudyComparisonData = () => {
    const studies = datasets?.slice(0, 5)?.map(d => d.name.substring(0, 20) + '...') || 
                   ['Study 1', 'Study 2', 'Study 3', 'Study 4', 'Study 5'];
    const meanRatings = studies.map(() => Math.random() * 5 + 3);
    const stdRatings = studies.map(() => Math.random() * 1 + 0.5);
    
    return {
      x: studies,
      y: meanRatings,
      error_y: {
        type: 'data',
        array: stdRatings,
        visible: true
      },
      type: 'bar',
      name: 'Mean Rating ± SD',
      marker: { color: '#fa8c16' }
    };
  };

  const generateTimeSeriesData = () => {
    const years = Array.from(new Set(datasets?.map(d => d.year) || [2018, 2019, 2020, 2021, 2022, 2023, 2024]));
    years.sort();
    
    const studyCounts = years.map(year => 
      datasets?.filter(d => d.year === year).length || Math.floor(Math.random() * 5) + 1
    );
    
    return {
      x: years,
      y: studyCounts,
      type: 'scatter',
      mode: 'lines+markers',
      name: 'Studies per Year',
      line: { color: '#722ed1' },
      marker: { size: 8, color: '#722ed1' }
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
            <Plot
              data={[generateStudyComparisonData()]}
              layout={{
                title: 'Mean Ratings Across Studies',
                xaxis: { title: 'Study', tickangle: -45 },
                yaxis: { title: 'Mean Rating' },
                height: 400,
                margin: { t: 50, b: 80, l: 50, r: 50 }
              }}
              config={{ responsive: true }}
              style={{ width: '100%', height: '100%' }}
            />
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="Research Timeline" style={{ height: 500 }}>
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
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default VisualizationsPage;
