import { Badge } from '../../../../components/ui/badge.jsx';
import { Button } from '../../../../components/ui/button.jsx';

const OpportunitySkillsSection = ({
  skills,
  visibleSkills,
  hiddenSkillsCount,
  showAllSkills,
  onToggleSkills,
}) => (
  <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
    <div className="mb-3 flex items-center justify-between gap-2">
      <h2 className="text-lg font-semibold text-neutral-900">Skills</h2>
      {skills.length > visibleSkills.length ? (
        <Button variant="ghost" size="sm" onClick={onToggleSkills}>
          {showAllSkills ? 'Show less' : `+${hiddenSkillsCount} more`}
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
      <p className="text-sm text-neutral-600">No structured skills provided.</p>
    )}
  </section>
);

export default OpportunitySkillsSection;
