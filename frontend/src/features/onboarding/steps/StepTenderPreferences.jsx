import { Label } from '../../../components/ui/label.jsx';
import { Input } from '../../../components/ui/input.jsx';
import { TENDER_CATEGORY_OPTIONS } from '../../profile/profilePreferences.js';

const getFirstCategory = (data) => {
	const categories = data?.tender_preferences?.categories;
	return Array.isArray(categories) && categories.length ? categories[0] : { category: '', subcategory: '' };
};

const StepTenderPreferences = ({ data, onChange, error = '' }) => {
	const selected = getFirstCategory(data);
	const selectedCategory = TENDER_CATEGORY_OPTIONS.find((option) => option.value === selected.category);
	const subcategories = selectedCategory?.subcategories || [];
	const maxBudget = data?.tender_preferences?.max_budget ?? '';

	const updatePreferences = (nextCategory) => {
		onChange('tender_preferences', {
			categories: nextCategory.category ? [nextCategory] : [],
			max_budget: maxBudget === '' ? null : maxBudget,
		});
	};

	const updateBudget = (value) => {
		onChange('tender_preferences', {
			categories: selected.category ? [selected] : [],
			max_budget: value === '' ? null : value,
		});
	};

	return (
		<div className="space-y-5">
			<div className="space-y-2">
				<Label htmlFor="tenderCategory">Tender category</Label>
				<select
					id="tenderCategory"
					value={selected.category}
					onChange={(event) => updatePreferences({ category: event.target.value, subcategory: '' })}
					className="h-11 w-full rounded-md border border-neutral-200 bg-white px-3 text-sm text-neutral-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
				>
					<option value="">Select a category</option>
					{TENDER_CATEGORY_OPTIONS.map((option) => (
						<option key={option.value} value={option.value}>
							{option.label}
						</option>
					))}
				</select>
			</div>

			{selected.category && selected.category !== 'Autre' ? (
				<div className="space-y-2">
					<Label htmlFor="tenderSubcategory">Subcategory</Label>
					<select
						id="tenderSubcategory"
						value={selected.subcategory}
						onChange={(event) => updatePreferences({ category: selected.category, subcategory: event.target.value })}
						className="h-11 w-full rounded-md border border-neutral-200 bg-white px-3 text-sm text-neutral-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
					>
						<option value="">Select a subcategory</option>
						{subcategories.map((option) => (
							<option key={option.value} value={option.value}>
								{option.label}
							</option>
						))}
					</select>
				</div>
			) : null}

			<div className="space-y-2">
				<Label htmlFor="tenderMaxBudget">Maximum caution budget, TND</Label>
				<Input
					id="tenderMaxBudget"
					type="number"
					min="0"
					inputMode="numeric"
					value={maxBudget}
					onChange={(event) => updateBudget(event.target.value)}
					placeholder="Optional"
				/>
			</div>

			{error ? (
				<p className="text-sm text-red-600" role="alert">
					{error}
				</p>
			) : null}
		</div>
	);
};

export default StepTenderPreferences;
