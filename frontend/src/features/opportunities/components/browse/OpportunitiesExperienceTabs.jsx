import { Compass, Sparkles } from 'lucide-react';

const TABS = [
  { value: 'for-you', label: 'For You', icon: Sparkles },
  { value: 'explore', label: 'Explore', icon: Compass },
];

const OpportunitiesExperienceTabs = ({ activeTab, isUserAuthenticated, onTabChange }) => {
  if (!isUserAuthenticated) return null;

  return (
    <div className="bg-white">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Centrage avec flex justify-center */}
        <div className="flex items-center justify-center gap-2 py-4" role="tablist" aria-label="Opportunity views">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.value;

            return (
              <button
                key={tab.value}
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() => onTabChange(tab.value)}
                className={[
                  'relative inline-flex cursor-pointer items-center justify-center gap-2 rounded-lg px-5 py-2 text-sm font-medium transition-all duration-200',
                  isActive
                    ? 'text-blue-600'
                    : 'text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700',
                ].join(' ')}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {tab.label}
                
                {/* Soulignement bleu pour l'élément actif */}
                {isActive && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-full" />
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default OpportunitiesExperienceTabs;