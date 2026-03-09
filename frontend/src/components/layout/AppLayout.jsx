import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Button } from '../ui/button.jsx';
import { Bell, Briefcase, LogOut, Search, User } from 'lucide-react';
import { useAuth } from '../../features/auth/AuthContext.jsx';

const AppLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();
  const isHome = location.pathname === '/';

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* H. Skip navigation link */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <header className="sticky top-0 z-50 border-b border-neutral-200 bg-white" role="banner">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <Link to="/" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
                <Briefcase className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-semibold text-neutral-900">BidWise</span>
            </Link>

            {!isHome && (
              <nav className="hidden items-center gap-8 md:flex" aria-label="Main navigation">
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
                      to="/dashboard"
                      className="flex items-center gap-2 text-neutral-700 hover:text-neutral-900"
                    >
                      <User className="h-4 w-4" />
                      My Dashboard
                    </Link>
                    <Link to="/profile" className="text-neutral-700 hover:text-neutral-900">
                      Profile
                    </Link>
                  </>
                )}
              </nav>
            )}

            <div className="flex items-center gap-3">
              {!isHome && (
                <>
                  {isAuthenticated ? (
                    <>
                      <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
                        <Bell className="h-5 w-5" aria-hidden="true" />
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
                    <Button variant="outline" asChild>
                      <Link to="/login">Sign In</Link>
                    </Button>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      <main id="main-content" tabIndex={-1}>
        <Outlet />
      </main>

      <footer className="mt-20 border-t border-neutral-200 bg-white" role="contentinfo">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
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
              <h3 className="mb-3 font-medium text-neutral-900">Platform</h3>
              <ul className="space-y-2 text-sm text-neutral-600">
                <li>
                  <Link to="/opportunities" className="hover:text-neutral-900">
                    Browse Opportunities
                  </Link>
                </li>
                <li>
                  <Link to="/dashboard" className="hover:text-neutral-900">
                    My Dashboard
                  </Link>
                </li>
                <li>
                  <Link to="/profile" className="hover:text-neutral-900">
                    My Profile
                  </Link>
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
