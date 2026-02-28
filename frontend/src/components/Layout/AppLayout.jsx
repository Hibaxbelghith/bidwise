import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Button } from '../ui/button.jsx';
import { Bell, Briefcase, Building2, LogOut, Search, User } from 'lucide-react';
import { useAuth } from '../../context/AuthContext.jsx';

const AppLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();
  const isHome = location.pathname === '/';

  const userRole = user?.account_type;
  const isOrganisation = userRole === 'ORGANISATION' || userRole === 'ADMIN';
  const dashboardPath = userRole === 'ORGANISATION' ? '/organization/dashboard' : '/dashboard';

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      <header className="sticky top-0 z-50 border-b border-neutral-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <Link to="/" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
                <Briefcase className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-semibold text-neutral-900">BidWise</span>
            </Link>

            {!isHome && (
              <nav className="hidden items-center gap-8 md:flex">
                <Link
                  to="/opportunities"
                  className="flex items-center gap-2 text-neutral-700 hover:text-neutral-900"
                >
                  <Search className="h-4 w-4" />
                  Browse Opportunities
                </Link>
                {isAuthenticated && (
                  <>
                    <Link
                      to={dashboardPath}
                      className="flex items-center gap-2 text-neutral-700 hover:text-neutral-900"
                    >
                      <User className="h-4 w-4" />
                      My Dashboard
                    </Link>
                    <Link to="/profile" className="text-neutral-700 hover:text-neutral-900">
                      Profile
                    </Link>
                    {userRole === 'ADMIN' && (
                      <Link
                        to="/organization/dashboard"
                        className="flex items-center gap-2 text-neutral-700 hover:text-neutral-900"
                      >
                        <Building2 className="h-4 w-4" />
                        Organization
                      </Link>
                    )}
                  </>
                )}
              </nav>
            )}

            <div className="flex items-center gap-3">
              {!isHome && (
                <>
                  {isAuthenticated ? (
                    <>
                      <Button variant="ghost" size="icon" className="relative">
                        <Bell className="h-5 w-5" />
                        <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-blue-600" />
                      </Button>
                      <span className="hidden text-sm text-neutral-700 lg:inline">
                        {user?.first_name || user?.profil?.prenom || user?.email}
                      </span>
                      <Button variant="outline" onClick={handleLogout}>
                        <LogOut className="mr-2 h-4 w-4" />
                        Logout
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button variant="outline" asChild>
                        <Link to="/login">Sign In</Link>
                      </Button>
                      <Button asChild>
                        <Link to="/register">Get Started</Link>
                      </Button>
                    </>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      <main>
        <Outlet />
      </main>

      <footer className="mt-20 border-t border-neutral-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-8 md:grid-cols-4">
            <div>
              <div className="mb-4 flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
                  <Briefcase className="h-5 w-5 text-white" />
                </div>
                <span className="text-lg font-semibold text-neutral-900">BidWise</span>
              </div>
              <p className="text-sm text-neutral-600">
                Discover and track professional opportunities with ease.
              </p>
            </div>
            <div>
              <h3 className="mb-3 font-medium text-neutral-900">For Candidates</h3>
              <ul className="space-y-2 text-sm text-neutral-600">
                <li>
                  <Link to="/opportunities" className="hover:text-neutral-900">
                    Browse Opportunities
                  </Link>
                </li>
                <li>
                  <Link to="/candidate/dashboard" className="hover:text-neutral-900">
                    My Dashboard
                  </Link>
                </li>
                <li>
                  <a href="#" className="hover:text-neutral-900">
                    Saved Searches
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="mb-3 font-medium text-neutral-900">For Organizations</h3>
              <ul className="space-y-2 text-sm text-neutral-600">
                <li>
                  <Link to="/organization/post" className="hover:text-neutral-900">
                    Post Opportunity
                  </Link>
                </li>
                <li>
                  <Link to="/organization/dashboard" className="hover:text-neutral-900">
                    Manage Listings
                  </Link>
                </li>
                <li>
                  <a href="#" className="hover:text-neutral-900">
                    API Documentation
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="mb-3 font-medium text-neutral-900">Company</h3>
              <ul className="space-y-2 text-sm text-neutral-600">
                <li>
                  <a href="#" className="hover:text-neutral-900">
                    About
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-neutral-900">
                    Contact
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-neutral-900">
                    Privacy
                  </a>
                </li>
              </ul>
            </div>
          </div>
          <div className="mt-8 border-t border-neutral-200 pt-8 text-center text-sm text-neutral-600">
            © 2026 BidWise. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
};

export default AppLayout;
