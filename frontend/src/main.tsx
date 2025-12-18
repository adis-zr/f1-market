import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import './index.css';
import App from './App.tsx';
import { fetchCsrfToken } from './api/client';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Fetch CSRF token on app initialization with retry logic
async function initializeCsrfToken(retries = 3): Promise<void> {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      await fetchCsrfToken();
      return;
    } catch (error) {
      console.error(`CSRF token fetch attempt ${attempt} failed:`, error);
      if (attempt < retries) {
        // Wait before retrying (exponential backoff)
        await new Promise((resolve) => setTimeout(resolve, 1000 * attempt));
      }
    }
  }
  console.error('Failed to fetch CSRF token after all retries');
}

// Initialize CSRF token before rendering, then start the app
async function main() {
  // Wait for CSRF token to be fetched before rendering
  await initializeCsrfToken();

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </StrictMode>
  );
}

main().catch(console.error);
