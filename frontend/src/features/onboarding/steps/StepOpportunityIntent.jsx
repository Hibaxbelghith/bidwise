import { Briefcase, GraduationCap, Rocket } from 'lucide-react';
import { ONBOARDING_OPPORTUNITY_TYPE_OPTIONS } from '../../profile/profilePreferences.js';

const OPTION_META = {
	JOB: { icon: Briefcase },
	INTERNSHIP: { icon: GraduationCap },
	CALLS_FOR_TENDER: { icon: Rocket },
};

const OPTIONS = ONBOARDING_OPPORTUNITY_TYPE_OPTIONS.map((option) => ({
	...option,
	...(OPTION_META[option.value] || {}),
}));

const StepOpportunityIntent = ({ data, onChange, error = '' }) => {
	const selected = data.opportunity_types || [];

	const isOptionSelected = (option) =>
		option.values.every((value) => selected.includes(value));

	const toggle = (option) => {
		if (isOptionSelected(option)) {
			onChange(
				'opportunity_types',
				selected.filter((value) => !option.values.includes(value))
			);
		} else {
			onChange('opportunity_types', Array.from(new Set([...selected, ...option.values])));
		}
	};

	return (
		<div className="space-y-4">
			<div className="grid grid-cols-2 gap-3 [&>button:last-child]:col-span-2 [&>button:last-child]:mx-auto [&>button:last-child]:w-1/2">
				{OPTIONS.map((opt) => {
					const isSelected = isOptionSelected(opt);
					const Icon = opt.icon || Briefcase;
					return (
						<button
							key={opt.value}
							type="button"
							onClick={() => toggle(opt)}
							className={[
								'relative flex flex-col items-center gap-2 rounded-lg border p-5 text-center transition-all',
								isSelected
									? 'border-blue-600 bg-blue-50 text-blue-700 ring-2 ring-blue-600/20'
									: 'border-neutral-200 bg-white text-neutral-700 hover:border-neutral-300 hover:bg-neutral-50',
							].join(' ')}
						>
							<Icon className="h-6 w-6" />
							<span className="text-sm font-medium">{opt.label}</span>
							<span className="text-xs leading-tight opacity-70">{opt.description}</span>
						</button>
					);
				})}
			</div>
			<p className="text-center text-xs text-neutral-400">
				This helps us personalize your experience.
			</p>
			{error ? (
				<p className="text-sm text-red-600" role="alert">
					{error}
				</p>
			) : null}
		</div>
	);
};

export default StepOpportunityIntent;
