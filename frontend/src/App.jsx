import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home.jsx';
import { OpportunitiesBrowse } from './pages/Opportunities.jsx';
import OpportunityDetail from './pages/OpportunityDetail.jsx';
import NotFound from './pages/NotFound.jsx';
import Login from './pages/Login.jsx';
import Register from './pages/Register.jsx';
import ForgotPassword from './pages/ForgotPassword.jsx';
import OrganizationDashboard from './pages/OrganizationDashboard.jsx';
import PostOpportunity from './pages/PostOpportunity.jsx';
import AppLayout from './components/Layout/AppLayout.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Profile from './pages/Profile.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import './App.css';

const App = () => (
  <BrowserRouter>
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/opportunities" element={<OpportunitiesBrowse />} />
        <Route path="/opportunities/:id" element={<OpportunityDetail />} />
        <Route path="/password-reset" element={<ForgotPassword />} />
        
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/profile" element={<Profile />} />
        </Route>

        <Route element={<ProtectedRoute allowedRoles={['ORGANISATION']} />}>
          <Route path="/organization/dashboard" element={<OrganizationDashboard />} />
          <Route path="/organization/post" element={<PostOpportunity />} />
        </Route>
      </Route>

      <Route path="/register" element={<Register />} />
      <Route path="/login" element={<Login />} />

      <Route path="*" element={<NotFound />} />
    </Routes>
  </BrowserRouter>
);

export default App;
