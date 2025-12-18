import axios from 'axios';

// Normalize URL to ensure protocol (Render's host property returns hostname without protocol)
const rawApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000';
const baseURL = rawApiUrl.startsWith('http') ? rawApiUrl : `https://${rawApiUrl}`;

// Store CSRF token
let csrfToken: string | null = null;

// Event emitter for auth state changes
type AuthEventListener = () => void;
const authEventListeners: AuthEventListener[] = [];

export function onUnauthorized(listener: AuthEventListener): () => void {
  authEventListeners.push(listener);
  return () => {
    const index = authEventListeners.indexOf(listener);
    if (index > -1) {
      authEventListeners.splice(index, 1);
    }
  };
}

function emitUnauthorized(): void {
  authEventListeners.forEach((listener) => listener());
}

const apiClient = axios.create({
  baseURL,
  withCredentials: true, // For session cookies
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor to add CSRF token to state-changing requests
apiClient.interceptors.request.use(
  (config) => {
    // Add CSRF token to POST, PUT, DELETE, PATCH requests
    if (csrfToken && config.method && ['post', 'put', 'delete', 'patch'].includes(config.method.toLowerCase())) {
      config.headers['X-CSRFToken'] = csrfToken;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Emit unauthorized event to trigger redirect to login
      emitUnauthorized();
    }
    return Promise.reject(error);
  }
);

/**
 * Fetch CSRF token from the server.
 * Call this on app initialization before making any POST requests.
 */
export async function fetchCsrfToken(): Promise<void> {
  try {
    const response = await apiClient.get('/auth/csrf-token');
    csrfToken = response.data.csrf_token;
  } catch (error) {
    console.error('Failed to fetch CSRF token:', error);
  }
}

/**
 * Get the current CSRF token (for manual use if needed).
 */
export function getCsrfToken(): string | null {
  return csrfToken;
}

export default apiClient;
