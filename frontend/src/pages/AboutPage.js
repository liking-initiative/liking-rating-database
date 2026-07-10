import React from 'react';
import { Card, Typography, Space } from 'antd';
import { useQuery } from 'react-query';
import { getStatistics } from '../services/api';

const { Title, Paragraph } = Typography;

const AboutPage = () => {
  const { data: stats } = useQuery('statistics', getStatistics);

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      <Title level={1}>About the Liking Rating Database</Title>

      <Card style={{ marginBottom: 24 }}>
        <Title level={2}>Overview</Title>
        <Paragraph>
          The Liking Rating Database is a curated collection of subjective liking
          ratings — food items and consumer products — from published
          decision-making studies. It currently contains
          {' '}{(stats?.total_ratings || 588602).toLocaleString()} individual ratings
          from {stats?.total_studies || 24} published studies
          ({stats?.total_datasets || 42} datasets), providing researchers with
          standardized access to preference data.
        </Paragraph>

        <Paragraph>
          All data has been standardized to enable cross-study comparisons, with ratings
          normalized to a 0-1 scale and consistent item categorization.
        </Paragraph>
      </Card>

      <Card style={{ marginBottom: 24 }}>
        <Title level={2}>Data Standards</Title>
        <Paragraph>
          <strong>Rating Normalization:</strong> All ratings are normalized to a 0-1 scale 
          to enable cross-study comparisons, regardless of the original scale used.
        </Paragraph>
        <Paragraph>
          <strong>Food Item Standardization:</strong> Food items are categorized and 
          standardized using a consistent naming convention to facilitate data aggregation.
        </Paragraph>
        <Paragraph>
          <strong>Metadata Completeness:</strong> Each dataset includes comprehensive 
          metadata about the study design, participants, and methodology.
        </Paragraph>
      </Card>

      <Card style={{ marginBottom: 24 }}>
        <Title level={2}>Citation</Title>
        <Paragraph>
          If you use this database in your research, please cite:
        </Paragraph>
        <div style={{
          background: '#f5f5f5',
          padding: '16px',
          borderRadius: '4px',
          fontFamily: 'monospace',
          marginBottom: '16px'
        }}>
          Fernandez, K., Goyal, S., &amp; Krajbich, I. A database of subjective
          evaluation ratings for decision-making research. (In preparation.)
        </div>
        <Paragraph type="secondary">
          Please also cite the original studies whose data you use — each study
          page provides its citation, DOI, and a BibTeX generator.
        </Paragraph>
      </Card>

      <Card>
        <Title level={2}>Contact & Support</Title>
        <Paragraph>
          For questions about the database, data requests, or technical support, 
          please contact us at:
        </Paragraph>
        <Space direction="vertical">
          <div>Email: support@likingdatabase.org</div>
          <div>GitHub: <a href="https://github.com/kiante-fernandez/liking-rating-database">
            Project Repository
          </a></div>
        </Space>
      </Card>
    </div>
  );
};

export default AboutPage;
