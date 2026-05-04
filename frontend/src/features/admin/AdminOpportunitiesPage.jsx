import AdminOpportunitiesContent from './components/AdminOpportunitiesContent.jsx';
import { useOpportunities } from './hooks/useOpportunities.js';

const AdminOpportunitiesPage = () => {
  const opportunitiesState = useOpportunities();

  return <AdminOpportunitiesContent {...opportunitiesState} />;
};

export default AdminOpportunitiesPage;
