import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Home from './pages/HomePage.jsx';
import { OpportunitiesBrowse } from './features/opportunities/pages/OpportunitiesPage.jsx';
import OpportunityDetail from './features/opportunities/pages/OpportunityDetailPage.jsx';
import NotFound from './pages/NotFoundPage.jsx';
import LoginPage from './features/auth/LoginPage.jsx';
import Onboarding from './features/onboarding/OnboardingPage.jsx';
import AppLayout from './components/layout/AppLayout.jsx';
import ScrollManager from './components/layout/ScrollManager.jsx';
import Dashboard from './features/dashboard/DashboardPage.jsx';
import AdminLayout from './features/admin/AdminLayout.jsx';
import AdminLoginPage from './features/admin/AdminLoginPage.jsx';
import AdminRoute from './features/admin/AdminRoute.jsx';
import DashboardAdminPage from './features/admin/DashboardAdminPage.jsx';
import AdminOpportunitiesPage from './features/admin/AdminOpportunitiesPage.jsx';
import AdminUsersPage from './features/admin/AdminUsersPage/index.jsx';
import Profile from './features/profile/ProfilePage.jsx';
import ProtectedRoute from './features/auth/ProtectedRoute.jsx';
import OrganizationRoute from './features/organization/OrganizationRoute.jsx';
import OrganizationLandingPage from './features/organization/pages/OrganizationLandingPage.jsx';
import CreateOrganizationAccountPage from './features/organization/pages/CreateOrganizationAccountPage.jsx';
import OrganizationDashboardPage from './features/organization/pages/OrganizationDashboardPage.jsx';
import OrganizationDashboardLegacyPage from './features/organization/pages/OrganizationDashboardLegacyPage.jsx';
import OrganizationInternshipPostPage from './features/organization/pages/OrganizationInternshipPostPage.jsx';
import OrganizationJobPostPage from './features/organization/pages/OrganizationJobPostPage.jsx';
import OrganizationOpportunityPostPage from './features/organization/pages/OrganizationOpportunityPostPage.jsx';
import OrganizationOpportunityDetailPage from './features/organization/pages/OrganizationOpportunityDetailPage.jsx';
import OrganizationOpportunitySubmittedPage from './features/organization/pages/OrganizationOpportunitySubmittedPage.jsx';
import OrganizationSeasonalPostPage from './features/organization/pages/OrganizationSeasonalPostPage.jsx';
import OrganizationTenderPostPage from './features/organization/pages/OrganizationTenderPostPage.jsx';

import './App.css';

const App = () => (
  <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <ScrollManager />
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/organizations" element={<OrganizationLandingPage />} />
        <Route path="/opportunities" element={<OpportunitiesBrowse />} />
        <Route path="/opportunities/:id" element={<OpportunityDetail />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
        <Route element={<OrganizationRoute />}>
          <Route path="/organization/create-account" element={<CreateOrganizationAccountPage />} />
        </Route>
        <Route element={<OrganizationRoute requireOrganizationAccount />}>
          <Route path="/organization/dashboard" element={<OrganizationDashboardPage />} />
          <Route path="/organization/opportunities/:opportunityId" element={<OrganizationOpportunityDetailPage />} />
          <Route path="/organization/post" element={<OrganizationOpportunityPostPage />} />
          <Route path="/organization/post/job" element={<OrganizationJobPostPage />} />
          <Route path="/organization/post/job/:opportunityId/edit" element={<OrganizationJobPostPage />} />
          <Route path="/organization/post/internship" element={<OrganizationInternshipPostPage />} />
          <Route path="/organization/post/internship/:opportunityId/edit" element={<OrganizationInternshipPostPage />} />
          <Route path="/organization/post/seasonal" element={<OrganizationSeasonalPostPage />} />
          <Route path="/organization/post/seasonal/:opportunityId/edit" element={<OrganizationSeasonalPostPage />} />
          <Route path="/organization/post/call-for-tender" element={<OrganizationTenderPostPage />} />
          <Route path="/organization/post/call-for-tender/:opportunityId/edit" element={<OrganizationTenderPostPage />} />
          <Route path="/organization/post/submitted" element={<OrganizationOpportunitySubmittedPage />} />
          <Route path="/organization/opportunity-submitted" element={<OrganizationOpportunitySubmittedPage />} />
          <Route path="/organization/submitted" element={<OrganizationOpportunitySubmittedPage />} />
          <Route path="/organization/dashboard-legacy" element={<OrganizationDashboardLegacyPage />} />
        </Route>

      </Route>

      <Route path="/login" element={<LoginPage />} />
      <Route path="/dashboard-admin" element={<Navigate to="/admin/dashboard" replace />} />
      <Route path="/admin/login" element={<AdminLoginPage />} />

      <Route element={<AdminRoute />}>
        <Route element={<AdminLayout />}>
          <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="/admin/dashboard" element={<DashboardAdminPage />} />
          <Route path="/admin/dashboard/:dashboardView" element={<DashboardAdminPage />} />
          <Route path="/admin/opportunities" element={<AdminOpportunitiesPage />} />
          <Route path="/admin/users" element={<AdminUsersPage />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route path="/onboarding" element={<Onboarding />} />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  </BrowserRouter>
);

export default App;
