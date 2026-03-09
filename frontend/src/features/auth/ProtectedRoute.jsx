import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './AuthContext.jsx';

/**
 * ProtectedRoute — requires authentication.
 * Unauthenticated users are redirected to /login.
 */
const ProtectedRoute = () => {
	const { isAuthenticated, loading } = useAuth();

	if (loading) {
		return <div style={{ padding: '24px' }}>Chargement...</div>;
	}

	if (!isAuthenticated) {
		return <Navigate to="/login" replace />;
	}

	return <Outlet />;
};

export default ProtectedRoute;
