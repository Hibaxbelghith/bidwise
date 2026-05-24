import {
	DEFAULT_COMPENSATION_PERIOD,
	validateSalaryRange,
} from '../../profile/profileValidation.js';
import { Input } from '../../../components/ui/input.jsx';
import { Label } from '../../../components/ui/label.jsx';

const StepSalary = ({ data, onChange }) => {
	const period = data.compensation_period || DEFAULT_COMPENSATION_PERIOD;
	const validation = validateSalaryRange(
		data.compensation_min_expectation,
		data.compensation_max_expectation,
		period
	);

	return (
		<div className="space-y-4">
			<div className="space-y-2">
				<Label>Expected salary range</Label>
				<div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
					<Input
						type="number"
						inputMode="numeric"
						min="0"
						placeholder="Min"
						value={data.compensation_min_expectation ?? ''}
						onChange={(event) =>
							onChange('compensation_min_expectation', event.target.value ? Number(event.target.value) : null)
						}
						aria-label="Minimum expected salary"
					/>
					<span className="text-sm text-neutral-400">-</span>
					<Input
						type="number"
						inputMode="numeric"
						min="0"
						placeholder="Max"
						value={data.compensation_max_expectation ?? ''}
						onChange={(event) =>
							onChange('compensation_max_expectation', event.target.value ? Number(event.target.value) : null)
						}
						aria-label="Maximum expected salary"
					/>
				</div>
				<p className="text-sm text-neutral-500">TND/month. Optional.</p>
				{validation.error ? (
					<p className="text-sm text-red-600" role="alert">
						{validation.error}
					</p>
				) : null}
			</div>
			<p className="text-xs text-neutral-400">
				Your compensation expectations are private and never shared with employers.
			</p>
		</div>
	);
};

export default StepSalary;
