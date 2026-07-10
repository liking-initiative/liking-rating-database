import React, { useState } from 'react';
import { Card, Typography, Row, Col, Spin, Select, Alert } from 'antd';
import Plot from 'react-plotly.js';
import { useQuery } from 'react-query';
import { getDatasets, getRatingAggregations, getRatings, getCategories } from '../services/api';

const { Title } = Typography;
const { Option } = Select;

const RATINGS_SAMPLE_SIZE = 1000;

const VisualizationsPage = () => {
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('all');

  // Data queries
  const { data: datasetsData, isLoading: datasetsLoading } = useQuery('datasets', () => getDatasets());
  const { data: categoriesData } = useQuery('categories', getCategories);

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

  // Aggregations for category analysis (each row carries its item category)
  const { data: aggregations, isLoading: aggregationsLoading } = useQuery(
    ['ratingAggregations', selectedDataset, 10],
    () => getRatingAggregations({
      min_ratings: 10,
      ...(selectedDataset && { dataset_ids: [selectedDataset] })
    }),
    {
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
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
      marker: { color: '#1890ff' },
      opacity: 0.7
    };
  };

  const generateCategoryData = () => {
    if (!aggregations?.length) {
      return { x: [], y: [] };
    }

    // Group aggregations by the category the API provides on each row
    const categoryData = {};
    aggregations.forEach(agg => {
      const category = agg.category;
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

  const generateDatasetsPerStudyData = () => {
    if (!datasets?.length) return [];

    // Filter datasets if needed
    const filteredDatasets = selectedDataset
      ? datasets.filter(d => d.id === selectedDataset)
      : datasets;

    // Group by study code (first word of the dataset name) and count datasets
    const studyCounts = {};
    filteredDatasets.forEach(dataset => {
      const studyName = dataset.name.split(' ')[0];
      studyCounts[studyName] = (studyCounts[studyName] || 0) + 1;
    });

    const studies = Object.keys(studyCounts)
      .sort((a, b) => studyCounts[b] - studyCounts[a])
      .slice(0, 15);
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
            placeholder="Select category"
            style={{ width: '100%' }}
            value={selectedCategory}
            onChange={setSelectedCategory}
          >
            <Option value="all">All Categories</Option>
            {categoriesData?.categories?.map(cat => (
              <Option key={cat} value={cat}>{cat.replace(/_/g, ' ')}</Option>
            ))}
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
        
        <Col xs={24} lg={12}>
          <Card title="Category Analysis" style={{ height: 500 }}>
            {aggregationsLoading ? (
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
                      title: selectedCategory === 'all' ? 'Average Normalized Rating by Category' : `Average Normalized Rating — ${selectedCategory}`,
                      xaxis: { title: 'Category', tickangle: -30 },
                      yaxis: { title: 'Mean normalized rating (0–1)', range: [0, 1] },
                      height: 400,
                      margin: { t: 50, b: 90, l: 50, r: 50 }
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
          <Card title="Dataset Distribution by Study" style={{ height: 500 }}>
            {datasets?.length > 0 ? (
              <Plot
                data={[generateDatasetsPerStudyData()]}
                layout={{
                  title: 'Datasets Contributed per Study',
                  xaxis: { title: 'Study (dataset code)', tickangle: -45 },
                  yaxis: { title: 'Number of Datasets' },
                  height: 400,
                  margin: { t: 50, b: 90, l: 50, r: 50 }
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
