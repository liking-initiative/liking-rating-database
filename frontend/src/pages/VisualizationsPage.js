import React from 'react';
import { Card, Typography, Row, Col, Empty } from 'antd';
import { BarChartOutlined } from '@ant-design/icons';

const { Title } = Typography;

const VisualizationsPage = () => {
  return (
    <div>
      <Title level={2}>Data Visualizations</Title>
      
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={12}>
          <Card title="Rating Distributions" style={{ height: 400 }}>
            <Empty 
              description="Visualization coming soon"
              image={<BarChartOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />}
            />
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="Cross-Study Comparisons" style={{ height: 400 }}>
            <Empty 
              description="Visualization coming soon"
              image={<BarChartOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />}
            />
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="Food Category Analysis" style={{ height: 400 }}>
            <Empty 
              description="Visualization coming soon"
              image={<BarChartOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />}
            />
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="Temporal Trends" style={{ height: 400 }}>
            <Empty 
              description="Visualization coming soon"
              image={<BarChartOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default VisualizationsPage;
