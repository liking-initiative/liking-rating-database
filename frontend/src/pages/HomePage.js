import React from 'react';
import { Typography, Row, Col, Card, Statistic, Button, Space, Alert } from 'antd';
import { 
  ExperimentOutlined, 
  DatabaseOutlined, 
  StarOutlined, 
  AppleOutlined,
  SearchOutlined,
  DownloadOutlined,
  BarChartOutlined 
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from 'react-query';
import { getStatistics } from '../services/api';

const { Title, Paragraph } = Typography;

const HomePage = () => {
  const navigate = useNavigate();
  
  const { data: statistics, isLoading, error: statsError } = useQuery('statistics', getStatistics);

  return (
    <div>
      {/* Hero Section */}
      <div style={{ textAlign: 'center', marginBottom: '48px' }}>
        <Title level={1}>
          Liking Rating Database
        </Title>
        <Paragraph style={{ fontSize: '18px', color: '#666', maxWidth: '800px', margin: '0 auto' }}>
          A curated database of liking ratings — food and consumer products —
          from published decision-making studies. Explore, analyze, and download
          standardized preference data for your research.
        </Paragraph>
        <Space size="large" style={{ marginTop: '24px' }}>
          <Button 
            type="primary" 
            size="large" 
            icon={<SearchOutlined />}
            onClick={() => navigate('/search')}
          >
            Start Browsing
          </Button>
          <Button 
            size="large" 
            icon={<DownloadOutlined />}
            onClick={() => navigate('/downloads')}
          >
            Download Data
          </Button>
        </Space>
      </div>

      {/* Statistics */}
      {statsError && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="Database statistics are temporarily unavailable"
        />
      )}
      <Row gutter={[24, 24]} style={{ marginBottom: '48px' }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Studies"
              value={statistics?.total_studies || 0}
              loading={isLoading}
              prefix={<ExperimentOutlined />}
              valueStyle={{ color: '#085AB3' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Datasets"
              value={statistics?.total_datasets || 0}
              loading={isLoading}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Ratings"
              value={statistics?.total_ratings || 0}
              loading={isLoading}
              prefix={<StarOutlined />}
              valueStyle={{ color: '#E78A00' }}
              formatter={(value) => value?.toLocaleString()}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Items"
              value={statistics?.total_items || 0}
              loading={isLoading}
              prefix={<AppleOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Features */}
      <Row gutter={[24, 24]}>
        <Col xs={24} md={8}>
          <Card 
            title="Advanced Search" 
            hoverable
            onClick={() => navigate('/search')}
            style={{ cursor: 'pointer' }}
          >
            <Paragraph>
              Search and filter datasets by study characteristics, food categories, 
              rating scales, and more. Find exactly the data you need for your research.
            </Paragraph>
            <Button type="link" icon={<SearchOutlined />}>
              Explore Search →
            </Button>
          </Card>
        </Col>
        
        <Col xs={24} md={8}>
          <Card 
            title="Multiple Export Formats" 
            hoverable
            onClick={() => navigate('/downloads')}
            style={{ cursor: 'pointer' }}
          >
            <Paragraph>
              Download data in your preferred format: CSV, Excel, JSON, or SPSS. 
              All exports include comprehensive metadata and documentation.
            </Paragraph>
            <Button type="link" icon={<DownloadOutlined />}>
              View Downloads →
            </Button>
          </Card>
        </Col>
        
        <Col xs={24} md={8}>
          <Card 
            title="Interactive Visualizations" 
            hoverable
            onClick={() => navigate('/visualizations')}
            style={{ cursor: 'pointer' }}
          >
            <Paragraph>
              Explore rating distributions, cross-study comparisons, and food preference 
              patterns through interactive charts and visualizations.
            </Paragraph>
            <Button type="link" icon={<BarChartOutlined />}>
              View Visualizations →
            </Button>
          </Card>
        </Col>
      </Row>

      {/* Recent Activity or Quick Links */}
      <div style={{ marginTop: '48px', textAlign: 'center' }}>
        <Title level={3}>Get Started</Title>
        <Space direction="vertical" size="middle">
          <Paragraph>
            New to the database? Start by browsing our collection of studies or 
            search for specific food items and rating data.
          </Paragraph>
          <Space>
            <Button onClick={() => navigate('/studies')}>
              Browse Studies
            </Button>
            <Button onClick={() => navigate('/items')}>
              View Food Items
            </Button>
            <Button onClick={() => navigate('/about')}>
              Learn More
            </Button>
          </Space>
        </Space>
      </div>
    </div>
  );
};

export default HomePage;
