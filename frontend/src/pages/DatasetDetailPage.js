import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Tag, Button, Space, Typography, Row, Col, Table, message, Modal, Select } from 'antd';
import { useQuery } from 'react-query';
import {
  DownloadOutlined,
  DatabaseOutlined,
  TeamOutlined,
  AppleOutlined,
  BarChartOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import { getDataset, getRatingAggregations, requestDownload, getDownload, downloadFile } from '../services/api';

const { Title, Paragraph } = Typography;
const { Option } = Select;

const DatasetDetailPage = () => {
  const { datasetId } = useParams();
  const navigate = useNavigate();
  const [downloadModalVisible, setDownloadModalVisible] = useState(false);
  const [downloadFormat, setDownloadFormat] = useState('csv');
  const [downloading, setDownloading] = useState(false);
  
  const { data: dataset, isLoading } = useQuery(
    ['dataset', datasetId], 
    () => getDataset(datasetId)
  );

  const { data: ratingStats } = useQuery(
    ['ratingAggregations', datasetId],
    () => getRatingAggregations({ dataset_ids: [datasetId], min_ratings: 1 }),
    { enabled: !!datasetId }
  );

  const handleDownload = async () => {
    try {
      setDownloading(true);
      
      // Request download
      const downloadResponse = await requestDownload({
        dataset_ids: [datasetId],
        format: downloadFormat,
        include_metadata: true,
        include_demographics: false
      });

      message.success('Download request initiated. Preparing file...');
      
      // Wait a moment for file preparation, then download
      setTimeout(async () => {
        try {
          const fileResponse = await getDownload(downloadResponse.download_id);
          const filename = `${dataset.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_dataset.${downloadFormat}`;
          downloadFile(fileResponse.data, filename);
          message.success('Download completed!');
        } catch (error) {
          console.error('Download error:', error);
          message.error('Failed to download file. Please try again.');
        } finally {
          setDownloading(false);
          setDownloadModalVisible(false);
        }
      }, 2000);
      
    } catch (error) {
      console.error('Download request error:', error);
      message.error('Failed to initiate download. Please try again.');
      setDownloading(false);
    }
  };

  const statsColumns = [
    {
      title: 'Food Item',
      dataIndex: 'item_name',
      key: 'item_name',
    },
    {
      title: 'Mean Rating',
      dataIndex: 'mean_rating',
      key: 'mean_rating',
      render: (value) => value?.toFixed(3),
      sorter: (a, b) => a.mean_rating - b.mean_rating,
    },
    {
      title: 'Std Dev',
      dataIndex: 'std_rating',
      key: 'std_rating',
      render: (value) => value?.toFixed(3),
    },
    {
      title: 'Median',
      dataIndex: 'median_rating',
      key: 'median_rating',
      render: (value) => value?.toFixed(3),
    },
    {
      title: '# Ratings',
      dataIndex: 'n_ratings',
      key: 'n_ratings',
      sorter: (a, b) => a.n_ratings - b.n_ratings,
    },
  ];

  if (isLoading) {
    return <Card loading={true} />;
  }

  if (!dataset) {
    return <Card>Dataset not found</Card>;
  }

  return (
    <div>
      {/* Dataset Header */}
      <Card style={{ marginBottom: 24 }}>
        <Row align="middle">
          <Col flex="auto">
            <Space size="large">
              <DatabaseOutlined style={{ fontSize: '24px', color: '#52c41a' }} />
              <div>
                <Title level={2} style={{ margin: 0 }}>
                  {dataset.name}
                </Title>
                <div style={{ color: '#666' }}>
                  From study: <strong>{dataset.study?.name}</strong>
                </div>
              </div>
            </Space>
          </Col>
          <Col>
            <Space>
              {dataset.study?.doi && (
                <Button
                  icon={<FileTextOutlined />}
                  onClick={() => window.open(`https://doi.org/${dataset.study.doi}`, '_blank')}
                >
                  View Paper
                </Button>
              )}
              <Button
                icon={<BarChartOutlined />}
                onClick={() => navigate(`/datasets/${datasetId}/visualize`)}
              >
                Visualize
              </Button>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                onClick={() => setDownloadModalVisible(true)}
                loading={downloading}
              >
                Download Dataset
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Row gutter={[24, 24]}>
        {/* Dataset Details */}
        <Col xs={24} lg={16}>
          <Card title="Dataset Information">
            <Descriptions column={1} bordered>
              <Descriptions.Item label="Dataset Name">
                {dataset.name}
              </Descriptions.Item>
              <Descriptions.Item label="Study">
                {dataset.study?.name}
              </Descriptions.Item>
              <Descriptions.Item label="Authors">
                <Space wrap>
                  {dataset.study?.authors?.map((author, index) => (
                    <Tag key={index}>{author}</Tag>
                  ))}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Publication Year">
                {dataset.study?.year}
              </Descriptions.Item>
              <Descriptions.Item label="Number of Subjects">
                <Space>
                  <TeamOutlined />
                  {dataset.n_subjects}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Number of Items">
                <Space>
                  <AppleOutlined />
                  {dataset.n_items}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Rating Scale">
                <div>
                  <div>Range: {dataset.rating_scale_min} - {dataset.rating_scale_max}</div>
                  {dataset.rating_scale_type && (
                    <Tag style={{ marginTop: 4 }}>{dataset.rating_scale_type}</Tag>
                  )}
                </div>
              </Descriptions.Item>
              <Descriptions.Item label="Data Completeness">
                {dataset.data_completeness ? `${dataset.data_completeness.toFixed(1)}%` : 'Not specified'}
              </Descriptions.Item>
              {dataset.description && (
                <Descriptions.Item label="Description">
                  <Paragraph>{dataset.description}</Paragraph>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="File Format">
                {dataset.file_format || 'Not specified'}
              </Descriptions.Item>
              {dataset.file_size_mb && (
                <Descriptions.Item label="File Size">
                  {dataset.file_size_mb.toFixed(2)} MB
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>
        </Col>
        
        {/* Quick Stats */}
        <Col xs={24} lg={8}>
          <Card title="Quick Statistics">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <div style={{ fontWeight: 'bold' }}>Subjects</div>
                <div style={{ fontSize: '24px', color: '#1890ff' }}>
                  <TeamOutlined style={{ marginRight: 8 }} />
                  {dataset.n_subjects}
                </div>
              </div>
              <div>
                <div style={{ fontWeight: 'bold' }}>Food Items</div>
                <div style={{ fontSize: '24px', color: '#52c41a' }}>
                  <AppleOutlined style={{ marginRight: 8 }} />
                  {dataset.n_items}
                </div>
              </div>
              <div>
                <div style={{ fontWeight: 'bold' }}>Total Ratings</div>
                <div style={{ fontSize: '24px', color: '#faad14' }}>
                  {(dataset.n_subjects * dataset.n_items).toLocaleString()}
                </div>
              </div>
              {dataset.data_completeness && (
                <div>
                  <div style={{ fontWeight: 'bold' }}>Completeness</div>
                  <div style={{ fontSize: '24px', color: dataset.data_completeness > 90 ? '#52c41a' : '#faad14' }}>
                    {dataset.data_completeness.toFixed(1)}%
                  </div>
                </div>
              )}
            </Space>
          </Card>

          {/* Study Info Card */}
          <Card title="Study Details" style={{ marginTop: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <div style={{ fontWeight: 'bold' }}>Study Name</div>
                <div>{dataset.study?.name}</div>
              </div>
              <div>
                <div style={{ fontWeight: 'bold' }}>Year</div>
                <div>{dataset.study?.year}</div>
              </div>
              {dataset.study?.journal && (
                <div>
                  <div style={{ fontWeight: 'bold' }}>Journal</div>
                  <div>{dataset.study?.journal}</div>
                </div>
              )}
              {dataset.study?.doi && (
                <div>
                  <div style={{ fontWeight: 'bold' }}>DOI</div>
                  <a href={`https://doi.org/${dataset.study.doi}`} target="_blank" rel="noopener noreferrer">
                    {dataset.study.doi}
                  </a>
                </div>
              )}
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Rating Statistics */}
      {ratingStats && ratingStats.length > 0 && (
        <Card title="Rating Statistics by Item" style={{ marginTop: 24 }}>
          <Table
            columns={statsColumns}
            dataSource={ratingStats}
            rowKey="item_id"
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
            }}
            scroll={{ x: 600 }}
          />
        </Card>
      )}

      {/* Download Modal */}
      <Modal
        title="Download Dataset"
        open={downloadModalVisible}
        onOk={handleDownload}
        onCancel={() => setDownloadModalVisible(false)}
        confirmLoading={downloading}
        okText="Download"
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <strong>Dataset:</strong> {dataset?.name}
          </div>
          <div>
            <strong>Study:</strong> {dataset?.study?.name}
          </div>
          <div>
            <strong>Format:</strong>
            <Select
              value={downloadFormat}
              onChange={setDownloadFormat}
              style={{ width: 120, marginLeft: 8 }}
            >
              <Option value="csv">CSV</Option>
              <Option value="json">JSON</Option>
              <Option value="xlsx">Excel</Option>
              <Option value="spss">SPSS</Option>
            </Select>
          </div>
          <div style={{ color: '#666', fontSize: '12px' }}>
            This will download the complete dataset including ratings, subject IDs, and item information.
          </div>
        </Space>
      </Modal>
    </div>
  );
};

export default DatasetDetailPage;
