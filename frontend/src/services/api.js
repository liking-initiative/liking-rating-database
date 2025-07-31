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
});

// Request interceptor for auth tokens if needed
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Studies API
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

export const createStudy = async (studyData) => {
  const response = await api.post('/studies', studyData);
  return response.data;
};

export const updateStudy = async (studyId, studyData) => {
  const response = await api.put(`/studies/${studyId}`, studyData);
  return response.data;
};

export const deleteStudy = async (studyId) => {
  const response = await api.delete(`/studies/${studyId}`);
  return response.data;
};

// Datasets API
export const getDatasets = async (params = {}) => {
  const response = await api.get('/datasets', { params });
  return response.data;
};

export const getDataset = async (datasetId) => {
  const response = await api.get(`/datasets/${datasetId}`);
  return response.data;
};

export const createDataset = async (datasetData) => {
  const response = await api.post('/datasets', datasetData);
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

export const generateCitation = (study, dataset = null) => {
  const authors = study.authors.join(', ');
  const year = study.year;
  const title = dataset ? `${study.name} - ${dataset.name}` : study.name;
  const journal = study.journal ? `, ${study.journal}` : '';
  const doi = study.doi ? `. DOI: ${study.doi}` : '';
  
  return `${authors} (${year}). ${title}${journal}${doi}`;
};

export default api;
