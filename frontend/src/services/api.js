/**
 * API service for the Liking Rating Database frontend
 */
import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  // FastAPI expects repeated query keys for list params (a=1&a=2),
  // not axios' default bracket notation (a[]=1&a[]=2).
  paramsSerializer: {
    serialize: (params) => {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value === undefined || value === null) return;
        if (Array.isArray(value)) {
          value.forEach((v) => searchParams.append(key, v));
        } else {
          searchParams.append(key, value);
        }
      });
      return searchParams.toString();
    },
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Studies API
// Returns a paginated envelope: { items, total, page, page_size, pages }
export const getStudies = async (params = {}) => {
  const defaultParams = {
    page: 1,
    page_size: 100,
    ...params
  };
  const response = await api.get('/studies', { params: defaultParams });
  return response.data;
};

export const getStudy = async (studyId) => {
  const response = await api.get(`/studies/${studyId}`);
  return response.data;
};

// Datasets API
// Returns a paginated envelope: { items, total, page, page_size, pages }
export const getDatasets = async (params = {}) => {
  const defaultParams = {
    page: 1,
    page_size: 100,
    ...params
  };
  const response = await api.get('/datasets', { params: defaultParams });
  return response.data;
};

export const getDataset = async (datasetId) => {
  const response = await api.get(`/datasets/${datasetId}`);
  return response.data;
};

// Items API
export const getItems = async (params = {}) => {
  const defaultParams = {
    page: 1,
    page_size: 100,
    ...params
  };
  const response = await api.get('/items', { params: defaultParams });
  return response.data;
};

export const getItem = async (itemId) => {
  // Basic UUID validation
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  if (!uuidRegex.test(itemId)) {
    throw new Error(`Invalid item ID format: ${itemId}`);
  }
  
  const response = await api.get(`/items/${itemId}`);
  return response.data;
};

// Search API
export const searchDatasets = async (searchRequest) => {
  const response = await api.post('/search', searchRequest);
  return response.data;
};

// Ratings API
export const getRatings = async (params = {}) => {
  const defaultParams = {
    page: 1,
    page_size: 1000,
    ...params
  };
  const response = await api.get('/ratings', { params: defaultParams });
  return response.data;
};

export const getRatingAggregations = async (params = {}) => {
  const response = await api.get('/ratings/aggregate', { params });
  return response.data;
};

export const getItemRatingsByDataset = async (itemId) => {
  const response = await api.get(`/items/${itemId}/ratings/by-dataset`);
  return response.data;
};

// Download API
export const requestDownload = async (downloadRequest) => {
  const response = await api.post('/download', downloadRequest);
  return response.data;
};

export const getDownload = async (downloadId) => {
  const response = await api.get(`/download/${downloadId}`, {
    responseType: 'blob', // Important for file downloads
  });
  return response;
};

// Statistics API
export const getStatistics = async () => {
  const response = await api.get('/statistics');
  return response.data;
};

// Metadata API
export const getCategories = async () => {
  const response = await api.get('/metadata/categories');
  return response.data;
};

export const getScaleTypes = async () => {
  const response = await api.get('/metadata/scale-types');
  return response.data;
};

export const getYearRange = async () => {
  const response = await api.get('/metadata/years');
  return response.data;
};

// Search suggestions
export const getSearchSuggestions = async (query) => {
  const response = await api.get('/search/suggestions', {
    params: { query }
  });
  return response.data;
};

// Utility functions
export const downloadFile = (blob, filename) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const generateBibtex = (study) => {
  const authors = Array.isArray(study.authors) ? study.authors : [];
  const firstAuthor = authors[0] || 'unknown';
  // "Lastname, F." puts the last name first; "First Lastname" puts it last
  const lastName = firstAuthor.includes(',')
    ? firstAuthor.split(',')[0]
    : firstAuthor.split(/\s+/).filter(Boolean).pop() || 'unknown';
  const firstAuthorKey = lastName.replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
  const citationKey = `${firstAuthorKey || 'unknown'}${study.year || ''}`;

  const fields = [
    `  author = {${authors.join(' and ')}}`,
    `  title = {${study.name}}`,
  ];
  if (study.year) {
    fields.push(`  year = {${study.year}}`);
  }
  if (study.journal) {
    fields.push(`  journal = {${study.journal}}`);
  }
  if (study.doi) {
    fields.push(`  doi = {${study.doi}}`);
  }

  return `@article{${citationKey},\n${fields.join(',\n')}\n}`;
};

export default api;
