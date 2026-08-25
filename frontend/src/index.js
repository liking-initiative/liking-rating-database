import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ConfigProvider } from 'antd';
import App from './App';
import './styles/main.css';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

// Ant Design theme configuration.
// The same values are declared as CSS custom properties in styles/main.css,
// so charts and UI chrome resolve to one palette.
const theme = {
  token: {
    colorPrimary: '#085AB3',
    colorInfo: '#085AB3',
    colorWarning: '#E78A00',
    colorLink: '#085AB3',
    colorBgLayout: '#f7f8fa',
    borderRadius: 6,
    wireframe: false,
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', " +
      "'Ubuntu', 'Cantarell', 'Open Sans', 'Helvetica Neue', sans-serif",
  },
  components: {
    Layout: {
      headerBg: '#085AB3',
      headerColor: 'rgba(255, 255, 255, 0.92)',
    },
    Menu: {
      darkItemBg: '#0b3c74',
      darkSubMenuItemBg: '#0b3c74',
      darkItemSelectedBg: '#085AB3',
    },
  },
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider theme={theme}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
