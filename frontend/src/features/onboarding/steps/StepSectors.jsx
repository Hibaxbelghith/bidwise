import BusinessFamilySelect from '../../profile/components/BusinessFamilySelect.jsx';

const StepSectors = ({ data, onChange, error = '' }) => (
	<div className="space-y-4">
		<BusinessFamilySelect
			id="onboardingSectors"
			label="Sectors"
			value={data.domaines_interet || []}
			onChange={(sectors) => onChange('domaines_interet', sectors)}
			maxItems={5}
		/>
		{error ? (
			<p className="text-sm text-red-600" role="alert">
				{error}
			</p>
		) : null}
	</div>
);

export default StepSectors;
