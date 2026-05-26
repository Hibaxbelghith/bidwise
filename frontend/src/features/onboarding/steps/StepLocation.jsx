import { Label } from '../../../components/ui/label.jsx';
import { Building2, Wifi, ArrowLeftRight } from 'lucide-react';
import LocationMultiSelect from '../../profile/components/LocationMultiSelect.jsx';
import PreferenceChipGroup from '../../profile/components/PreferenceChipGroup.jsx';
import { WORK_MODE_OPTIONS } from '../../profile/profilePreferences.js';

const WORK_MODE_STEP_OPTIONS = WORK_MODE_OPTIONS.map((option) => ({
	...option,
	description:
		option.value === 'REMOTE'
			? 'Work from anywhere'
			: option.value === 'HYBRID'
				? 'Mix of office and remote'
				: 'Work from the office',
	icon:
		option.value === 'REMOTE'
			? Wifi
			: option.value === 'HYBRID'
				? ArrowLeftRight
				: Building2,
}));

const StepLocation = ({ data, onChange, error = '' }) => {
	const selectedModes = Array.isArray(data.work_mode_preferences)
		? data.work_mode_preferences
		: [];
	const locationRequired = selectedModes.some((mode) => mode === 'ON_SITE' || mode === 'HYBRID');

	return (
		<div className="space-y-6">
			<LocationMultiSelect
				id="preferredLocations"
				value={data.preferred_locations}
				onChange={(locations) => onChange('preferred_locations', locations)}
				placeholder={locationRequired ? 'Search Tunis, Sfax, Sousse...' : 'Optional for remote roles'}
				maxItems={10}
			/>
			<p className="text-xs text-neutral-500">
				{locationRequired
					? 'Location is required for on-site or hybrid work.'
					: 'Location is optional when you are open to remote work.'}
			</p>

			<div className="space-y-2">
				<Label>Work style</Label>
				<PreferenceChipGroup
					options={WORK_MODE_STEP_OPTIONS}
					value={data.work_mode_preferences}
					onChange={(modes) => onChange('work_mode_preferences', modes)}
					columns
				/>
				{error ? (
					<p className="text-sm text-red-600" role="alert">
						{error}
					</p>
				) : null}
			</div>
		</div>
	);
};

export default StepLocation;
