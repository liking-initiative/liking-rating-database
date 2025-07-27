import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Layout } from 'antd';
import AppHeader from './components/AppHeader';
import AppSidebar from './components/AppSidebar';
import HomePage from './pages/HomePage';
import SearchPage from './pages/SearchPage';
import StudiesPage from './pages/StudiesPage';
import StudyDetailPage from './pages/StudyDetailPage';
import DatasetDetailPage from './pages/DatasetDetailPage';
import ItemsPage from './pages/ItemsPage';
import VisualizationsPage from './pages/VisualizationsPage';
import DownloadsPage from './pages/DownloadsPage';
import AboutPage from './pages/AboutPage';

const { Content } = Layout;

function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <AppHeader />
      <Layout>
        <AppSidebar />
        <Layout style={{ padding: '24px' }}>
          <Content
            style={{
              padding: '24px',
              margin: 0,
              minHeight: 280,
              background: '#fff',
              borderRadius: '8px',
            }}
          >
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/studies" element={<StudiesPage />} />
              <Route path="/studies/:studyId" element={<StudyDetailPage />} />
              <Route path="/datasets/:datasetId" element={<DatasetDetailPage />} />
              <Route path="/items" element={<ItemsPage />} />
              <Route path="/visualizations" element={<VisualizationsPage />} />
              <Route path="/downloads" element={<DownloadsPage />} />
              <Route path="/about" element={<AboutPage />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
}

export default App;
