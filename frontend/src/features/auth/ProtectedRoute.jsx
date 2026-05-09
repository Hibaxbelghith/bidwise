import { useEffect, useRef, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './AuthContext.jsx';

const FETCHING_SKELETON_DELAY_MS = 150;
const FETCHING_SKELETON_MIN_VISIBLE_MS = 250;

const SkeletonOpportunityCard = ({ compact = false }) => (
	<article className="rounded-lg border border-neutral-200 bg-white p-5">
		<div className="animate-pulse space-y-4">
			<div className="flex items-start gap-4">
				<div className="h-12 w-12 shrink-0 rounded-lg bg-neutral-200" />
				<div className="min-w-0 flex-1 space-y-2">
					<div className="h-4 w-3/4 rounded bg-neutral-200" />
					<div className="h-3 w-1/2 rounded bg-neutral-100" />
				</div>
			</div>

			{!compact && (
				<>
					<div className="flex flex-wrap gap-2">
						<div className="h-3 w-24 rounded-full bg-neutral-100" />
						<div className="h-3 w-28 rounded-full bg-neutral-100" />
						<div className="h-3 w-20 rounded-full bg-neutral-100" />
					</div>
					<div className="space-y-2">
						<div className="h-3 w-full rounded bg-neutral-100" />
						<div className="h-3 w-11/12 rounded bg-neutral-100" />
						<div className="h-3 w-2/3 rounded bg-neutral-100" />
					</div>
				</>
			)}
		</div>
	</article>
);

const ProtectedRouteSkeleton = () => (
	<section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
		<div className="mb-4 flex items-center justify-between">
			<div className="h-4 w-40 animate-pulse rounded bg-neutral-200" />
			<div className="h-4 w-24 animate-pulse rounded bg-neutral-100" />
		</div>
		<div className="space-y-4">
			{[0, 1, 2].map((index) => (
				<SkeletonOpportunityCard key={index} />
			))}
		</div>
	</section>
);

/**
 * ProtectedRoute — requires authentication.
 * Unauthenticated users are redirected to /login.
 */
const ProtectedRoute = ({ requireAdmin = false }) => {
	const { isAuthenticated, loading, user } = useAuth();
	const [showLoadingSkeleton, setShowLoadingSkeleton] = useState(false);
	const skeletonShownAtRef = useRef(0);
	const skeletonShowTimeoutRef = useRef(null);
	const skeletonHideTimeoutRef = useRef(null);

	useEffect(() => {
		return () => {
			if (skeletonShowTimeoutRef.current) {
				clearTimeout(skeletonShowTimeoutRef.current);
				skeletonShowTimeoutRef.current = null;
			}
			if (skeletonHideTimeoutRef.current) {
				clearTimeout(skeletonHideTimeoutRef.current);
				skeletonHideTimeoutRef.current = null;
			}
		};
	}, []);

	useEffect(() => {
		if (loading) {
			if (skeletonHideTimeoutRef.current) {
				clearTimeout(skeletonHideTimeoutRef.current);
				skeletonHideTimeoutRef.current = null;
			}

			if (!showLoadingSkeleton && !skeletonShowTimeoutRef.current) {
				skeletonShowTimeoutRef.current = setTimeout(() => {
					skeletonShowTimeoutRef.current = null;
					skeletonShownAtRef.current = Date.now();
					setShowLoadingSkeleton(true);
				}, FETCHING_SKELETON_DELAY_MS);
			}
			return undefined;
		}

		if (skeletonShowTimeoutRef.current) {
			clearTimeout(skeletonShowTimeoutRef.current);
			skeletonShowTimeoutRef.current = null;
		}

		if (!showLoadingSkeleton) {
			skeletonShownAtRef.current = 0;
			return undefined;
		}

		const elapsedVisibleMs = Date.now() - (skeletonShownAtRef.current || 0);
		const remainingVisibleMs = FETCHING_SKELETON_MIN_VISIBLE_MS - elapsedVisibleMs;

		if (remainingVisibleMs <= 0) {
			skeletonShownAtRef.current = 0;
			setShowLoadingSkeleton(false);
			return undefined;
		}

		skeletonHideTimeoutRef.current = setTimeout(() => {
			skeletonHideTimeoutRef.current = null;
			skeletonShownAtRef.current = 0;
			setShowLoadingSkeleton(false);
		}, remainingVisibleMs);

		return () => {
			if (skeletonHideTimeoutRef.current) {
				clearTimeout(skeletonHideTimeoutRef.current);
				skeletonHideTimeoutRef.current = null;
			}
		};
	}, [loading, showLoadingSkeleton]);

	if (loading && !showLoadingSkeleton) {
		return null;
	}

	if (showLoadingSkeleton) {
		return <ProtectedRouteSkeleton />;
	}

	if (!isAuthenticated) {
		return <Navigate to="/login" replace />;
	}

	const isAdmin = Boolean(user?.is_admin || user?.is_staff || user?.is_superuser);
	if (requireAdmin && !isAdmin) {
		return <Navigate to="/opportunities" replace />;
	}

	return <Outlet />;
};

export default ProtectedRoute;
