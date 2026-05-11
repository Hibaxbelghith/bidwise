import { AlertCircle } from 'lucide-react';

import { Input } from '../../../components/ui/input.jsx';
import { Label } from '../../../components/ui/label.jsx';
import {
	DEFAULT_COMPENSATION_PERIOD,
	buildSalaryHelperText,
	parseSalaryInput,
} from '../profileValidation.js';

const SalaryExpectationInput = ({
	amount,
	period,
	error = '',
	onAmountChange,
}) => {
	const selectedPeriod = period || DEFAULT_COMPENSATION_PERIOD;

	return (
		<div className="space-y-2">
			<Label htmlFor="salaryExpectation">Expected salary (TND / month)</Label>
			<div className="relative">
				<span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-neutral-500">
					TND
				</span>
				<Input
					id="salaryExpectation"
					type="text"
					inputMode="numeric"
					pattern="[0-9]*"
					autoComplete="off"
					placeholder="e.g. 1800"
					className="pl-14 pr-24"
					value={amount ?? ''}
					aria-describedby="salary-helper salary-error"
					aria-invalid={Boolean(error)}
					onChange={(event) => {
						const parsed = parseSalaryInput(event.target.value);
						onAmountChange(parsed === null ? '' : String(parsed));
					}}
				/>
				<span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded-md bg-neutral-100 px-2 py-1 text-xs font-semibold text-neutral-600">
					Monthly
				</span>
			</div>

			<p id="salary-helper" className="text-sm text-neutral-500">
				{buildSalaryHelperText(selectedPeriod)}
			</p>

			{error ? (
				<p id="salary-error" className="flex items-center gap-1.5 text-sm text-red-600" role="alert">
					<AlertCircle className="h-4 w-4" aria-hidden="true" />
					{error}
				</p>
			) : null}
		</div>
	);
};

export default SalaryExpectationInput;
