import { useMemo, useState } from 'react';
import { MapPin, Plus, X } from 'lucide-react';
import { Badge } from '../../../components/ui/badge.jsx';
import { Button } from '../../../components/ui/button.jsx';
import { Input } from '../../../components/ui/input.jsx';
import { Label } from '../../../components/ui/label.jsx';
import {
	TUNISIAN_LOCATION_OPTIONS,
	normalizeLocations,
} from '../profilePreferences.js';
import { normalizeLocationLabel } from '../profileValidation.js';

const locationKey = (value) =>
	String(value || '')
		.trim()
		.replace(/\s+/g, ' ')
		.toLocaleLowerCase();

const LocationMultiSelect = ({
	id,
	label = 'Preferred locations',
	value,
	onChange,
	placeholder = 'Search or add a location',
}) => {
	const selected = normalizeLocations(value);
	const [query, setQuery] = useState('');
	const trimmedQuery = query.trim();

	const suggestions = useMemo(() => {
		const selectedKeys = new Set(selected.map(locationKey));
		const key = locationKey(trimmedQuery);

		return TUNISIAN_LOCATION_OPTIONS.filter((location) => {
			if (selectedKeys.has(locationKey(location))) return false;
			return !key || locationKey(location).includes(key);
		}).slice(0, 6);
	}, [selected, trimmedQuery]);

	const addLocation = (location) => {
		const cleaned = normalizeLocationLabel(location);
		if (!cleaned) return;

		const exists = selected.some((item) => locationKey(item) === locationKey(cleaned));
		if (!exists) {
			onChange([...selected, cleaned]);
		}
		setQuery('');
	};

	const removeLocation = (location) => {
		onChange(selected.filter((item) => item !== location));
	};

	const handleKeyDown = (event) => {
		if (event.key !== 'Enter') return;
		event.preventDefault();
		addLocation(suggestions[0] || trimmedQuery);
	};

	return (
		<div className="space-y-3">
			<Label htmlFor={id}>
				<span className="flex items-center gap-1.5">
					<MapPin className="h-4 w-4 text-neutral-400" aria-hidden="true" />
					{label}
				</span>
			</Label>

			<div className="flex gap-2">
				<Input
					id={id}
					type="text"
					value={query}
					placeholder={placeholder}
					autoComplete="off"
					onChange={(event) => setQuery(event.target.value)}
					onKeyDown={handleKeyDown}
				/>
				<Button
					type="button"
					variant="outline"
					onClick={() => addLocation(trimmedQuery)}
					disabled={!trimmedQuery}
					aria-label="Add location"
				>
					<Plus className="h-4 w-4" aria-hidden="true" />
				</Button>
			</div>

			{suggestions.length > 0 ? (
				<div className="flex flex-wrap gap-2">
					{suggestions.map((location) => (
						<button
							key={location}
							type="button"
							onClick={() => addLocation(location)}
							className="rounded-md border border-neutral-200 bg-white px-2.5 py-1 text-xs font-medium text-neutral-700 transition hover:border-blue-300 hover:text-blue-700"
						>
							{location}
						</button>
					))}
				</div>
			) : null}

			{selected.length > 0 ? (
				<div className="flex flex-wrap gap-2">
					{selected.map((location) => (
						<Badge key={location} variant="secondary" className="py-1.5 pl-3 pr-1">
							{location}
							<button
								type="button"
								onClick={() => removeLocation(location)}
								className="ml-2 rounded-full p-0.5 hover:bg-neutral-200"
								aria-label={`Remove ${location}`}
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

export default LocationMultiSelect;
