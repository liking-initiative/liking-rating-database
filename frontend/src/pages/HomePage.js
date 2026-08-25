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
        <Paragraph style={{ fontSize: '17px', color: '#4a4a4a', maxWidth: '760px', margin: '0 auto' }}>
          The Liking Rating Database is a collection of subjective liking
          ratings from published decision-making studies. It currently contains
          individual item level ratings from published studies providing
          researchers with access to a large set of preference data.
        </Paragraph>
        <Paragraph style={{ color: '#5a5a5a', fontSize: 14, marginTop: 14 }}>
          The Liking Initiative is built and maintained by{' '}
          <a
            href="https://kiantefernandez.com"
            target="_blank"
            rel="noreferrer"
          >
            Kianté Fernandez
          </a>
          .
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
              Filter datasets by study, category, rating scale, and year.
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
              The whole database as one archive, or any dataset as CSV, Excel,
              JSON, or SPSS.
            </Paragraph>
            <Button type="link" icon={<DownloadOutlined />}>
              View Downloads →
            </Button>
          </Card>
        </Col>
        
        <Col xs={24} md={8}>
          <Card 
            title="Descriptive Statistics" 
            hoverable
            onClick={() => navigate('/descriptives')}
            style={{ cursor: 'pointer' }}
          >
            <Paragraph>
              How an item was rated within a study, how that shifts across
              studies, and which items the same people liked together.
            </Paragraph>
            <Button type="link" icon={<BarChartOutlined />}>
              View Descriptives →
            </Button>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default HomePage;
