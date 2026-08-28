import React, { useState } from 'react';
import { Table, Card, Tag, Button, Space, Typography, Row, Col, Modal, message } from 'antd';
import { useQuery } from 'react-query';
import { EyeOutlined, TeamOutlined, CalendarOutlined, CopyOutlined, FileTextOutlined, LinkOutlined } from '@ant-design/icons';
import { getStudies, generateCitationBundle } from '../services/api';
import { useNavigate } from 'react-router-dom';

const { Title } = Typography;

const StudiesPage = () => {
  const navigate = useNavigate();
  const [citationStudy, setCitationStudy] = useState(null);

  // Fetch every page of studies (the table paginates client-side)
  const fetchAllStudies = async () => {
    const first = await getStudies({ page: 1, page_size: 100 });
    const all = [...(first.items || [])];
    for (let page = 2; page <= (first.pages || 1); page += 1) {
      const next = await getStudies({ page, page_size: 100 });
      all.push(...(next.items || []));
    }
    return { ...first, items: all };
  };

  const { data: studiesData, isLoading, error } = useQuery(
    'studies-all',
    fetchAllStudies,
    {
      retry: 3,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );

  const studies = studiesData?.items;

  const handleCopyCitation = async () => {
    if (!citationStudy) return;
    // Both entries: the study's, and the initiative's.
    const bibtex = generateCitationBundle(citationStudy);
    try {
      await navigator.clipboard.writeText(bibtex);
      message.success('Copied both citations — the study and the database');
    } catch (err) {
      message.error('Failed to copy citation to clipboard');
    }
  };

  const columns = [
    {
      title: 'Study Name',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 'bold', marginBottom: 4 }}>{text}</div>
          {record.description && (
            <div style={{ color: '#4a4a4a', fontSize: '13.5px' }}>
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
      width: 180,
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/studies/${record.id}`)}
          >
            View
          </Button>
          <Button
            size="small"
            icon={<FileTextOutlined />}
            onClick={() => setCitationStudy(record)}
          >
            Cite
          </Button>
          {record.doi && (
            <Button
              size="small"
              icon={<LinkOutlined />}
              onClick={() => window.open(`https://doi.org/${record.doi}`, '_blank')}
              title="Open the paper via its DOI"
            >
              Paper
            </Button>
          )}
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
              defaultPageSize: 20,
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

      <Modal
        title="BibTeX citations"
        width={720}
        open={!!citationStudy}
        onCancel={() => setCitationStudy(null)}
        footer={[
          <Button key="copy" type="primary" icon={<CopyOutlined />} onClick={handleCopyCitation}>
            Copy both
          </Button>,
          <Button key="close" onClick={() => setCitationStudy(null)}>
            Close
          </Button>,
        ]}
      >
        {citationStudy && (
          <>
          <p className="page-caption">
            Two entries: the study whose ratings you are using, and the
            initiative that collected them. Please cite both.
          </p>
          <pre
            style={{
              background: '#f5f5f5',
              padding: '16px',
              borderRadius: '4px',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {generateCitationBundle(citationStudy)}
          </pre>
          </>
        )}
      </Modal>
    </div>
  );
};

export default StudiesPage;
