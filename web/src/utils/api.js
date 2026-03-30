import axios from 'axios';

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

const api = axios.create({
  baseURL: apiBaseUrl || '/api',
  timeout: 10000,
});

export const fetchApartments = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.minPrice !== null && filters.minPrice !== undefined && filters.minPrice !== '') {
    params.append('min_price', filters.minPrice);
  }
  if (filters.maxPrice !== null && filters.maxPrice !== undefined && filters.maxPrice !== '') {
    params.append('max_price', filters.maxPrice);
  }
  // Support multiple websites as comma-separated values
  // Send "__none__" marker when explicitly no websites selected (returns no results)
  if (filters.websites !== undefined) {
    if (filters.websites.length > 0) {
      params.append('website', filters.websites.join(','));
    } else {
      params.append('website', '__none__');
    }
  }
  if (filters.targetId !== null && filters.targetId !== undefined && filters.targetId !== '') {
    params.append('target_id', filters.targetId);
  }
  if (filters.minTime !== null && filters.minTime !== undefined && filters.minTime !== '') {
    params.append('min_time', filters.minTime);
  }
  if (filters.maxTime !== null && filters.maxTime !== undefined && filters.maxTime !== '') {
    params.append('max_time', filters.maxTime);
  }
  
  const response = await api.get(`/apartments?${params.toString()}`);
  return response.data;
};

export const fetchApartment = async (id) => {
  const response = await api.get(`/apartments/${id}`);
  return response.data;
};

export const fetchWebsites = async () => {
  const response = await api.get('/websites');
  return response.data;
};

export const fetchTargets = async () => {
  const response = await api.get('/targets');
  return response.data;
};

export const fetchStats = async () => {
  const response = await api.get('/stats');
  return response.data;
};

export default api;
