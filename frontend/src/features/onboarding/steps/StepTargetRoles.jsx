import ProfileAutocompleteInput from '../../profile/components/ProfileAutocompleteInput.jsx';

const MAX_ROLES = 5;

const StepTargetRoles = ({ data, onChange, error = '' }) => {
	const roles = Array.isArray(data.target_roles) ? data.target_roles : [];

	return (
		<div className="space-y-3">
			<ProfileAutocompleteInput
				id="role-input"
				label="Target roles"
				termType="role"
				value={roles}
				onChange={(nextRoles) => onChange('target_roles', nextRoles.slice(0, MAX_ROLES))}
				maxItems={MAX_ROLES}
				placeholder="Search Frontend Developer, Data Scientist..."
			/>
			{error ? (
				<p className="text-sm text-red-600" role="alert">
					{error}
				</p>
			) : null}
		</div>
	);
};

export default StepTargetRoles;
