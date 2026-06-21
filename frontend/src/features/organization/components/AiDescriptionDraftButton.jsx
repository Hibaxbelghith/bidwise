import { Loader2, Sparkles } from 'lucide-react';
import { useState } from 'react';

import { Button } from '../../../components/ui/button.jsx';
import { generateOrganizationDescriptionDraft } from '../services/organizationService.js';

const normalizeSkills = (skills) => (
  Array.isArray(skills)
    ? skills
    : String(skills || '').split(',').map((skill) => skill.trim()).filter(Boolean)
);

const AiDescriptionDraftButton = ({
  type,
  title,
  contract = '',
  workMode = '',
  location = '',
  skills = [],
  minExperience = null,
  maxExperience = null,
  educationLevel = '',
  salary = '',
  deadline = '',
  currentDescription = '',
  onApply,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [draftInserted, setDraftInserted] = useState(false);
  const canGenerate = String(title || '').trim().length >= 5 && !loading;

  const handleGenerate = async () => {
    setError('');
    setLoading(true);
    try {
      const data = await generateOrganizationDescriptionDraft({
        type,
        title,
        contract,
        work_mode: workMode,
        location,
        skills: normalizeSkills(skills),
        min_experience: minExperience ?? null,
        max_experience: maxExperience ?? null,
        education_level: educationLevel,
        salary,
        deadline,
      });

      if (currentDescription && currentDescription.trim().length > 0) {
        const confirmed = window.confirm('Replace the current description with the AI draft?');
        if (!confirmed) return;
      }

      onApply?.(data.description);
      setDraftInserted(true);
    } catch {
      setError('AI suggestion unavailable. You can write it manually.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-end">
      <Button
        type="button"
        variant="outline"
        className="h-9 rounded-xl border-blue-200 bg-white px-3 text-sm font-semibold text-blue-700 hover:border-blue-300 hover:bg-blue-50"
        onClick={handleGenerate}
        disabled={!canGenerate}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 bidwise-force-spin" aria-hidden="true" />
        ) : (
          <Sparkles className="h-4 w-4" aria-hidden="true" />
        )}
        {loading ? 'Generating...' : 'Generate with AI'}
      </Button>
      {draftInserted && !error ? (
        <p className="mt-2 max-w-xs text-right text-xs text-neutral-500">
          AI-generated suggestion. Please review before publishing.
        </p>
      ) : null}
      {error ? (
        <p className="mt-2 max-w-xs text-right text-sm text-amber-700">{error}</p>
      ) : null}
    </div>
  );
};

export default AiDescriptionDraftButton;
