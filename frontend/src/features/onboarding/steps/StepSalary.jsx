import { Input } from '../../../components/ui/input.jsx';
import { Label } from '../../../components/ui/label.jsx';
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '../../../components/ui/select.jsx';

const PERIOD_OPTIONS = [
	{ value: 'YEARLY', label: 'per year' },
	{ value: 'MONTHLY', label: 'per month' },
	{ value: 'HOURLY', label: 'per hour' },
];

const StepSalary = ({ data, onChange }) => {
	const amount = data.compensation_expectation;
	const period = data.compensation_period || '';

	return (
		<div className="space-y-6">
			<div className="space-y-2">
				<Label htmlFor="salary">Desired minimum compensation</Label>
				<div className="flex gap-3">
					<div className="relative flex-1">
						<span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-neutral-400">
							$
						</span>
						<Input
							id="salary"
							type="number"
							min={0}
							placeholder="e.g. 55000"
							className="pl-7"
							value={amount != null ? amount : ''}
							onChange={(e) => {
								const val = e.target.value;
								onChange('compensation_expectation', val ? parseInt(val, 10) : null);
							}}
						/>
					</div>
					<div className="w-36">
						<Select
							value={period}
							onValueChange={(val) => onChange('compensation_period', val || null)}
						>
							<SelectTrigger>
								<SelectValue placeholder="Period" />
							</SelectTrigger>
							<SelectContent>
								{PERIOD_OPTIONS.map((opt) => (
									<SelectItem key={opt.value} value={opt.value}>
										{opt.label}
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					</div>
				</div>
			</div>

			<p className="text-xs text-neutral-400">
				Your compensation expectations are private and never shared with employers.
			</p>
		</div>
	);
};

export default StepSalary;
