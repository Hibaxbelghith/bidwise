import { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Button } from '../ui/button.jsx';
import {
  Bell,
  Building2,
  ChevronDown,
  LogOut,
  Mail,
  MessageCircle,
  Search,
  Settings,
  ShieldCheck,
  User,
} from 'lucide-react';
import { useAuth } from '../../features/auth/AuthContext.jsx';
import {
  getProfileCompletionScore,
} from '../../features/opportunities/utils/recommendationUtils.js';

const PROFILE_VISITED_KEY = 'bidwise:profile-visited:v1';
const LOGOUT_REDIRECT_DELAY_MS = 160;

const isCallsForTenderOnlyProfile = (profile) => {
  const types = Array.isArray(profile?.opportunity_types) ? profile.opportunity_types : [];
  return types.length === 1 && types[0] === 'CALLS_FOR_TENDER';
};

const animationStyles = `
  @keyframes attention-pulse-keyframe {
    0% {
      transform: scale(0.7);
      opacity: 0.7;
    }
    50% {
      transform: scale(1.4);
      opacity: 1;
    }
    100% {
      transform: scale(0.7);
      opacity: 0.7;
    }
  }
  .animate-attention-pulse {
    animation: attention-pulse-keyframe 1.2s ease-in-out infinite !important;
  }
`;

const AppLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, loading: authLoading, user, logout } = useAuth();
  const [showProfileTooltip, setShowProfileTooltip] = useState(false);
  const [hasUserVisitedProfile, setHasUserVisitedProfile] = useState(false);
  const [isLogoutPending, setIsLogoutPending] = useState(false);
  const [isOrganizationAccountMenuOpen, setIsOrganizationAccountMenuOpen] = useState(false);
  const tooltipRef = useRef(null);
  const hoverTimeoutRef = useRef(null);
  const organizationAccountMenuRef = useRef(null);
  
  const isHome = location.pathname === '/';
  const isOrganizationLanding = location.pathname === '/organizations';
  const isOrganizationSurface =
    isOrganizationLanding || location.pathname.startsWith('/organization');
  const isAdminRoute =
    location.pathname.startsWith('/dashboard-admin') || location.pathname.startsWith('/admin');
  const isAdmin = Boolean(user?.is_admin || user?.is_staff || user?.is_superuser);
  const isOrganizationAccount = user?.account_type === 'organization';
  const authPendingWithoutUser = authLoading && !user;
  const isOrganizationWorkspace = isOrganizationSurface && isOrganizationAccount;
  const dashboardPath = isOrganizationAccount ? '/organization/dashboard' : '/dashboard';
  const dashboardLabel = isOrganizationAccount ? 'Organization Dashboard' : 'My Dashboard';
  const organizationLogo = user?.organization_profile?.logo || '';
  const organizationName = user?.organization_profile?.organization_name || 'Organization';
  const profileCompletionScore = getProfileCompletionScore(user);
  const isProfileComplete = profileCompletionScore >= 60;
  const isTenderOnlyProfile = isCallsForTenderOnlyProfile(user?.profil);
  
  // Besoin de nudge = profil incomplet ET utilisateur non-organisation
  const needsProfileNudge =
    isAuthenticated &&
    !isOrganizationAccount &&
    !isTenderOnlyProfile &&
    !isProfileComplete;

  // Vérifier si l'utilisateur a déjà visité son profil (une fois dans sa vie)
  useEffect(() => {
    if (!user?.id || typeof window === 'undefined') {
      setHasUserVisitedProfile(false);
      return;
    }

    try {
      setHasUserVisitedProfile(localStorage.getItem(`${PROFILE_VISITED_KEY}:${user.id}`) === 'true');
    } catch {
      setHasUserVisitedProfile(false);
    }
  }, [user?.id]);

  // Marquer que l'utilisateur a visité son profil (appelé quand il va sur /profile)
  const markProfileVisited = useCallback(() => {
    if (!user?.id || typeof window === 'undefined') return;
    try {
      localStorage.setItem(`${PROFILE_VISITED_KEY}:${user?.id}`, 'true');
    } catch {}
    setHasUserVisitedProfile(true);
  }, [user?.id]);

  // Décider si le pulse doit être affiché
  // Conditions : besoin de nudge + n'a jamais visité son profil
  const shouldShowPulse = useMemo(() => {
    if (!needsProfileNudge) return false;
    if (isHome || isOrganizationSurface || isAdminRoute) return false;
    if (location.pathname === '/profile' || location.pathname.startsWith('/onboarding')) return false;
    // Le pulse s'affiche uniquement si l'utilisateur n'a JAMAIS visité son profil
    return !hasUserVisitedProfile;
  }, [needsProfileNudge, isHome, isOrganizationSurface, isAdminRoute, location.pathname, hasUserVisitedProfile]);

  // Détecter quand l'utilisateur est sur la page profil pour marquer la visite
  useEffect(() => {
    if (location.pathname === '/profile' && user?.id && !hasUserVisitedProfile) {
      markProfileVisited();
    }
  }, [location.pathname, user?.id, hasUserVisitedProfile, markProfileVisited]);

  useEffect(() => {
    if (!isOrganizationAccountMenuOpen) return undefined;

    const handlePointerDown = (event) => {
      if (!organizationAccountMenuRef.current?.contains(event.target)) {
        setIsOrganizationAccountMenuOpen(false);
      }
    };

    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [isOrganizationAccountMenuOpen]);

  // Gestion du hover avec délai pour éviter les clignotements
  const handleMouseEnter = () => {
    if (!needsProfileNudge) return;
    
    // Petit délai avant d'afficher (évite les ouverture intempestives)
    hoverTimeoutRef.current = setTimeout(() => {
      setShowProfileTooltip(true);
    }, 150);
  };

  const handleMouseLeave = () => {
    // Annuler le timeout si pas encore exécuté
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }
    
    // Ne pas fermer immédiatement si la souris est sur la tooltip
    // La tooltip a son propre gestionnaire onMouseEnter/onMouseLeave
    setTimeout(() => {
      if (!tooltipRef.current?.matches(':hover')) {
        setShowProfileTooltip(false);
      }
    }, 100);
  };

  // Gestion du hover sur la tooltip (pour la garder ouverte)
  const handleTooltipMouseEnter = () => {
    setShowProfileTooltip(true);
  };

  const handleTooltipMouseLeave = () => {
    setShowProfileTooltip(false);
  };

  // Click sur l'icône : redirige vers profile
  const handleProfileClick = () => {
    navigate('/profile');
  };

  const handleGoToProfile = () => {
    setShowProfileTooltip(false);
    navigate('/profile');
  };

  const handleLogout = () => {
    if (isLogoutPending) return;

    setIsLogoutPending(true);
    window.setTimeout(async () => {
      await logout();
      navigate('/', { replace: true });
    }, LOGOUT_REDIRECT_DELAY_MS);
  };

  // Ne pas afficher la tooltip sur certaines pages
  const shouldShowTooltip = showProfileTooltip && 
    needsProfileNudge && 
    !isHome && 
    !isOrganizationSurface && 
    !isAdminRoute && 
    location.pathname !== '/profile' && 
    !location.pathname.startsWith('/onboarding');

  const shouldShowFooter = !isOrganizationSurface && !isAdminRoute;

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: animationStyles }} />
      <div className="min-h-screen bg-neutral-50">
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>

        {!isOrganizationLanding ? (
          <header className="sticky top-0 z-50 border-b border-neutral-200 bg-white" role="banner">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
              <div className="flex h-16 items-center justify-between">
                <Link to="/" className="flex items-center gap-2">
                  <img src="/BidWise Logo.svg" alt="BidWise Logo" width="190" height="50"/>
                </Link>

                {!isHome && !isOrganizationSurface && (
                  <nav className="hidden items-center gap-8 md:flex" aria-label="Main navigation">
                    <Link
                      to="/opportunities"
                      className="flex items-center gap-2 text-neutral-700 hover:text-neutral-900"
                    >
                      <Search className="h-4 w-4" />
                      Browse Opportunities
                    </Link>
                    {!authPendingWithoutUser && isAuthenticated && (
                      <>
                        {!isAdminRoute ? (
                          <Link
                            to={dashboardPath}
                            className="flex items-center gap-2 text-neutral-700 hover:text-neutral-900"
                          >
                            {isOrganizationAccount ? (
                              organizationLogo ? (
                                <img
                                  src={organizationLogo}
                                  alt={`${organizationName} logo`}
                                  className="h-4 w-4 rounded-sm object-contain"
                                  loading="lazy"
                                  onError={(event) => {
                                    event.currentTarget.style.display = 'none';
                                  }}
                                />
                              ) : (
                                <Building2 className="h-4 w-4" />
                              )
                            ) : (
                              <User className="h-4 w-4" />
                            )}
                            {dashboardLabel}
                          </Link>
                        ) : null}
                        {isAdmin ? (
                          <Link
                            to="/dashboard-admin"
                            className="flex items-center gap-2 text-neutral-700 hover:text-neutral-900"
                          >
                            <ShieldCheck className="h-4 w-4" />
                            Admin Panel
                          </Link>
                        ) : null}
                      </>
                    )}
                  </nav>
                )}

                <div className="flex items-center gap-3">
                  {isHome ? (
                    <Button
                      asChild
                      className="h-9 rounded-md border border-emerald-200 bg-emerald-50 px-3 text-sm text-emerald-900 shadow-sm hover:bg-emerald-100 sm:px-4"
                    >
                      <Link to="/organizations">
                        <Building2 className="h-4 w-4" aria-hidden="true" />
                        <span className="hidden sm:inline">For Organizations</span>
                        <span className="sm:hidden">Organizations</span>
                      </Link>
                    </Button>
                  ) : (
                    <>
                      {authPendingWithoutUser ? (
                        <div
                          className="h-9 w-24 rounded-md border border-neutral-200 bg-neutral-50"
                          aria-hidden="true"
                        />
                      ) : isAuthenticated ? (
                        <>
                          {isOrganizationWorkspace ? (
                            <>
                              <Button variant="ghost" size="icon" className="relative" aria-label="Messages">
                                <Mail className="h-5 w-5" aria-hidden="true" />
                                <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-blue-600" />
                              </Button>
                              <div className="relative" ref={organizationAccountMenuRef}>
                                <button
                                  type="button"
                                  className="inline-flex h-9 items-center gap-2 rounded-md border border-neutral-200 bg-white px-3 text-sm text-neutral-800 hover:bg-neutral-50"
                                  onClick={() => setIsOrganizationAccountMenuOpen((previous) => !previous)}
                                >
                                  {organizationLogo ? (
                                    <img
                                      src={organizationLogo}
                                      alt={`${organizationName} logo`}
                                      className="h-4 w-4 rounded-sm object-contain"
                                      loading="lazy"
                                      onError={(event) => {
                                        event.currentTarget.style.display = 'none';
                                      }}
                                    />
                                  ) : (
                                    <Building2 className="h-4 w-4" aria-hidden="true" />
                                  )}
                                  <span className="hidden max-w-[220px] truncate sm:inline">
                                    {organizationName}
                                  </span>
                                  <ChevronDown className="h-4 w-4" aria-hidden="true" />
                                </button>
                                {isOrganizationAccountMenuOpen ? (
                                  <div className="absolute right-0 top-full z-50 mt-2 w-64 rounded-lg border border-neutral-200 bg-white py-2 shadow-lg shadow-neutral-950/10">
                                    <div className="border-b border-neutral-100 px-4 py-3">
                                      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                                        Organization account
                                      </p>
                                      <p className="mt-1 truncate text-sm font-medium text-neutral-950">{organizationName}</p>
                                      <p className="mt-1 truncate text-xs text-neutral-500">{user?.email}</p>
                                    </div>
                                    <Link
                                      to="/organization/create-account"
                                      className="flex items-center gap-3 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 hover:text-neutral-950"
                                      onClick={() => setIsOrganizationAccountMenuOpen(false)}
                                    >
                                      <Settings className="h-4 w-4" aria-hidden="true" />
                                      Account settings
                                    </Link>
                                    <Link
                                      to="/organizations"
                                      className="flex items-center gap-3 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 hover:text-neutral-950"
                                      onClick={() => setIsOrganizationAccountMenuOpen(false)}
                                    >
                                      <MessageCircle className="h-4 w-4" aria-hidden="true" />
                                      Contact us
                                    </Link>
                                    <button
                                      type="button"
                                      className="flex w-full items-center gap-3 px-4 py-2 text-left text-sm text-neutral-700 hover:bg-neutral-50 hover:text-neutral-950 disabled:opacity-50"
                                      onClick={handleLogout}
                                      disabled={isLogoutPending}
                                    >
                                      <LogOut className="h-4 w-4" aria-hidden="true" />
                                      Logout
                                    </button>
                                  </div>
                                ) : null}
                              </div>
                            </>
                          ) : (
                            <>
                              <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
                                <Bell className="h-5 w-5" aria-hidden="true" />
                                <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-blue-600" />
                              </Button>
                              {isAdminRoute ? (
                            <span className="hidden items-center gap-2 rounded-md border border-neutral-200 px-3 py-1.5 text-sm font-medium text-neutral-700 lg:inline-flex">
                              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                              Admin Panel
                            </span>
                              ) : (
                            <div className="relative">
                              <button
                                type="button"
                                className="relative inline-flex h-9 w-9 items-center justify-center rounded-md border border-neutral-200 bg-white text-neutral-700 hover:bg-neutral-50 hover:text-neutral-950"
                                aria-label="Profile"
                                onClick={handleProfileClick}
                                onMouseEnter={handleMouseEnter}
                                onMouseLeave={handleMouseLeave}
                              >
                                <span className="relative inline-flex">
                                  <User className="cursor-pointer h-4 w-4" aria-hidden="true" />
                                  {needsProfileNudge && (
                                    <span className="absolute -right-1.5 -top-1.5 flex h-3 w-3">
                                      <span
                                        className={[
                                          'inline-flex h-full w-full rounded-full',
                                          shouldShowPulse
                                            ? 'animate-attention-pulse bg-blue-600'
                                            : 'bg-blue-600',
                                        ].join(' ')}
                                      />
                                    </span>
                                  )}
                                </span>
                              </button>
                              
                              {/* Tooltip au survol */}
                              {shouldShowTooltip && (
                                <div 
                                  ref={tooltipRef}
                                  className="absolute left-1/2 -translate-x-1/2 top-full mt-2 z-50 w-80 rounded-md border border-neutral-200 bg-white p-4 shadow-lg shadow-neutral-950/10"
                                  onMouseEnter={handleTooltipMouseEnter}
                                  onMouseLeave={handleTooltipMouseLeave}
                                >
                                  {/* Flèche qui pointe vers l'icône */}
                                  <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-3 h-3 rotate-45 border-l border-t border-neutral-200 bg-white"></div>
                                  
                                  <div className="flex items-start gap-3">
                                    <div className="min-w-0 flex-1">
                                      <p className="text-sm font-semibold text-neutral-950">Is your profile right?</p>
                                      <p className="mt-1 text-sm leading-6 text-neutral-600">
                                        Your latest profile info is powering BidWise AI recommendations. Take a moment to double check.
                                      </p>
                                      <div className="mt-3 flex items-center justify-between gap-3">
                                        <span className="text-xs font-semibold text-blue-700">
                                          {profileCompletionScore}% complete
                                        </span>
                                        <Button size="sm" className="bg-blue-600 text-white hover:bg-blue-700" onClick={handleGoToProfile}>
                                          Go to profile
                                        </Button>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                              )}
                              <Button
                                className="cursor-pointer"
                                variant="outline"
                                onClick={handleLogout}
                                disabled={isLogoutPending}
                              >
                                <LogOut className="mr-2 h-4 w-4" />
                                Logout
                              </Button>
                            </>
                          )}
                        </>
                      ) : (
                        <Button variant="outline" asChild>
                          <Link to="/login" className='cursor-pointer' >Sign In</Link>
                        </Button>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          </header>
        ) : null}

        <main id="main-content" tabIndex={-1}>
          <Outlet />
        </main>

        {shouldShowFooter ? (
          <footer className="mt-20 border-t border-neutral-200 bg-white" role="contentinfo">
            <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
              <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
                <div>
                  <div className="flex items-center gap-2">
                    <img src="/BidWise Logo.png" alt="BidWise Logo" className="h-16 w-auto object-contain" />
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
                      <Link to={dashboardPath} className="hover:text-neutral-900">
                        {dashboardLabel}
                      </Link>
                    </li>
                    <li>
                      <Link to="/profile" className="cursor-pointer hover:text-neutral-900">
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
        ) : null}
      </div>
    </>
  );
};

export default AppLayout;
