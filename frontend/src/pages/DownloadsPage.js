import React from 'react';
import { Card, Typography, Button, Space, Empty, Row, Col, Alert, Divider } from 'antd';
import { DownloadOutlined, HistoryOutlined, SearchOutlined, DatabaseOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Paragraph } = Typography;

const DownloadsPage = () => {
  const navigate = useNavigate();

  return (
    <div>
      <Title level={2}>Data Downloads</Title>
      
      <Alert
        message="How to Download Data"
        description="To download datasets, browse to specific studies or use the search interface to find datasets, then use the download buttons available on each dataset."
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
        <Col xs={24} md={8}>
          <Card 
            title="Search & Browse" 
            hoverable
            onClick={() => navigate('/search')}
            style={{ cursor: 'pointer', height: '100%' }}
          >
            <Space direction="vertical" style={{ width: '100%', textAlign: 'center' }}>
              <SearchOutlined style={{ fontSize: '32px', color: '#1890ff' }} />
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
              <DownloadOutlined style={{ fontSize: '32px', color: '#faad14' }} />
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

      <Card title={<><HistoryOutlined /> Download Formats</>} style={{ marginBottom: 24 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Card size="small">
              <div style={{ textAlign: 'center' }}>
                <Title level={4} style={{ color: '#1890ff', margin: '8px 0' }}>CSV</Title>
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
                <Title level={4} style={{ color: '#faad14', margin: '8px 0' }}>Excel</Title>
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

      <Card title={<><HistoryOutlined /> Recent Downloads</>}>
        <Empty 
          description="No download history available"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Button type="primary" onClick={() => navigate('/search')}>
            Start Downloading Data
          </Button>
        </Empty>
      </Card>
    </div>
  );
};

export default DownloadsPage;
