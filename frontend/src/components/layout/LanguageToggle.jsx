import { useLanguage } from '../../i18n/LanguageContext.jsx';

const LanguageToggle = ({ className = '' }) => {
  const { language, toggleLanguage, t } = useLanguage();
  const isFrench = language === 'fr';

  // Drapeaux SVG intégrés
  const FrenchFlag = ({ className = '' }) => (
    <svg className={className} viewBox="0 0 3 2" xmlns="http://www.w3.org/2000/svg">
      <rect width="1" height="2" fill="#002395"/>
      <rect x="1" width="1" height="2" fill="white"/>
      <rect x="2" width="1" height="2" fill="#ED2939"/>
    </svg>
  );

  const EnglishFlag = ({ className = '' }) => (
    <svg className={className} viewBox="0 0 3 2" xmlns="http://www.w3.org/2000/svg">
      <rect width="3" height="2" fill="#012169"/>
      <path d="M0 0L3 2M3 0L0 2" stroke="white" strokeWidth="0.2"/>
      <path d="M1.5 0V2M0 1H3" stroke="white" strokeWidth="0.2"/>
      <path d="M0 0L3 2M3 0L0 2" stroke="#C8102E" strokeWidth="0.1"/>
      <path d="M1.5 0V2M0 1H3" stroke="#C8102E" strokeWidth="0.1"/>
    </svg>
  );

  return (
    <button
      type="button"
      onClick={toggleLanguage}
      className={[
        'inline-flex h-9 items-center rounded-md transition-all duration-200 hover:scale-105 active:scale-95',
        className,
      ].join(' ')}
      aria-label={`${t('common.language')}: ${isFrench ? 'EN' : 'FR'}`}
      title={`${t('common.language')}: ${isFrench ? 'EN' : 'FR'}`}
    >
      <div className="relative h-7 w-14 rounded-md bg-neutral-200 transition-colors duration-300">
        {/* Curseur */}
        <div
          className={[
            'absolute top-0.5 h-6 w-6 rounded-md bg-white shadow-sm transition-all duration-300 flex items-center justify-center',
            isFrench ? 'left-0.5' : 'left-[calc(100%-1.625rem)]',
          ].join(' ')}
        >
          {isFrench ? (
            <FrenchFlag className="h-3 w-3" />
          ) : (
            <EnglishFlag className="h-3 w-3" />
          )}
        </div>
        
        {/* Drapeaux en arrière-plan */}
        <div className="absolute inset-0 flex items-center justify-between px-2">
          <FrenchFlag className={`h-3 w-3 ${isFrench ? 'opacity-100' : 'opacity-25'}`} />
          <EnglishFlag className={`h-3 w-3 ${!isFrench ? 'opacity-100' : 'opacity-25'}`} />
        </div>
      </div>
    </button>
  );
};

export default LanguageToggle;