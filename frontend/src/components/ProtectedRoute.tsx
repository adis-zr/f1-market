import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useCurrentUser } from '@/hooks';

/**
 * Route guard component that checks authentication before rendering child routes.
 * Redirects to /login if user is not authenticated, preserving the intended destination.
 */
export function ProtectedRoute() {
  const { data: user, isLoading } = useCurrentUser();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (!user?.logged_in) {
    // Redirect to login, preserving intended destination for post-login redirect
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // User is authenticated, render child routes
  return <Outlet />;
}
