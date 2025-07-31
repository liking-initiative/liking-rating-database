import React from 'react';
import { Table, Card, Tag, Button, Space, Typography, Row, Col } from 'antd';
import { useQuery } from 'react-query';
import { EyeOutlined, TeamOutlined, CalendarOutlined } from '@ant-design/icons';
import { getStudies } from '../services/api';
import { useNavigate } from 'react-router-dom';

const { Title } = Typography;

const StudiesPage = () => {
  const navigate = useNavigate();
  
  const { data: studies, isLoading, error } = useQuery(
    'studies', 
    () => getStudies(),
    {
      retry: 3,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );

  const columns = [
    {
      title: 'Study Name',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 'bold', marginBottom: 4 }}>{text}</div>
          {record.description && (
            <div style={{ color: '#666', fontSize: '12px' }}>
              {record.description.length > 100 
                ? record.description.substring(0, 100) + '...' 
                : record.description
              }
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Authors',
      dataIndex: 'authors',
      key: 'authors',
      render: (authors) => (
        <div>
          {authors.slice(0, 3).map((author, index) => (
            <Tag key={index} style={{ marginBottom: 2 }}>
              {author}
            </Tag>
          ))}
          {authors.length > 3 && (
            <Tag>+{authors.length - 3} more</Tag>
          )}
        </div>
      ),
    },
    {
      title: 'Year',
      dataIndex: 'year',
      key: 'year',
      width: 100,
      render: (year) => (
        <div style={{ textAlign: 'center' }}>
          <CalendarOutlined style={{ marginRight: 4 }} />
          {year}
        </div>
      ),
    },
    {
      title: 'Journal',
      dataIndex: 'journal',
      key: 'journal',
      render: (journal) => journal || '-',
    },
    {
      title: 'Datasets',
      dataIndex: 'datasets',
      key: 'datasets',
      width: 100,
      render: (datasets) => (
        <div style={{ textAlign: 'center' }}>
          <TeamOutlined style={{ marginRight: 4 }} />
          {datasets?.length || 0}
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
            icon={<EyeOutlined />}
            onClick={() => navigate(`/studies/${record.id}`)}
          >
            View
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2}>Research Studies</Title>
        </Col>
        <Col>
          <Space>
            <Button type="primary">
              Add Study
            </Button>
          </Space>
        </Col>
      </Row>

      <Card>
        {error ? (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <p>Error loading studies: {error.message}</p>
            <Button onClick={() => window.location.reload()}>Retry</Button>
          </div>
        ) : (
          <Table
            columns={columns}
            dataSource={studies}
            rowKey="id"
            loading={isLoading}
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) => 
                `${range[0]}-${range[1]} of ${total} studies`,
            }}
            locale={{
              emptyText: isLoading ? 'Loading...' : 'No studies found'
            }}
          />
        )}
      </Card>
    </div>
  );
};

export default StudiesPage;
