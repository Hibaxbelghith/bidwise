import { memo, useEffect, useState } from 'react';
import { TableCell, TableRow } from '../../../components/ui/table.jsx';

const SKELETON_DELAY_MS = 150;
const SKELETON_ROW_KEYS = Array.from(
  { length: 6 },
  (_, index) => `admin-users-skeleton-${index + 1}`
);

// Composant Shimmer réutilisable
const ShimmerOverlay = ({ delay = 0, className = '' }) => (
  <div 
    className={`absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/30 to-transparent ${className}`}
    style={{
      animation: `shimmer 1.8s ease-in-out infinite ${delay}s`,
    }}
  />
);

// Ligne skeleton moderne avec effet shimmer
const SkeletonRow = ({ className = '', isVisible = false }) => (
  <TableRow className={`relative overflow-hidden transition-all duration-300 ${className} ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}`}>
    {/* Email column - avec nom et email simulé */}
    <TableCell className="px-4 py-4">
      <div className="relative overflow-hidden rounded">
        <div className="h-4 w-48 rounded bg-gradient-to-r from-neutral-100 via-neutral-200/60 to-neutral-100 bg-[length:200%_100%] animate-shimmer" />
        <ShimmerOverlay delay={0} />
      </div>
      <div className="relative mt-2 overflow-hidden rounded">
        <div className="h-3 w-28 rounded bg-gradient-to-r from-neutral-50 via-neutral-100/40 to-neutral-50 bg-[length:200%_100%] animate-shimmer" />
        <ShimmerOverlay delay={0.15} />
      </div>
    </TableCell>
    
    {/* Joined date */}
    <TableCell className="px-4 py-4">
      <div className="relative overflow-hidden rounded">
        <div className="h-4 w-24 rounded bg-gradient-to-r from-neutral-100 via-neutral-200/60 to-neutral-100 bg-[length:200%_100%] animate-shimmer" />
        <ShimmerOverlay delay={0.3} />
      </div>
    </TableCell>
    
    {/* Last login */}
    <TableCell className="px-4 py-4">
      <div className="relative overflow-hidden rounded">
        <div className="h-4 w-32 rounded bg-gradient-to-r from-neutral-100 via-neutral-200/60 to-neutral-100 bg-[length:200%_100%] animate-shimmer" />
        <ShimmerOverlay delay={0.45} />
      </div>
    </TableCell>
    
    {/* Role badge */}
    <TableCell className="px-4 py-4">
      <div className="relative overflow-hidden rounded-full">
        <div className="h-6 w-20 rounded-full bg-gradient-to-r from-neutral-100 via-neutral-200/60 to-neutral-100 bg-[length:200%_100%] animate-shimmer" />
        <ShimmerOverlay delay={0.6} />
      </div>
    </TableCell>
    
    {/* Status badge */}
    <TableCell className="px-4 py-4">
      <div className="relative overflow-hidden rounded-full">
        <div className="h-6 w-20 rounded-full bg-gradient-to-r from-neutral-100 via-neutral-200/60 to-neutral-100 bg-[length:200%_100%] animate-shimmer" />
        <ShimmerOverlay delay={0.75} />
      </div>
    </TableCell>
    
    {/* Actions buttons */}
    <TableCell className="px-4 py-4">
      <div className="flex justify-end gap-2">
        <div className="relative overflow-hidden rounded-md">
          <div className="h-9 w-24 rounded-md bg-gradient-to-r from-neutral-100 via-neutral-200/60 to-neutral-100 bg-[length:200%_100%] animate-shimmer" />
          <ShimmerOverlay delay={0.9} />
        </div>
        <div className="relative overflow-hidden rounded-md">
          <div className="h-9 w-20 rounded-md bg-gradient-to-r from-neutral-100 via-neutral-200/60 to-neutral-100 bg-[length:200%_100%] animate-shimmer" />
          <ShimmerOverlay delay={1.05} />
        </div>
      </div>
    </TableCell>
  </TableRow>
);

// Version alternative avec animation progressive des lignes
const ProgressiveSkeletonRows = ({ count = 6, onComplete }) => {
  const [visibleRows, setVisibleRows] = useState(0);

  useEffect(() => {
    // Animation progressive ligne par ligne
    const intervals = [];
    for (let i = 0; i < count; i++) {
      const timer = setTimeout(() => {
        setVisibleRows(prev => {
          const newCount = Math.min(prev + 1, count);
          if (newCount === count && onComplete) {
            onComplete();
          }
          return newCount;
        });
      }, i * 80);
      intervals.push(timer);
    }
    return () => intervals.forEach(clearTimeout);
  }, [count, onComplete]);

  return (
    <>
      {SKELETON_ROW_KEYS.slice(0, visibleRows).map((key, index) => (
        <SkeletonRow key={key} isVisible={true} />
      ))}
      {visibleRows < count && visibleRows > 0 && (
        <TableRow>
          <TableCell colSpan={6} className="px-4 py-8 text-center">
            <div className="flex items-center justify-center gap-2">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-neutral-200 border-t-blue-600" />
              <span className="text-sm text-neutral-500">Loading more users...</span>
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
};

// Composant principal AdminUsersSkeleton
const AdminUsersSkeleton = ({ 
  isInitialLoading, 
  variant = 'standard', // 'standard' | 'progressive'
  rows = 6 
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [showProgressive, setShowProgressive] = useState(false);

  useEffect(() => {
    if (!isInitialLoading) {
      setIsVisible(false);
      setShowProgressive(false);
      return;
    }

    // Délai avant d'afficher le skeleton (évite le flash pour les chargements rapides)
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, SKELETON_DELAY_MS);

    return () => clearTimeout(timer);
  }, [isInitialLoading]);

  // Pour la version progressive, attendre que le skeleton soit visible
  useEffect(() => {
    if (isVisible && variant === 'progressive') {
      const timer = setTimeout(() => setShowProgressive(true), 50);
      return () => clearTimeout(timer);
    }
  }, [isVisible, variant]);

  if (!isInitialLoading) return null;

  // Version avec animation progressive ligne par ligne
  if (variant === 'progressive' && showProgressive) {
    return <ProgressiveSkeletonRows count={rows} />;
  }

  // Version standard (toutes les lignes apparaissent ensemble)
  return (
    <>
      {SKELETON_ROW_KEYS.slice(0, rows).map((key) => (
        <SkeletonRow
          key={key}
          isVisible={isVisible}
          className={isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}
        />
      ))}
    </>
  );
};

// Export du composant mémorisé
export default memo(AdminUsersSkeleton);