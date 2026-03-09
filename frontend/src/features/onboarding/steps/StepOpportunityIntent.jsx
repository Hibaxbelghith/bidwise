import { Briefcase, GraduationCap, BookOpen, TrendingUp } from 'lucide-react';
import { Badge } from '../../../components/ui/badge.jsx';

const OPTIONS = [
	{ value: 'JOB', label: 'Jobs', description: 'Full-time, part-time, and contract positions', icon: Briefcase, enabled: true },
	{ value: 'INTERNSHIP', label: 'Internships', description: 'Internship and trainee programs', icon: GraduationCap, enabled: false },
	{ value: 'RESEARCH', label: 'Research projects', description: 'Academic and R&D opportunities', icon: BookOpen, enabled: false },
	{ value: 'FUNDING', label: 'Funding', description: 'Grants, scholarships, and funding', icon: TrendingUp, enabled: false },
];

const StepOpportunityIntent = ({ data, onChange }) => {
	const selected = data.opportunity_types || [];

	const toggle = (value) => {
		if (selected.includes(value)) {
			onChange('opportunity_types', selected.filter((v) => v !== value));
		} else {
			onChange('opportunity_types', [...selected, value]);
		}
	};

	return (
		<div className="space-y-4">
			<div className="grid grid-cols-2 gap-3">
				{OPTIONS.map((opt) => {
					const isSelected = selected.includes(opt.value);
					const Icon = opt.icon;
					return (
						<button
							key={opt.value}
							type="button"
							disabled={!opt.enabled}
							onClick={() => toggle(opt.value)}
							className={[
								'relative flex flex-col items-center gap-2 rounded-lg border p-5 text-center transition-all',
								opt.enabled
									? isSelected
										? 'border-blue-600 bg-blue-50 text-blue-700 ring-2 ring-blue-600/20'
										: 'border-neutral-200 bg-white text-neutral-700 hover:border-neutral-300 hover:bg-neutral-50'
									: 'cursor-not-allowed border-neutral-100 bg-neutral-50 text-neutral-400',
							].join(' ')}
						>
							{!opt.enabled && (
								<Badge variant="secondary" className="absolute right-2 top-2 text-[10px]">
									Soon
								</Badge>
							)}
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
		</div>
	);
};

export default StepOpportunityIntent;
