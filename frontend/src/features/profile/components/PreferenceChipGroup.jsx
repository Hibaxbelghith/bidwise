import { cn } from '../../../components/ui/utils.js';
import { toggleListValue } from '../profilePreferences.js';

const PreferenceChipGroup = ({ options, value, onChange, columns = false }) => {
	const selected = Array.isArray(value) ? value : [];

	return (
		<div className={columns ? 'grid gap-3 sm:grid-cols-3' : 'flex flex-wrap gap-2'}>
			{options.map((option) => {
				const isActive = selected.includes(option.value);
				const Icon = option.icon;

				return (
					<button
						key={option.value}
						type="button"
						aria-pressed={isActive}
						onClick={() => onChange(toggleListValue(selected, option.value))}
						className={cn(
							columns
								? 'flex min-h-24 flex-col items-center justify-center gap-1.5 rounded-lg border p-4 text-center text-sm transition-all'
								: 'rounded-md border px-3 py-2 text-sm font-medium transition-all',
							isActive
								? 'border-blue-600 bg-blue-600 text-white shadow-sm'
								: 'border-neutral-200 bg-white text-neutral-700 hover:border-neutral-300 hover:bg-neutral-50'
						)}
					>
						{Icon ? <Icon className="h-5 w-5" aria-hidden="true" /> : null}
						<span className="font-medium">{option.label}</span>
						{option.description ? (
							<span className={cn('text-[11px] leading-tight', isActive ? 'text-blue-50' : 'text-neutral-500')}>
								{option.description}
							</span>
						) : null}
					</button>
				);
			})}
		</div>
	);
};

export default PreferenceChipGroup;
