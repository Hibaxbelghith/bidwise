import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/HomePage.jsx';
import { OpportunitiesBrowse } from './features/opportunities/OpportunitiesPage.jsx';
import OpportunityDetail from './features/opportunities/OpportunityDetailPage.jsx';
import NotFound from './pages/NotFoundPage.jsx';
import LoginPage from './features/auth/LoginPage.jsx';
import Onboarding from './features/onboarding/OnboardingPage.jsx';
import AppLayout from './components/layout/AppLayout.jsx';
import ScrollManager from './components/layout/ScrollManager.jsx';
import Dashboard from './features/dashboard/DashboardPage.jsx';
import Profile from './features/profile/ProfilePage.jsx';
import ProtectedRoute from './features/auth/ProtectedRoute.jsx';
import './App.css';

const App = () => (
  <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <ScrollManager />
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/opportunities" element={<OpportunitiesBrowse />} />
        <Route path="/opportunities/:id" element={<OpportunityDetail />} />

        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/profile" element={<Profile />} />
        </Route>

      </Route>

      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/onboarding" element={<Onboarding />} />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  </BrowserRouter>
);

export default App;
