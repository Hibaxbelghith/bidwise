import { useParams } from 'react-router-dom';

import DashboardAdminContent from './components/DashboardAdminContent.jsx';
import { useDashboard } from './hooks/useDashboard.js';

const DashboardAdminPage = () => {
  const { dashboardView } = useParams();
  const dashboardState = useDashboard(dashboardView || 'dashboard');

  return <DashboardAdminContent {...dashboardState} />;
};

export default DashboardAdminPage;
