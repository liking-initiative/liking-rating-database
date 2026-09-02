import React from 'react';
import { Layout, Typography, Button, Space } from 'antd';
import { DownloadOutlined, GithubOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Header } = Layout;
const { Title } = Typography;

const AppHeader = () => {
  const navigate = useNavigate();

  return (
    <Header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px'
    }}>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <Title
          level={3}
          style={{
            color: 'white',
            margin: 0,
            cursor: 'pointer'
          }}
          onClick={() => navigate('/')}
        >
          The Liking Initiative
        </Title>
      </div>
      
      <Space>
        <Button 
          type="text" 
          icon={<DownloadOutlined />}
          style={{ color: 'rgba(255, 255, 255, 0.85)' }}
          onClick={() => navigate('/downloads')}
        >
          Downloads
        </Button>
        <Button 
          type="text" 
          icon={<GithubOutlined />}
          style={{ color: 'rgba(255, 255, 255, 0.85)' }}
          onClick={() => window.open('https://github.com/liking-initiative/liking-rating-database', '_blank')}
        >
          GitHub
        </Button>
      </Space>
    </Header>
  );
};

export default AppHeader;
