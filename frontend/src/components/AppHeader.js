import React from 'react';
import { Layout, Menu, Typography, Button, Space } from 'antd';
import { HomeOutlined, DownloadOutlined, GithubOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Header } = Layout;
const { Title } = Typography;

const AppHeader = () => {
  const navigate = useNavigate();

  const menuItems = [
    {
      key: 'home',
      icon: <HomeOutlined />,
      label: 'Home',
      onClick: () => navigate('/')
    }
  ];

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
            marginRight: '24px',
            cursor: 'pointer'
          }}
          onClick={() => navigate('/')}
        >
          Liking Rating Database
        </Title>
        <Menu
          theme="dark"
          mode="horizontal"
          items={menuItems}
          style={{ 
            flex: 1, 
            minWidth: 0,
            backgroundColor: 'transparent',
            border: 'none'
          }}
        />
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
          onClick={() => window.open('https://github.com/yourusername/liking-rating-database', '_blank')}
        >
          GitHub
        </Button>
      </Space>
    </Header>
  );
};

export default AppHeader;
