import React from 'react';
import { Layout, Menu } from 'antd';
import { 
  SearchOutlined, 
  ExperimentOutlined, 
  AppleOutlined, 
  BarChartOutlined,
  InfoCircleOutlined 
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';

const { Sider } = Layout;

const AppSidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    {
      key: '/search',
      icon: <SearchOutlined />,
      label: 'Search & Browse',
      onClick: () => navigate('/search')
    },
    {
      key: '/studies',
      icon: <ExperimentOutlined />,
      label: 'Studies',
      onClick: () => navigate('/studies')
    },
    {
      key: '/items',
      icon: <AppleOutlined />,
      label: 'Food Items',
      onClick: () => navigate('/items')
    },
    {
      key: '/visualizations',
      icon: <BarChartOutlined />,
      label: 'Visualizations',
      onClick: () => navigate('/visualizations')
    },
    {
      key: '/about',
      icon: <InfoCircleOutlined />,
      label: 'About',
      onClick: () => navigate('/about')
    }
  ];

  // Get current selected key based on location
  const selectedKey = menuItems.find(item => location.pathname.startsWith(item.key))?.key || '/search';

  return (
    <Sider 
      width={240} 
      style={{ background: '#fff' }}
      breakpoint="lg"
      collapsedWidth="0"
    >
      <Menu
        mode="inline"
        selectedKeys={[selectedKey]}
        style={{ height: '100%', borderRight: 0 }}
        items={menuItems}
      />
    </Sider>
  );
};

export default AppSidebar;
