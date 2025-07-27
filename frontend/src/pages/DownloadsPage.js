import React from 'react';
import { Card, Typography, Button, Space, Empty } from 'antd';
import { DownloadOutlined, HistoryOutlined } from '@ant-design/icons';

const { Title } = Typography;

const DownloadsPage = () => {
  return (
    <div>
      <Title level={2}>Downloads</Title>
      
      <Card style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%', textAlign: 'center' }}>
          <DownloadOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />
          <Title level={4}>No Downloads Yet</Title>
          <p>
            You haven't requested any downloads yet. Use the search interface to find 
            datasets and request downloads in your preferred format.
          </p>
          <Button type="primary" href="/search">
            Start Browsing Data
          </Button>
        </Space>
      </Card>

      <Card title={<><HistoryOutlined /> Download History</>}>
        <Empty 
          description="No download history available"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    </div>
  );
};

export default DownloadsPage;
