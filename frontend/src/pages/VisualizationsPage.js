import React, { useState, useEffect } from 'react';
import { Card, Typography, Row, Col, Empty, Spin, Select, Alert } from 'antd';
import { BarChartOutlined } from '@ant-design/icons';
import Plot from 'react-plotly.js';
import { useQuery } from 'react-query';
import { getDatasets, getItems, getRatingAggregations, getStatistics, getRatings } from '../services/api';

const { Title } = Typography;
const { Option } = Select;

const VisualizationsPage = () => {
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('all');

  // Data queries
  const { data: datasets, isLoading: datasetsLoading } = useQuery('datasets', getDatasets);
  const { data: items, isLoading: itemsLoading } = useQuery('items', getItems);
  const { data: statistics, isLoading: statsLoading } = useQuery('statistics', getStatistics);
  
  // Get individual ratings for histogram (limited to 1k for performance)
  const { data: ratingsData, isLoading: ratingsLoading, error: ratingsError } = useQuery(
    ['ratings', selectedDataset], 
    () => getRatings({ 
      page: 1, 
      page_size: 1000, // Start with smaller number
      ...(selectedDataset && { dataset_id: selectedDataset })
    }),
    {
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
      enabled: true, // Explicitly enable the query
      retry: 2,
      onError: (error) => {
        console.error('Ratings query error:', error);
      },
      onSuccess: (data) => {
        console.log('Ratings data loaded:', data?.items?.length, 'items');
      }
    }
  );
  
  // Get aggregations for category analysis
  const { data: aggregations, isLoading: aggregationsLoading } = useQuery(
    ['ratingAggregations', selectedDataset], 
    () => getRatingAggregations({ 
      min_ratings: 10,
      ...(selectedDataset && { dataset_ids: [selectedDataset] })
    }),
    {
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );
  
  // Real data for rating distributions using individual ratings
  const generateRatingDistributionData = () => {
    if (!ratingsData?.items?.length) return [];
    
    // Create histogram bins for ratings
    const ratings = ratingsData.items.map(r => r.rating).filter(r => r !== null && r !== undefined);
    if (ratings.length === 0) return [];
    
    const minRating = Math.min(...ratings);
    const maxRating = Math.max(...ratings);
    
    // If all ratings are the same, create a single bin
    if (minRating === maxRating) {
      return {
        x: [minRating],
        y: [ratings.length],
        type: 'bar',
        name: 'Rating Frequency',
        marker: { color: '#1890ff' },
        opacity: 0.7
      };
    }
    
    // Create 20 bins
    const numBins = 20;
    const binSize = (maxRating - minRating) / numBins;
    const bins = [];
    const binCounts = [];
    
    for (let i = 0; i < numBins; i++) {
      const binStart = minRating + i * binSize;
      const binEnd = minRating + (i + 1) * binSize;
      bins.push(binStart + binSize / 2); // Use bin center
      
      // Include the last bin's upper bound
      const count = i === numBins - 1 
        ? ratings.filter(r => r >= binStart && r <= binEnd).length
        : ratings.filter(r => r >= binStart && r < binEnd).length;
      binCounts.push(count);
    }
    
    return {
      x: bins,
      y: binCounts,
      type: 'bar',
      name: 'Rating Frequency',
      marker: { color: '#1890ff' },
      opacity: 0.7
    };
  };

  const generateCategoryData = () => {
    if (!aggregations?.length || !items?.items?.length) {
      return { x: [], y: [] };
    }
    
    // Create a map of item_id to category
    const itemCategoryMap = {};
    items.items.forEach(item => {
      itemCategoryMap[item.id] = item.category;
    });
    
    // Group aggregations by category
    const categoryData = {};
    aggregations.forEach(agg => {
      const category = itemCategoryMap[agg.item_id];
      if (category && agg.mean_rating !== null && agg.mean_rating !== undefined) {
        if (!categoryData[category]) {
          categoryData[category] = { ratings: [], count: 0 };
        }
        categoryData[category].ratings.push(agg.mean_rating);
        categoryData[category].count += agg.n_ratings;
      }
    });
    
    // Filter by selected category
    const filteredCategories = selectedCategory === 'all' 
      ? Object.keys(categoryData)
      : Object.keys(categoryData).filter(cat => cat === selectedCategory);
    
    if (filteredCategories.length === 0) {
      return { x: [], y: [] };
    }
    
    const categories = filteredCategories;
    const avgRatings = categories.map(cat => {
      const ratings = categoryData[cat].ratings;
      return ratings.reduce((sum, r) => sum + r, 0) / ratings.length;
    });
    
    return {
      x: categories,
      y: avgRatings,
      type: 'bar',
      name: 'Average Rating',
      marker: { color: '#52c41a' }
    };
  };

  const generateStudyComparisonData = () => {
    if (!datasets?.length) return [];
    
    // Filter datasets if a specific dataset is selected
    const filteredDatasets = selectedDataset 
      ? datasets.filter(d => d.id === selectedDataset)
      : datasets.slice(0, 15); // Show top 15 for readability
    
    const studyData = filteredDatasets.map(dataset => ({
      name: dataset.name.length > 25 ? dataset.name.substring(0, 25) + '...' : dataset.name,
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
    
    // Filter datasets if needed
    const filteredDatasets = selectedDataset 
      ? datasets.filter(d => d.id === selectedDataset)
      : datasets;
    
    // Group by study and count datasets per study
    const studyCounts = {};
    filteredDatasets.forEach(dataset => {
      const studyName = dataset.name.split(' ')[0]; // Get first word as study identifier
      studyCounts[studyName] = (studyCounts[studyName] || 0) + 1;
    });
    
    const studies = Object.keys(studyCounts).slice(0, 15); // Top 15 studies by dataset count
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
            <Option value="other">Other</Option>
          </Select>
        </Col>
      </Row>
      
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={12}>
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
                  title: `Distribution of ${ratingsData.items.length.toLocaleString()} Ratings`,
                  xaxis: { title: 'Rating Value' },
                  yaxis: { title: 'Frequency' },
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
        
        <Col xs={24} lg={12}>
          <Card title="Food Category Analysis" style={{ height: 500 }}>
            {aggregationsLoading || itemsLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
                <Spin size="large" />
              </div>
            ) : (
              (() => {
                const categoryData = generateCategoryData();
                return categoryData.x?.length > 0 ? (
                  <Plot
                    data={[categoryData]}
                    layout={{
                      title: selectedCategory === 'all' ? 'Average Ratings by Food Category' : `Average Ratings - ${selectedCategory}`,
                      xaxis: { title: 'Food Category' },
                      yaxis: { title: 'Average Rating' },
                      height: 400,
                      margin: { t: 50, b: 50, l: 50, r: 50 }
                    }}
                    config={{ responsive: true }}
                    style={{ width: '100%', height: '100%' }}
                  />
                ) : (
                  <Alert 
                    message="No category data available" 
                    description={selectedCategory === 'all' ? "Category analysis will appear when data is loaded." : `No data available for category: ${selectedCategory}`}
                    type="info" 
                  />
                );
              })()
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
