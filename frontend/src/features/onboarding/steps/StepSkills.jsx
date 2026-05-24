import ProfileAutocompleteInput from '../../profile/components/ProfileAutocompleteInput.jsx';

const StepSkills = ({ data, onChange, error = '' }) => (
	<div className="space-y-4">
		<ProfileAutocompleteInput
			id="onboardingSkills"
			label="What are your top skills?"
			termType="skill"
			value={data.competences || []}
			onChange={(skills) => onChange('competences', skills)}
			placeholder="Python, React, Django..."
			emptyText="Add at least one skill to improve your recommendations."
		/>
		{error ? (
			<p className="text-sm text-red-600" role="alert">
				{error}
			</p>
		) : null}
	</div>
);

export default StepSkills;
