import axios from "axios";
import { getApiBaseUrl } from './config.js';

const api = axios.create({
  baseURL: getApiBaseUrl(import.meta.env),
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
