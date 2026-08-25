import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Tag, Table, Button, Space, Typography, Row, Col, Alert, message } from 'antd';
import { useQuery } from 'react-query';
import {
  DownloadOutlined,
  ExperimentOutlined,
  CalendarOutlined,
  TeamOutlined,
  DatabaseOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import { getStudy, requestDownload, getDownload, downloadFile } from '../services/api';

const { Title } = Typography;

const StudyDetailPage = () => {
  const { studyId } = useParams();
  const navigate = useNavigate();
  const [downloadingDatasets, setDownloadingDatasets] = useState(new Set());
  const [downloadingAll, setDownloadingAll] = useState(false);
  
  const { data: study, isLoading, error: studyError } = useQuery(
    ['study', studyId],
    () => getStudy(studyId)
  );

  const handleDatasetDownload = async (dataset) => {
    try {
      setDownloadingDatasets(prev => new Set(prev).add(dataset.id));
      
      // Request download
      const downloadRequest = {
        dataset_ids: [dataset.id],
        format: 'csv'
      };
      
      const downloadInfo = await requestDownload(downloadRequest);
      
      // Get the file
      const response = await getDownload(downloadInfo.download_id);
      
      // Download the file
      const filename = `${dataset.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_data.csv`;
      downloadFile(response.data, filename);

    } catch (error) {
      console.error('Download failed:', error);
      message.error(`Download of ${dataset.name} failed. Please try again.`);
    } finally {
      setDownloadingDatasets(prev => {
        const newSet = new Set(prev);
        newSet.delete(dataset.id);
        return newSet;
      });
    }
  };

  const handleDownloadAllDatasets = async () => {
    try {
      setDownloadingAll(true);
      
      // Request download for all datasets in the study
      const downloadRequest = {
        dataset_ids: study.datasets.map(ds => ds.id),
        format: 'csv'
      };
      
      const downloadInfo = await requestDownload(downloadRequest);
      
      // Get the file
      const response = await getDownload(downloadInfo.download_id);
      
      // Multi-dataset CSV downloads arrive as a zip archive
      const multi = (study.datasets?.length || 0) > 1;
      const filename = `${study.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_all_datasets.${multi ? 'zip' : 'csv'}`;
      downloadFile(response.data, filename);

    } catch (error) {
      console.error('Download failed:', error);
      message.error('Download failed. Please try again.');
    } finally {
      setDownloadingAll(false);
    }
  };

  const datasetColumns = [
    {
      title: 'Dataset Name',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          {record.description && (
            <div style={{ color: '#4a4a4a', fontSize: '13.5px' }}>
              {record.description}
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Subjects',
      dataIndex: 'n_subjects',
      key: 'n_subjects',
      width: 100,
      render: (value) => (
        <div style={{ textAlign: 'center' }}>
          <TeamOutlined style={{ marginRight: 4 }} />
          {value}
        </div>
      ),
    },
    {
      title: 'Items',
      dataIndex: 'n_items',
      key: 'n_items',
      width: 100,
      render: (value) => (
        <div style={{ textAlign: 'center' }}>
          <DatabaseOutlined style={{ marginRight: 4 }} />
          {value}
        </div>
      ),
    },
    {
      title: 'Rating Scale',
      key: 'rating_scale',
      render: (_, record) => (
        <div>
          <div>{record.rating_scale_min} - {record.rating_scale_max}</div>
          {record.rating_scale_type && (
            <Tag size="small">{record.rating_scale_type}</Tag>
          )}
        </div>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button 
            size="small"
            onClick={() => navigate(`/datasets/${record.id}`)}
          >
            View
          </Button>
          <Button 
            size="small" 
            icon={<DownloadOutlined />}
            loading={downloadingDatasets.has(record.id)}
            onClick={() => handleDatasetDownload(record)}
          >
            Download
          </Button>
        </Space>
      ),
    },
  ];

  if (isLoading) {
    return <Card loading={true} />;
  }

  if (studyError) {
    const notFound = studyError?.response?.status === 404;
    return (
      <Alert
        type={notFound ? 'warning' : 'error'}
        showIcon
        message={notFound ? 'Study not found' : 'Error loading study'}
        description={notFound
          ? 'No study exists with this id — it may have been merged or the link is stale.'
          : 'The study could not be loaded. Please try again.'}
        action={<Button onClick={() => navigate('/studies')}>Back to Studies</Button>}
      />
    );
  }

  if (!study) {
    return <Card>Study not found</Card>;
  }

  return (
    <div>
      {/* Study Header */}
      <Card style={{ marginBottom: 24 }}>
        <Row align="middle">
          <Col flex="auto">
            <Space size="large">
              <ExperimentOutlined style={{ fontSize: '24px', color: '#085AB3' }} />
              <div>
                <Title level={2} style={{ margin: 0 }}>
                  {study.name}
                </Title>
                <Space size="middle">
                  <span>
                    <CalendarOutlined style={{ marginRight: 4 }} />
                    {study.year}
                  </span>
                  <span>
                    <DatabaseOutlined style={{ marginRight: 4 }} />
                    {study.datasets?.length || 0} datasets
                  </span>
                </Space>
              </div>
            </Space>
          </Col>
          <Col>
            <Space>
              {study.doi && (
                <Button
                  icon={<FileTextOutlined />}
                  onClick={() => window.open(`https://doi.org/${study.doi}`, '_blank')}
                >
                  View Paper
                </Button>
              )}
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                loading={downloadingAll}
                onClick={handleDownloadAllDatasets}
                disabled={!study.datasets || study.datasets.length === 0}
              >
                Download All Datasets
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Study Details */}
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <Card title="Study Information">
            <Descriptions column={1} bordered>
              <Descriptions.Item label="Study Name">
                {study.name}
              </Descriptions.Item>
              <Descriptions.Item label="Authors">
                <Space wrap>
                  {study.authors?.map((author, index) => (
                    <Tag key={index}>{author}</Tag>
                  ))}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Publication Year">
                {study.year}
              </Descriptions.Item>
              {study.journal && (
                <Descriptions.Item label="Journal">
                  {study.journal}
                </Descriptions.Item>
              )}
              {study.publication_title && (
                <Descriptions.Item label="Publication Title">
                  {study.publication_title}
                </Descriptions.Item>
              )}
              {study.doi && (
                <Descriptions.Item label="DOI">
                  <a href={`https://doi.org/${study.doi}`} target="_blank" rel="noopener noreferrer">
                    {study.doi}
                  </a>
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>
        </Col>
        
        <Col xs={24} lg={8}>
          <Card title="Quick Stats">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <div style={{ fontWeight: 'bold' }}>Total Datasets</div>
                <div style={{ fontSize: '24px', color: '#085AB3' }}>
                  {study.datasets?.length || 0}
                </div>
              </div>
              <div>
                <div style={{ fontWeight: 'bold' }}>Total Subjects</div>
                <div style={{ fontSize: '24px', color: '#52c41a' }}>
                  {study.datasets?.reduce((sum, ds) => sum + ds.n_subjects, 0) || 0}
                </div>
              </div>
              <div>
                <div style={{ fontWeight: 'bold' }}>Total Items</div>
                <div style={{ fontSize: '24px', color: '#E78A00' }}>
                  {study.datasets?.reduce((sum, ds) => sum + ds.n_items, 0) || 0}
                </div>
              </div>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Datasets Table */}
      <Card title="Datasets" style={{ marginTop: 24 }}>
        <Table
          columns={datasetColumns}
          dataSource={study.datasets}
          rowKey="id"
          pagination={false}
        />
      </Card>
    </div>
  );
};

export default StudyDetailPage;
