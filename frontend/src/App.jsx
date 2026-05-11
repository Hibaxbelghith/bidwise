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
import AdminUsersPage from './features/admin/AdminUsersPage.jsx';
import Profile from './features/profile/ProfilePage.jsx';
import ProtectedRoute from './features/auth/ProtectedRoute.jsx';
import OrganizationLandingPage from './features/organization/pages/OrganizationLandingPage.jsx';
import CreateOrganizationAccountPage from './features/organization/pages/CreateOrganizationAccountPage.jsx';
import OrganizationDashboardPage from './features/organization/pages/OrganizationDashboardPage.jsx';

import './App.css';

const App = () => (
  <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <ScrollManager />
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/organizations" element={<OrganizationLandingPage />} />
        <Route path="/organization/post" element={<Navigate to="/organizations" replace />} />
        <Route path="/opportunities" element={<OpportunitiesBrowse />} />
        <Route path="/opportunities/:id" element={<OpportunityDetail />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/organization/create-account" element={<CreateOrganizationAccountPage />} />
          <Route path="/organization/dashboard" element={<OrganizationDashboardPage />} />
        </Route>

      </Route>

      <Route path="/login" element={<LoginPage />} />
      <Route path="/dashboard-admin" element={<Navigate to="/admin/dashboard" replace />} />
      <Route path="/admin/login" element={<AdminLoginPage />} />

      <Route element={<AdminRoute />}>
        <Route element={<AdminLayout />}>
          <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="/admin/dashboard" element={<DashboardAdminPage />} />
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
