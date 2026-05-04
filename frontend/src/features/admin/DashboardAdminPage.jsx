import DashboardAdminContent from './components/DashboardAdminContent.jsx';
import { useDashboard } from './hooks/useDashboard.js';

const DashboardAdminPage = () => {
  const dashboardState = useDashboard();

  return <DashboardAdminContent {...dashboardState} />;
};

export default DashboardAdminPage;
