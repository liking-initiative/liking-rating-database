import React, { Suspense, lazy } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Layout, Spin } from 'antd';
import AppHeader from './components/AppHeader';
import AppSidebar from './components/AppSidebar';
import HomePage from './pages/HomePage';

// Every page except the landing one is split into its own chunk. Plotly is
// ~4 MB of the bundle and only three pages plot anything, so without this a
// visitor reading the documentation still downloads a charting library. The
// home page stays eager: splitting the first thing rendered only adds a
// spinner to the initial paint.
const SearchPage = lazy(() => import('./pages/SearchPage'));
const StudiesPage = lazy(() => import('./pages/StudiesPage'));
const StudyDetailPage = lazy(() => import('./pages/StudyDetailPage'));
const DatasetDetailPage = lazy(() => import('./pages/DatasetDetailPage'));
const DatasetVisualizationPage = lazy(() => import('./pages/DatasetVisualizationPage'));
const ItemsPage = lazy(() => import('./pages/ItemsPage'));
const ItemDetailPage = lazy(() => import('./pages/ItemDetailPage'));
const ItemAnalysisPage = lazy(() => import('./pages/ItemAnalysisPage'));
const NetworkPage = lazy(() => import('./pages/NetworkPage'));
const DescriptivesPage = lazy(() => import('./pages/DescriptivesPage'));
const DocumentationPage = lazy(() => import('./pages/DocumentationPage'));
const DownloadsPage = lazy(() => import('./pages/DownloadsPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));

const { Content } = Layout;

const PageFallback = () => (
  <div style={{ display: 'grid', placeItems: 'center', minHeight: 320 }}>
    <Spin size="large" />
  </div>
);

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
            <Suspense fallback={<PageFallback />}>
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
                <Route path="/network" element={<NetworkPage />} />
                <Route path="/descriptives" element={<DescriptivesPage />} />
                <Route path="/docs" element={<DocumentationPage />} />
                <Route path="/downloads" element={<DownloadsPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </Suspense>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
}

export default App;
