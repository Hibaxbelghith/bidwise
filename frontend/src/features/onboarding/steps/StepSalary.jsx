import SalaryExpectationInput from '../../profile/components/SalaryExpectationInput.jsx';
import {
	DEFAULT_COMPENSATION_PERIOD,
	validateSalaryExpectation,
} from '../../profile/profileValidation.js';

const StepSalary = ({ data, onChange }) => {
	const period = data.compensation_period || DEFAULT_COMPENSATION_PERIOD;
	const validation = validateSalaryExpectation(data.compensation_expectation, period);

	return (
		<div className="space-y-4">
			<SalaryExpectationInput
				amount={data.compensation_expectation ?? ''}
				period={period}
				error={validation.error}
				onAmountChange={(value) => onChange('compensation_expectation', value ? Number(value) : null)}
				onPeriodChange={(value) => onChange('compensation_period', value || DEFAULT_COMPENSATION_PERIOD)}
			/>
			<p className="text-xs text-neutral-400">
				Your compensation expectations are private and never shared with employers.
			</p>
		</div>
	);
};

export default StepSalary;
