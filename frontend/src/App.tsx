import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { MarketsPage } from './pages/MarketsPage';
import { MarketDetailPage } from './pages/MarketDetailPage';
import { EventsPage } from './pages/EventsPage';
import { EventDetailPage } from './pages/EventDetailPage';
import { PortfolioPage } from './pages/PortfolioPage';
import { WalletPage } from './pages/WalletPage';
import {
  ReplayPage,
  ReplayPortfolioPage,
  ReplayWalletPage,
  ReplayCompletePage,
  ReplayLeaderboardPage,
} from './pages/replay';
import { ToastContainer } from './components/ui/toast';
import { onUnauthorized } from './api/client';
import { ErrorBoundary } from './components/ErrorBoundary';

// Component to handle auth redirects
function AuthRedirectHandler() {
  const navigate = useNavigate();

  useEffect(() => {
    const unsubscribe = onUnauthorized(() => {
      // Only redirect if not already on login page
      if (window.location.pathname !== '/login') {
        navigate('/login', { replace: true });
      }
    });
    return unsubscribe;
  }, [navigate]);

  return null;
}

function App() {
  return (
    <BrowserRouter>
      <AuthRedirectHandler />
      <ErrorBoundary>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          {/* Protected routes - require authentication */}
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<AppLayout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="markets" element={<MarketsPage />} />
              <Route path="markets/:marketId" element={<MarketDetailPage />} />
              <Route path="events" element={<EventsPage />} />
              <Route path="events/:eventId" element={<EventDetailPage />} />
              <Route path="portfolio" element={<PortfolioPage />} />
              <Route path="wallet" element={<WalletPage />} />
              {/* Replay Mode Routes */}
              <Route path="replay" element={<ReplayPage />} />
              <Route path="replay/portfolio" element={<ReplayPortfolioPage />} />
              <Route path="replay/wallet" element={<ReplayWalletPage />} />
              <Route path="replay/complete" element={<ReplayCompletePage />} />
              <Route path="replay/leaderboard" element={<ReplayLeaderboardPage />} />
            </Route>
          </Route>
        </Routes>
      </ErrorBoundary>
      <ToastContainer />
    </BrowserRouter>
  );
}

export default App;
