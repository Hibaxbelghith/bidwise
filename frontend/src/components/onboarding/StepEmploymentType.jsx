const EMPLOYMENT_OPTIONS = [
	{ value: 'FULL_TIME', label: 'Full-time' },
	{ value: 'PART_TIME', label: 'Part-time' },
	{ value: 'CONTRACT', label: 'Contract' },
	{ value: 'FREELANCE', label: 'Freelance' },
	{ value: 'INTERNSHIP', label: 'Internship' },
];

const StepEmploymentType = ({ data, onChange }) => {
	const selected = data.employment_types || [];

	const toggle = (value) => {
		if (selected.includes(value)) {
			onChange('employment_types', selected.filter((v) => v !== value));
		} else {
			onChange('employment_types', [...selected, value]);
		}
	};

	return (
		<div className="space-y-4">
			<div className="flex flex-wrap gap-3">
				{EMPLOYMENT_OPTIONS.map((opt) => {
					const isActive = selected.includes(opt.value);
					return (
						<button
							key={opt.value}
							type="button"
							onClick={() => toggle(opt.value)}
							className={[
								'rounded-full border px-5 py-2.5 text-sm font-medium transition-all',
								isActive
									? 'border-blue-600 bg-blue-600 text-white'
									: 'border-neutral-200 bg-white text-neutral-700 hover:border-neutral-300 hover:bg-neutral-50',
							].join(' ')}
						>
							{opt.label}
						</button>
					);
				})}
			</div>

			{selected.length > 0 && (
				<p className="text-xs text-neutral-400">
					{selected.length} selected
				</p>
			)}
		</div>
	);
};

export default StepEmploymentType;
