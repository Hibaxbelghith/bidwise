import { AlertCircle } from 'lucide-react';
import { Input } from '../../../components/ui/input.jsx';
import { Label } from '../../../components/ui/label.jsx';
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '../../../components/ui/select.jsx';
import {
	COMPENSATION_PERIOD_OPTIONS,
	DEFAULT_COMPENSATION_PERIOD,
	buildSalaryHelperText,
	parseSalaryInput,
} from '../profileValidation.js';

const SalaryExpectationInput = ({
	amount,
	period,
	error = '',
	onAmountChange,
	onPeriodChange,
}) => {
	const selectedPeriod = period || DEFAULT_COMPENSATION_PERIOD;

	return (
		<div className="space-y-2">
			<Label htmlFor="salaryExpectation">Expected salary (TND / month)</Label>
			<div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_180px]">
				<div>
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
							className="pl-14"
							value={amount ?? ''}
							aria-describedby="salary-helper salary-error"
							aria-invalid={Boolean(error)}
							onChange={(event) => {
								const parsed = parseSalaryInput(event.target.value);
								onAmountChange(parsed === null ? '' : String(parsed));
							}}
						/>
					</div>
				</div>

				<Select value={selectedPeriod} onValueChange={onPeriodChange}>
					<SelectTrigger aria-label="Salary period">
						<SelectValue placeholder="Period" />
					</SelectTrigger>
					<SelectContent>
						{COMPENSATION_PERIOD_OPTIONS.map((option) => (
							<SelectItem key={option.value} value={option.value}>
								{option.label}
								{option.helper ? ` · ${option.helper}` : ''}
							</SelectItem>
						))}
					</SelectContent>
				</Select>
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
