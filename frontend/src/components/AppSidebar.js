import React from 'react';
import { Layout, Menu } from 'antd';
import { 
  SearchOutlined, 
  ShareAltOutlined,
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
      label: 'Items',
      onClick: () => navigate('/items')
    },
    {
      key: '/network',
      icon: <ShareAltOutlined />,
      label: 'Item Network',
      onClick: () => navigate('/network')
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

  // Highlight the section the current path belongs to; datasets live under
  // studies, and pages without a sidebar entry (home, downloads) select nothing
  const path = location.pathname;
  let selectedKey = menuItems.find(item => path.startsWith(item.key))?.key;
  if (!selectedKey && path.startsWith('/datasets')) selectedKey = '/studies';

  return (
    <Sider
      width={240}
      style={{ background: '#fff' }}
      breakpoint="lg"
      collapsedWidth="0"
    >
      <Menu
        mode="inline"
        selectedKeys={selectedKey ? [selectedKey] : []}
        style={{ height: '100%', borderRight: 0 }}
        items={menuItems}
      />
    </Sider>
  );
};

export default AppSidebar;
