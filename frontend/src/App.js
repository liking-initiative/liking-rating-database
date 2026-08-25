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
import DatasetVisualizationPage from './pages/DatasetVisualizationPage';
import ItemsPage from './pages/ItemsPage';
import ItemDetailPage from './pages/ItemDetailPage';
import ItemAnalysisPage from './pages/ItemAnalysisPage';
import VisualizationsPage from './pages/VisualizationsPage';
import NetworkPage from './pages/NetworkPage';
import DescriptivesPage from './pages/DescriptivesPage';
import DocumentationPage from './pages/DocumentationPage';
import DownloadsPage from './pages/DownloadsPage';
import AboutPage from './pages/AboutPage';
import NotFoundPage from './pages/NotFoundPage';

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
              <Route path="/datasets/:datasetId/visualize" element={<DatasetVisualizationPage />} />
              <Route path="/items" element={<ItemsPage />} />
              <Route path="/items/:itemId" element={<ItemDetailPage />} />
              <Route path="/items/:itemId/analyze" element={<ItemAnalysisPage />} />
              <Route path="/visualizations" element={<VisualizationsPage />} />
              <Route path="/network" element={<NetworkPage />} />
              <Route path="/descriptives" element={<DescriptivesPage />} />
              <Route path="/docs" element={<DocumentationPage />} />
              <Route path="/downloads" element={<DownloadsPage />} />
              <Route path="/about" element={<AboutPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
}

export default App;
