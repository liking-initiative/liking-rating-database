import React from 'react';
import { Card, Typography, Space, Button, Divider } from 'antd';

const { Title, Paragraph } = Typography;

const AboutPage = () => {
  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      <Title level={1}>About the Liking Rating Database</Title>
      
      <Card style={{ marginBottom: 24 }}>
        <Title level={2}>Overview</Title>
        <Paragraph>
          The Liking Rating Database is a comprehensive collection of food preference data 
          from multiple research studies. This database contains over 700,000 individual 
          ratings from 30+ research studies, providing researchers with standardized access 
          to food liking data for analysis and comparison.
        </Paragraph>
        
        <Paragraph>
          All data has been standardized to enable cross-study comparisons, with ratings 
          normalized to a 0-1 scale and consistent food item categorization.
        </Paragraph>
      </Card>

      <Card style={{ marginBottom: 24 }}>
        <Title level={2}>Features</Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Title level={4}>Advanced Search & Filtering</Title>
            <Paragraph>
              Search datasets by study characteristics, food categories, rating scales, 
              number of subjects, and more. Our flexible filtering system helps you find 
              exactly the data you need.
            </Paragraph>
          </div>
          
          <div>
            <Title level={4}>Multiple Export Formats</Title>
            <Paragraph>
              Download data in CSV, Excel, JSON, or SPSS formats. All exports include 
              comprehensive metadata and documentation to ensure proper data usage.
            </Paragraph>
          </div>
          
          <div>
            <Title level={4}>Interactive Visualizations</Title>
            <Paragraph>
              Explore rating distributions, cross-study comparisons, and food preference 
              patterns through interactive charts and visualizations.
            </Paragraph>
          </div>
          
          <div>
            <Title level={4}>Open Science Framework Integration</Title>
            <Paragraph>
              All data is stored and versioned through the Open Science Framework (OSF), 
              ensuring transparency, reproducibility, and long-term accessibility.
            </Paragraph>
          </div>
        </Space>
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
          [Citation format will be provided upon publication]
        </div>
        <Button type="primary">
          Generate Citation
        </Button>
      </Card>

      <Card>
        <Title level={2}>Contact & Support</Title>
        <Paragraph>
          For questions about the database, data requests, or technical support, 
          please contact us at:
        </Paragraph>
        <Space direction="vertical">
          <div>Email: support@likingdatabase.org</div>
          <div>GitHub: <a href="https://github.com/your-repo/liking-rating-database">
            Project Repository
          </a></div>
        </Space>
      </Card>
    </div>
  );
};

export default AboutPage;
