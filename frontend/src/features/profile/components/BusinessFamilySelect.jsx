import { X } from 'lucide-react';
import { useMemo } from 'react';

import { Badge } from '../../../components/ui/badge.jsx';
import { Label } from '../../../components/ui/label.jsx';
import { cn } from '../../../components/ui/utils.js';
import {
	BUSINESS_FAMILY_OPTIONS,
	normalizeBusinessFamilyValues,
} from '../profilePreferences.js';

const GROUP_ORDER = [
	'Technology',
	'Business',
	'Operations',
	'Creative',
	'Regulated Services',
	'Other',
];

const BusinessFamilySelect = ({
	id = 'businessFamilies',
	label = 'Sectors',
	value = [],
	onChange,
	maxItems = 5,
}) => {
	const selected = normalizeBusinessFamilyValues(value);
	const selectedSet = new Set(selected);

	const selectedOptions = useMemo(
		() => selected
			.map((item) => BUSINESS_FAMILY_OPTIONS.find((option) => option.value === item))
			.filter(Boolean),
		[selected]
	);

	const availableOptions = useMemo(
		() => BUSINESS_FAMILY_OPTIONS.filter((option) => !selectedSet.has(option.value)),
		[selected]
	);

	const groupedAvailableOptions = useMemo(() => {
		const groups = new Map(GROUP_ORDER.map((group) => [group, []]));
		for (const option of availableOptions) {
			const group = groups.has(option.group) ? option.group : 'Other';
			groups.get(group).push(option);
		}
		return [...groups.entries()].filter(([, options]) => options.length > 0);
	}, [availableOptions]);

	const addFamily = (family) => {
		if (!family || selectedSet.has(family) || selected.length >= maxItems) return;
		onChange([...selected, family]);
	};

	const removeFamily = (family) => {
		onChange(selected.filter((item) => item !== family));
	};

	const isSelectionDisabled = selected.length >= maxItems || availableOptions.length === 0;

	return (
		<div className="space-y-3">
			<div className="flex items-start justify-between gap-3">
				<div>
					<Label htmlFor={id}>{label}</Label>
					<p className="mt-1 text-xs text-neutral-500">
						Choose up to {maxItems} professional domains used by the AI matching engine.
					</p>
				</div>
				<span className="shrink-0 text-xs font-medium text-neutral-500">
					{selected.length}/{maxItems}
				</span>
			</div>

			<select
				id={id}
				value=""
				disabled={isSelectionDisabled}
				onChange={(event) => addFamily(event.target.value)}
				className={cn(
					'h-11 w-full rounded-md border border-neutral-200 bg-white px-3 text-sm text-neutral-900',
					'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
					isSelectionDisabled ? 'cursor-not-allowed opacity-60' : ''
				)}
			>
				<option value="" disabled>
					Add a professional domain
				</option>
				{groupedAvailableOptions.map(([group, options]) => (
					<optgroup key={group} label={group}>
						{options.map((option) => (
							<option key={option.value} value={option.value}>
								{option.label}
							</option>
						))}
					</optgroup>
				))}
			</select>

			{selectedOptions.length > 0 ? (
				<div className="flex flex-wrap gap-2">
					{selectedOptions.map((option) => (
						<Badge key={option.value} variant="secondary" className="py-1.5 pl-3 pr-1">
							{option.label}
							<button
								type="button"
								onClick={() => removeFamily(option.value)}
								className="ml-2 rounded-full p-0.5 hover:bg-neutral-200"
								aria-label={`Remove ${option.label}`}
							>
								<X className="h-3 w-3" aria-hidden="true" />
							</button>
						</Badge>
					))}
				</div>
			) : null}
		</div>
	);
};

export default BusinessFamilySelect;
