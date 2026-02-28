import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

/**
 * ProtectedRoute — guards routes by authentication and optionally by role.
 *
 * @param {Object} props
 * @param {string[]} [props.allowedRoles] — e.g. ['ORGANISATION']. ADMIN always has access.
 *   If omitted, any authenticated user is allowed.
 */
const ProtectedRoute = ({ allowedRoles }) => {
	const { isAuthenticated, user, loading } = useAuth();

	if (loading) {
		return <div style={{ padding: '24px' }}>Chargement...</div>;
	}

	// Not logged in → send to login
	if (!isAuthenticated) {
		return <Navigate to="/login" replace />;
	}

	// Role check (only when allowedRoles is specified)
	if (allowedRoles && allowedRoles.length > 0) {
		const userRole = user?.account_type;

		// ADMIN bypasses every role gate
		const hasAccess =
			userRole === 'ADMIN' || allowedRoles.includes(userRole);

		if (!hasAccess) {
			// Authenticated but wrong role → redirect to generic dashboard
			return <Navigate to="/dashboard" replace />;
		}
	}

	return <Outlet />;
};

export default ProtectedRoute;
