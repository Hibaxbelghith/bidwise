import PreferenceChipGroup from '../../profile/components/PreferenceChipGroup.jsx';
import { EMPLOYMENT_TYPE_OPTIONS } from '../../profile/profilePreferences.js';

const StepEmploymentType = ({ data, onChange }) => {
	const selected = data.employment_types || [];

	return (
		<div className="space-y-4">
			<PreferenceChipGroup
				options={EMPLOYMENT_TYPE_OPTIONS}
				value={selected}
				onChange={(values) => onChange('employment_types', values)}
			/>

			{selected.length > 0 && (
				<p className="text-xs text-neutral-400">
					{selected.length} selected
				</p>
			)}
		</div>
	);
};

export default StepEmploymentType;
