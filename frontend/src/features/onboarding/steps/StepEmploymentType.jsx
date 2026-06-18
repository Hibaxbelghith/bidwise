import PreferenceChipGroup from '../../profile/components/PreferenceChipGroup.jsx';
import { getEmploymentTypeOptionsForOpportunityTypes } from '../../profile/profilePreferences.js';

const StepEmploymentType = ({ data, onChange, error = '' }) => {
	const selected = data.employment_types || [];
	const options = getEmploymentTypeOptionsForOpportunityTypes(data.opportunity_types);
	const visibleValues = new Set(options.map((option) => option.value));
	const visibleSelected = selected.filter((value) => visibleValues.has(value));

	return (
		<div className="space-y-4">
			<PreferenceChipGroup
				options={options}
				value={visibleSelected}
				onChange={(values) => onChange('employment_types', values)}
			/>

			{visibleSelected.length > 0 && (
				<p className="text-xs text-neutral-400">
					{visibleSelected.length} selected
				</p>
			)}

			{error ? (
				<p className="text-sm text-red-600" role="alert">
					{error}
				</p>
			) : null}
		</div>
	);
};

export default StepEmploymentType;
