import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Card, 
  Table, 
  Input, 
  Button, 
  Space, 
  Typography, 
  Row, 
  Col,
  Statistic 
} from 'antd';
import { useQuery } from 'react-query';
import { AppleOutlined } from '@ant-design/icons';
import { getItems } from '../services/api';

const { Title } = Typography;
const { Search } = Input;

const ItemsPage = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [pagination, setPagination] = useState({ page: 1, pageSize: 20 });

  // A new search always restarts from page 1
  const applySearch = (value) => {
    setSearchTerm(value);
    setPagination((p) => ({ ...p, page: 1 }));
  };

  const { data: items, isLoading } = useQuery(
    ['items', searchTerm, pagination],
    () => getItems({
      search: searchTerm,
      page: pagination.page,
      page_size: pagination.pageSize
    }),
    {
      retry: 3,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );


  const columns = [
    {
      title: 'Food Item',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          {record.standardized_name && record.standardized_name !== text && (
            <div style={{ color: '#4a4a4a', fontSize: '13.5px' }}>
              Also known as: {record.standardized_name}
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Frequency',
      dataIndex: 'frequency',
      key: 'frequency',
      width: 100,
      sorter: (a, b) => a.frequency - b.frequency,
      render: (frequency) => (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontWeight: 'bold' }}>{frequency}</div>
          <div style={{ fontSize: '13.5px', color: '#4a4a4a' }}>
            {frequency === 1 ? 'dataset' : 'datasets'}
          </div>
        </div>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button 
            size="small"
            onClick={() => navigate(`/items/${record.id}`)}
          >
            View
          </Button>
          <Button 
            size="small"
            onClick={() => navigate(`/items/${record.id}/analyze`)}
          >
            Analyze
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2}>Food Items</Title>
        </Col>
      </Row>

      {/* Summary Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24}>
          <Card>
            <Statistic
              title="Total Items"
              value={items?.total || 0}
              prefix={<AppleOutlined />}
              valueStyle={{ color: '#085AB3' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16}>
          <Col xs={24} sm={12} md={8}>
            <Search
              placeholder="Search items..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onSearch={applySearch}
              allowClear
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Space>
              <Button
                onClick={() => {
                  setSearchInput('');
                  applySearch('');
                }}
              >
                Clear Filters
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Items Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={items?.items}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: pagination.page,
            pageSize: pagination.pageSize,
            total: items?.total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => 
              `${range[0]}-${range[1]} of ${total} items`,
            onChange: (page, pageSize) => {
              setPagination({ page, pageSize });
            },
          }}
        />
      </Card>
    </div>
  );
};

export default ItemsPage;
