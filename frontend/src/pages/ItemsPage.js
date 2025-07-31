import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Card, 
  Table, 
  Tag, 
  Input, 
  Select, 
  Button, 
  Space, 
  Typography, 
  Row, 
  Col,
  Statistic 
} from 'antd';
import { useQuery } from 'react-query';
import { SearchOutlined, AppleOutlined, TagOutlined } from '@ant-design/icons';
import { getItems, getCategories } from '../services/api';

const { Title } = Typography;
const { Option } = Select;
const { Search } = Input;

const ItemsPage = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [pagination, setPagination] = useState({ page: 1, pageSize: 20 });

  const { data: items, isLoading, error } = useQuery(
    ['items', searchTerm, selectedCategory, pagination],
    () => getItems({
      search: searchTerm,
      category: selectedCategory,
      page: pagination.page,
      page_size: pagination.pageSize
    }),
    {
      retry: 3,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );

  const { data: categories } = useQuery('categories', getCategories);

  const columns = [
    {
      title: 'Food Item',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          {record.standardized_name && record.standardized_name !== text && (
            <div style={{ color: '#666', fontSize: '12px' }}>
              Also known as: {record.standardized_name}
            </div>
          )}
          {record.aliases && record.aliases.length > 0 && (
            <div style={{ marginTop: 4 }}>
              {record.aliases.slice(0, 3).map((alias, index) => (
                <Tag key={index} size="small" style={{ marginRight: 4 }}>
                  {alias}
                </Tag>
              ))}
              {record.aliases.length > 3 && (
                <Tag size="small">+{record.aliases.length - 3} more</Tag>
              )}
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      width: 150,
      render: (category) => category ? (
        <Tag icon={<TagOutlined />} color="blue">
          {category}
        </Tag>
      ) : '-',
    },
    {
      title: 'Subcategory',
      dataIndex: 'subcategory',
      key: 'subcategory',
      width: 150,
      render: (subcategory) => subcategory ? (
        <Tag color="geekblue">{subcategory}</Tag>
      ) : '-',
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
          <div style={{ fontSize: '12px', color: '#666' }}>
            {frequency === 1 ? 'dataset' : 'datasets'}
          </div>
        </div>
      ),
    },
    {
      title: 'Image',
      dataIndex: 'image_available',
      key: 'image_available',
      width: 80,
      render: (hasImage) => (
        <Tag color={hasImage ? 'green' : 'default'}>
          {hasImage ? 'Yes' : 'No'}
        </Tag>
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
        <Col>
          <Space>
            <Button type="primary">
              Add Item
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Summary Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Total Items"
              value={items?.total || 0}
              prefix={<AppleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Categories"
              value={categories?.categories?.length || 0}
              prefix={<TagOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="With Images"
              value={items?.items?.filter(item => item.image_available).length || 0}
              valueStyle={{ color: '#faad14' }}
              suffix={`/ ${items?.items?.length || 0}`}
            />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16}>
          <Col xs={24} sm={12} md={8}>
            <Search
              placeholder="Search food items..."
              onSearch={setSearchTerm}
              allowClear
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Select
              placeholder="Filter by category"
              allowClear
              style={{ width: '100%' }}
              onChange={setSelectedCategory}
            >
              {categories?.categories?.map(category => (
                <Option key={category} value={category}>
                  {category}
                </Option>
              ))}
            </Select>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Space>
              <Button 
                onClick={() => {
                  setSearchTerm('');
                  setSelectedCategory(null);
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
