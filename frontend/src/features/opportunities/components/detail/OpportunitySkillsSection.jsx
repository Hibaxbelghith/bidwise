import { Badge } from '../../../../components/ui/badge.jsx';
import { Button } from '../../../../components/ui/button.jsx';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';

const OpportunitySkillsSection = ({
  skills,
  visibleSkills,
  hiddenSkillsCount,
  showAllSkills,
  onToggleSkills,
  skillsDetectedByAi = false,
}) => {
  const { t } = useLanguage();

  return (
    <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-neutral-900">
          {t('opportunities.detail.skills')}
          {skillsDetectedByAi && (
            <span className="inline-flex items-center gap-1 rounded-full bg-violet-50 px-2 py-0.5 text-[11px] font-medium text-violet-600">
              {t('opportunities.detail.ai')}
            </span>
          )}
        </h2>
        {skills.length > visibleSkills.length ? (
          <Button variant="ghost" size="sm" onClick={onToggleSkills}>
            {showAllSkills
              ? t('opportunities.detail.showLess')
              : t('opportunities.detail.more', { count: hiddenSkillsCount })}
          </Button>
        ) : null}
      </div>

      {visibleSkills.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {visibleSkills.map((skill) => (
            <Badge key={skill} variant="outline" className="bg-white font-medium">
              {skill}
            </Badge>
          ))}
        </div>
      ) : (
        <p className="text-sm text-neutral-600">{t('opportunities.detail.noStructuredSkills')}</p>
      )}
    </section>
  );
};

export default OpportunitySkillsSection;
