import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Card, 
  Input, 
  Form, 
  Row, 
  Col, 
  Button, 
  Table, 
  Tag, 
  Space, 
  Pagination,
  Collapse,
  Select,
  Slider,
  Typography,
  Modal,
  message,
  Spin
} from 'antd';
import { SearchOutlined, FilterOutlined, DownloadOutlined, FileTextOutlined } from '@ant-design/icons';
import { useQuery } from 'react-query';
import { searchDatasets, getCategories, getScaleTypes, getYearRange, requestDownload, getDownload, downloadFile } from '../services/api';

const { Panel } = Collapse;
const { Title } = Typography;
const { Option } = Select;

const SearchPage = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState({});
  const [pagination, setPagination] = useState({ page: 1, pageSize: 20 });
  const [selectedDatasets, setSelectedDatasets] = useState([]);
  const [downloadModalVisible, setDownloadModalVisible] = useState(false);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [downloadFormat, setDownloadFormat] = useState('csv');
  const [includeMetadata, setIncludeMetadata] = useState(true);
  const [includeDemographics, setIncludeDemographics] = useState(false);

  // Metadata queries
  const { data: categories } = useQuery('categories', getCategories);
  const { data: scaleTypes } = useQuery('scaleTypes', getScaleTypes);
  const { data: yearRange } = useQuery('yearRange', getYearRange);

  // Search query
  const { data: searchResults, isLoading, refetch } = useQuery(
    ['search', searchQuery, filters, pagination],
    () => searchDatasets({
      query: searchQuery,
      filters,
      page: pagination.page,
      page_size: pagination.pageSize
    }),
    { 
      enabled: searchQuery.length > 0 || Object.keys(filters).length > 0,
      refetchOnWindowFocus: false
    }
  );

  const handleSearch = (values) => {
    setSearchQuery(values.query || '');
    setFilters(values);
    setPagination({ ...pagination, page: 1 });
    refetch();
  };

  const handleDownloadSingle = async (datasetId) => {
    try {
      setDownloadLoading(true);
      message.loading('Preparing download...', 0);
      
      const downloadRequest = {
        dataset_ids: [datasetId],
        format: 'csv',
        include_metadata: true,
        include_demographics: false
      };
      
      const response = await requestDownload(downloadRequest);
      
      // Get the file
      const fileResponse = await getDownload(response.download_id);
      
      // Extract filename from response headers or use default
      const contentDisposition = fileResponse.headers['content-disposition'];
      let filename = 'dataset.csv';
      if (contentDisposition) {
        const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
        if (matches != null && matches[1]) {
          filename = matches[1].replace(/['"]/g, '');
        }
      }
      
      downloadFile(fileResponse.data, filename);
      message.destroy();
      message.success('Download completed!');
    } catch (error) {
      message.destroy();
      console.error('Download error:', error);
      message.error('Failed to initiate download. Please try again.');
    } finally {
      setDownloadLoading(false);
    }
  };

  const handleDownloadSelected = () => {
    if (selectedDatasets.length === 0) {
      message.warning('Please select at least one dataset to download.');
      return;
    }
    setDownloadModalVisible(true);
  };

  const handleDownloadConfirm = async () => {
    try {
      setDownloadLoading(true);
      message.loading('Preparing download...', 0);
      
      const downloadRequest = {
        dataset_ids: selectedDatasets,
        format: downloadFormat,
        include_metadata: includeMetadata,
        include_demographics: includeDemographics
      };
      
      const response = await requestDownload(downloadRequest);
      
      // Get the file
      const fileResponse = await getDownload(response.download_id);
      
      // Extract filename from response headers or use default
      const contentDisposition = fileResponse.headers['content-disposition'];
      let filename = `datasets.${downloadFormat}`;
      if (contentDisposition) {
        const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
        if (matches != null && matches[1]) {
          filename = matches[1].replace(/['"]/g, '');
        }
      }
      
      downloadFile(fileResponse.data, filename);
      
      message.destroy();
      message.success('Download completed!');
      setDownloadModalVisible(false);
      setSelectedDatasets([]);
    } catch (error) {
      message.destroy();
      console.error('Download error:', error);
      message.error('Failed to initiate download. Please try again.');
    } finally {
      setDownloadLoading(false);
    }
  };

  const columns = [
    {
      title: 'Dataset',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          <div style={{ color: '#666', fontSize: '12px' }}>
            {record.study?.name}
          </div>
        </div>
      ),
    },
    {
      title: 'Authors',
      dataIndex: ['study', 'authors'],
      key: 'authors',
      render: (authors, record) => {
        const authorList = record.study?.authors;
        if (!authorList || !Array.isArray(authorList) || authorList.length === 0) {
          return '-';
        }
        return authorList.slice(0, 2).join(', ') + (authorList.length > 2 ? ' et al.' : '');
      },
    },
    {
      title: 'Year',
      dataIndex: ['study', 'year'],
      key: 'year',
      width: 80,
    },
    {
      title: 'Subjects',
      dataIndex: 'n_subjects',
      key: 'n_subjects',
      width: 100,
    },
    {
      title: 'Items',
      dataIndex: 'n_items',
      key: 'n_items',
      width: 100,
    },
    {
      title: 'Scale Type',
      dataIndex: 'rating_scale_type',
      key: 'rating_scale_type',
      render: (type) => type ? <Tag>{type}</Tag> : '-',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            onClick={() => navigate(`/datasets/${record.id}`)}
          >
            View
          </Button>
          {record.study?.doi && (
            <Button
              size="small"
              icon={<FileTextOutlined />}
              onClick={() => window.open(`https://doi.org/${record.study.doi}`, '_blank')}
              title="View Paper"
            >
              Paper
            </Button>
          )}
          <Button
            size="small"
            icon={<DownloadOutlined />}
            loading={downloadLoading}
            onClick={() => handleDownloadSingle(record.id)}
          >
            Download
          </Button>
        </Space>
      ),
    },
  ];

  const rowSelection = {
    selectedRowKeys: selectedDatasets,
    onChange: setSelectedDatasets,
  };

  return (
    <div>
      <Title level={2}>Search Datasets</Title>
      
      {/* Search Form */}
      <Card style={{ marginBottom: 24 }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSearch}
        >
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item name="query" label="Search Query">
                <Input
                  placeholder="Search studies, authors, food items..."
                  size="large"
                  suffix={<SearchOutlined />}
                />
              </Form.Item>
            </Col>
          </Row>
          
          <Collapse ghost>
            <Panel header="Advanced Filters" key="filters" extra={<FilterOutlined />}>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item name="study_name" label="Study Name">
                    <Input placeholder="Filter by study name" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="rating_scale_type" label="Rating Scale">
                    <Select placeholder="Select scale type" allowClear>
                      {scaleTypes?.scale_types?.map(type => (
                        <Option key={type} value={type}>{type}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="food_category" label="Food Category">
                    <Select placeholder="Select category" allowClear>
                      {categories?.categories?.map(category => (
                        <Option key={category} value={category}>{category}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
              
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="year_range" label="Year Range">
                    <Slider
                      range
                      min={yearRange?.min_year || 2000}
                      max={yearRange?.max_year || 2024}
                      defaultValue={[yearRange?.min_year || 2000, yearRange?.max_year || 2024]}
                    />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item name="n_subjects_min" label="Min Subjects">
                    <Input type="number" placeholder="0" />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item name="n_subjects_max" label="Max Subjects">
                    <Input type="number" placeholder="1000" />
                  </Form.Item>
                </Col>
              </Row>
            </Panel>
          </Collapse>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={isLoading}>
                Search
              </Button>
              <Button onClick={() => form.resetFields()}>
                Clear
              </Button>
              {selectedDatasets.length > 0 && (
                <Button 
                  type="primary" 
                  icon={<DownloadOutlined />}
                  loading={downloadLoading}
                  onClick={handleDownloadSelected}
                >
                  Download Selected ({selectedDatasets.length})
                </Button>
              )}
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {/* Results */}
      {searchResults && (
        <Card>
          <div style={{ marginBottom: 16 }}>
            <Title level={4}>
              {searchResults.total} datasets found
            </Title>
          </div>
          
          <Table
            columns={columns}
            dataSource={searchResults.results}
            rowKey="id"
            rowSelection={rowSelection}
            loading={isLoading}
            pagination={false}
          />
          
          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <Pagination
              current={pagination.page}
              pageSize={pagination.pageSize}
              total={searchResults.total}
              showSizeChanger
              showQuickJumper
              showTotal={(total, range) => 
                `${range[0]}-${range[1]} of ${total} items`
              }
              onChange={(page, pageSize) => {
                setPagination({ page, pageSize });
                refetch();
              }}
            />
          </div>
        </Card>
      )}
      
      {/* Download Modal */}
      <Modal
        title="Download Options"
        open={downloadModalVisible}
        onOk={handleDownloadConfirm}
        onCancel={() => setDownloadModalVisible(false)}
        confirmLoading={downloadLoading}
        okText="Download"
        cancelText="Cancel"
      >
        <Form layout="vertical">
          <Form.Item label="Format">
            <Select 
              value={downloadFormat} 
              onChange={setDownloadFormat}
              style={{ width: '100%' }}
            >
              <Select.Option value="csv">CSV</Select.Option>
              <Select.Option value="json">JSON</Select.Option>
              <Select.Option value="xlsx">Excel (XLSX)</Select.Option>
              <Select.Option value="spss">SPSS (SAV)</Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item>
            <Space direction="vertical">
              <label>
                <input
                  type="checkbox"
                  checked={includeMetadata}
                  onChange={(e) => setIncludeMetadata(e.target.checked)}
                />
                {' '}Include study metadata
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={includeDemographics}
                  onChange={(e) => setIncludeDemographics(e.target.checked)}
                />
                {' '}Include demographic data
              </label>
            </Space>
          </Form.Item>
          
          <p style={{ color: '#666', fontSize: '14px' }}>
            Downloading {selectedDatasets.length} dataset(s) in {downloadFormat.toUpperCase()} format.
          </p>
        </Form>
      </Modal>
    </div>
  );
};

export default SearchPage;
