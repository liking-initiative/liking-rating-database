import React from 'react';
import { Card, Typography, Button, Space, Row, Col, Alert, Divider, Statistic, Spin } from 'antd';
import { DownloadOutlined, FileTextOutlined, SearchOutlined, DatabaseOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from 'react-query';
import AccessCode from '../components/AccessCode';
import { getDatabaseArchiveInfo, databaseArchiveUrl } from '../services/api';

const { Title, Paragraph } = Typography;

const DownloadsPage = () => {
  const navigate = useNavigate();
  // The archive is built on the server's first request, so this can take a
  // few seconds on a cold start.
  const { data: archive, isLoading: archiveLoading } = useQuery(
    'database-archive-info',
    getDatabaseArchiveInfo,
    { staleTime: 60 * 60 * 1000, retry: 1 }
  );

  return (
    <div>
      <Title level={2}>Data Downloads</Title>
      
      <Alert
        message="Three ways to get the data"
        description="Take the whole database as one archive below, pull it straight into R or Python, or download individual datasets from any study, dataset, or search result page."
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Card
        title="Download the entire database"
        style={{ marginBottom: 24 }}
        extra={
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            href={databaseArchiveUrl()}
          >
            Download ZIP
          </Button>
        }
      >
        <Paragraph>
          Every rating in the database, plus the study, dataset, and item
          metadata needed to interpret it, and a codebook explaining each
          column. This is the fastest way to get the whole corpus — one file
          instead of walking the API dataset by dataset.
        </Paragraph>
        {archiveLoading ? (
          <Spin />
        ) : archive ? (
          <Row gutter={[24, 16]}>
            <Col xs={12} sm={6}>
              <Statistic title="Ratings" value={archive.n_ratings} />
            </Col>
            <Col xs={12} sm={6}>
              <Statistic title="Studies" value={archive.n_studies} />
            </Col>
            <Col xs={12} sm={6}>
              <Statistic title="Datasets" value={archive.n_datasets} />
            </Col>
            <Col xs={12} sm={6}>
              <Statistic
                title="Archive size"
                value={(archive.size_bytes / 1024 / 1024).toFixed(1)}
                suffix="MB"
              />
            </Col>
          </Row>
        ) : (
          <Alert
            type="info"
            showIcon
            message="Archive size unavailable right now — the download link still works."
          />
        )}
      </Card>

      <AccessCode title="Or pull it straight into R or Python" />

      <Divider />

      <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
        <Col xs={24} md={8}>
          <Card 
            title="Search & Browse" 
            hoverable
            onClick={() => navigate('/search')}
            style={{ cursor: 'pointer', height: '100%' }}
          >
            <Space direction="vertical" style={{ width: '100%', textAlign: 'center' }}>
              <SearchOutlined style={{ fontSize: '32px', color: '#085AB3' }} />
              <Paragraph>
                Find specific datasets by searching for studies, authors, food items, or other criteria.
              </Paragraph>
              <Button type="primary" block>
                Start Searching
              </Button>
            </Space>
          </Card>
        </Col>

        <Col xs={24} md={8}>
          <Card 
            title="Browse Studies" 
            hoverable
            onClick={() => navigate('/studies')}
            style={{ cursor: 'pointer', height: '100%' }}
          >
            <Space direction="vertical" style={{ width: '100%', textAlign: 'center' }}>
              <DatabaseOutlined style={{ fontSize: '32px', color: '#52c41a' }} />
              <Paragraph>
                Browse all available studies and download individual or multiple datasets from each study.
              </Paragraph>
              <Button type="primary" block>
                Browse Studies
              </Button>
            </Space>
          </Card>
        </Col>

        <Col xs={24} md={8}>
          <Card 
            title="Food Items" 
            hoverable
            onClick={() => navigate('/items')}
            style={{ cursor: 'pointer', height: '100%' }}
          >
            <Space direction="vertical" style={{ width: '100%', textAlign: 'center' }}>
              <DownloadOutlined style={{ fontSize: '32px', color: '#E78A00' }} />
              <Paragraph>
                Explore food items and access rating data across multiple studies for comparative analysis.
              </Paragraph>
              <Button type="primary" block>
                Explore Items
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      <Divider />

      <Card title={<><FileTextOutlined /> Download Formats</>} style={{ marginBottom: 24 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <div style={{ textAlign: 'center' }}>
                <Title level={4} style={{ color: '#085AB3', margin: '8px 0' }}>CSV</Title>
                <Paragraph style={{ fontSize: '12px', margin: 0 }}>
                  Comma-separated values format, compatible with Excel, R, Python, and most data analysis tools.
                </Paragraph>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <div style={{ textAlign: 'center' }}>
                <Title level={4} style={{ color: '#52c41a', margin: '8px 0' }}>JSON</Title>
                <Paragraph style={{ fontSize: '12px', margin: 0 }}>
                  JavaScript Object Notation, ideal for web applications and API integration.
                </Paragraph>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <div style={{ textAlign: 'center' }}>
                <Title level={4} style={{ color: '#E78A00', margin: '8px 0' }}>Excel</Title>
                <Paragraph style={{ fontSize: '12px', margin: 0 }}>
                  Microsoft Excel format (.xlsx) with formatted sheets and metadata.
                </Paragraph>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <div style={{ textAlign: 'center' }}>
                <Title level={4} style={{ color: '#722ed1', margin: '8px 0' }}>SPSS</Title>
                <Paragraph style={{ fontSize: '12px', margin: 0 }}>
                  SPSS format (.sav) for direct import into statistical analysis software.
                </Paragraph>
              </div>
            </Card>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default DownloadsPage;
