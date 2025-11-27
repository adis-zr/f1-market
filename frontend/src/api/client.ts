import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000',
  withCredentials: true, // For session cookies
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login if needed
      console.error('Unauthorized request');
    }
    return Promise.reject(error);
  }
);

export default apiClient;

