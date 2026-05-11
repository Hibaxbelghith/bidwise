import { useEffect, useMemo, useState } from 'react';
import { Loader2, Plus, X } from 'lucide-react';
import api from '../../../lib/api.js';
import { Badge } from '../../../components/ui/badge.jsx';
import { Button } from '../../../components/ui/button.jsx';
import { Input } from '../../../components/ui/input.jsx';
import { Label } from '../../../components/ui/label.jsx';
import {
	PROFILE_AUTOCOMPLETE_DEBOUNCE_MS,
	canonicalizeInterestLabel,
	canonicalizeSkillLabel,
	isGarbageSkillInput,
	isGarbageTextInput,
	normalizeTermKey,
} from '../profileValidation.js';

const ENDPOINTS = {
	role: '/profile/roles/suggest/',
	skill: '/profile/skills/suggest/',
	interest: '/profile/interests/suggest/',
};

const normalizeItems = (value) => {
	const seen = new Set();
	return (Array.isArray(value) ? value : [])
		.map((item) => String(item || '').trim())
		.filter((item) => {
			const key = normalizeTermKey(item);
			if (!item || seen.has(key)) return false;
			seen.add(key);
			return true;
		});
};

const suggestionValue = (suggestion) => suggestion?.value || suggestion?.label || '';

const ProfileAutocompleteInput = ({
	id,
	label = '', // Valeur par défaut pour éviter undefined
	value = [], // Valeur par défaut pour éviter undefined
	onChange = () => {}, // Fonction par défaut
	termType,
	maxItems = 20,
	placeholder = '',
	emptyText = '',
}) => {
	const [query, setQuery] = useState('');
	const [suggestions, setSuggestions] = useState([]);
	const [isLoading, setIsLoading] = useState(false);
	const [message, setMessage] = useState('');
	const trimmedQuery = query.trim();
	const endpoint = ENDPOINTS[termType];
	const isRole = termType === 'role';
	const isSkill = termType === 'skill';
	const isInterest = termType === 'interest';
	
	const selected = useMemo(
		() => {
			const seen = new Set();
			return normalizeItems(value)
		.map((item) => {
			if (isSkill) return canonicalizeSkillLabel(item);
			if (isInterest) return canonicalizeInterestLabel(item);
			return item;
		})
				.filter((item) => {
					const key = normalizeTermKey(item);
					if (!item || seen.has(key)) return false;
					seen.add(key);
					return true;
				});
		},
		[value, isSkill, isInterest]
	);

	useEffect(() => {
		if (!endpoint || !trimmedQuery) {
			setSuggestions([]);
			setIsLoading(false);
			return undefined;
		}

		const controller = new AbortController();
		const timer = window.setTimeout(async () => {
			setIsLoading(true);
			try {
				const response = await api.get(endpoint, {
					params: { q: trimmedQuery, limit: 6 },
					signal: controller.signal,
				});
				setSuggestions(Array.isArray(response.data?.results) ? response.data.results : []);
			} catch (error) {
				if (error.name !== 'CanceledError' && error.code !== 'ERR_CANCELED') {
					setSuggestions([]);
				}
			} finally {
				if (!controller.signal.aborted) {
					setIsLoading(false);
				}
			}
		}, PROFILE_AUTOCOMPLETE_DEBOUNCE_MS);

		return () => {
			window.clearTimeout(timer);
			controller.abort();
		};
	}, [endpoint, trimmedQuery]);

	const addCanonical = (rawValue) => {
		const canonical = String(rawValue || '').trim().replace(/\s+/g, ' ');
		if (!canonical || selected.length >= maxItems) return false;
		if (isRole && isGarbageTextInput(canonical, 2)) {
			setMessage('Enter a specific job title.');
			return false;
		}
		if (isInterest && isGarbageTextInput(canonical, 2)) {
			setMessage('Enter a recognizable industry or interest.');
			return false;
		}
		if (isSkill && isGarbageSkillInput(canonical)) {
			setMessage('Enter a recognizable skill name.');
			return false;
		}

		const key = normalizeTermKey(canonical);
		if (selected.some((item) => normalizeTermKey(item) === key)) {
			setMessage(`${canonical} is already added.`);
			setQuery('');
			setSuggestions([]);
			return true;
		}

		onChange([...selected, canonical]);
		setQuery('');
		setSuggestions([]);
		setMessage('');
		return true;
	};

	const findPreferredSuggestion = (items) => {
		const queryKey = normalizeTermKey(trimmedQuery);
		const exact = items.find((suggestion) => {
			const valueKey = normalizeTermKey(suggestionValue(suggestion));
			const aliasKeys = Array.isArray(suggestion.aliases)
				? suggestion.aliases.map(normalizeTermKey)
				: [];
			return valueKey === queryKey || aliasKeys.includes(queryKey);
		});
		return exact || items[0] || null;
	};

	const fetchCurrentSuggestions = async (url) => {
		if (!url || !trimmedQuery) return [];
		try {
			const response = await api.get(url, {
				params: { q: trimmedQuery, limit: 6 },
			});
			return Array.isArray(response.data?.results) ? response.data.results : [];
		} catch {
			return [];
		}
	};

	const explainRejectedRole = async () => {
		const skill = findPreferredSuggestion(await fetchCurrentSuggestions(ENDPOINTS.skill));
		const skillLabel = suggestionValue(skill);
		if (skillLabel) {
			setMessage(`${skillLabel} is a skill, not a role.`);
			return;
		}
		setMessage('Choose a role from the suggestions.');
	};

	const addFromInput = async () => {
		if (!trimmedQuery || selected.length >= maxItems) return;

		let preferred = findPreferredSuggestion(suggestions);
		if (!preferred) {
			const freshSuggestions = await fetchCurrentSuggestions(endpoint);
			preferred = findPreferredSuggestion(freshSuggestions);
			setSuggestions(freshSuggestions);
		}

		if (preferred) {
			if (isSkill) {
				addCanonical(canonicalizeSkillLabel(suggestionValue(preferred)));
			} else if (isInterest) {
				addCanonical(canonicalizeInterestLabel(suggestionValue(preferred)));
			} else {
				addCanonical(suggestionValue(preferred));
			}
			return;
		}

		if (isSkill) {
			addCanonical(canonicalizeSkillLabel(trimmedQuery));
		} else if (isInterest) {
			addCanonical(canonicalizeInterestLabel(trimmedQuery));
		} else {
			addCanonical(trimmedQuery);
		}
	};

	const removeItem = (item) => {
		onChange(selected.filter((selectedItem) => selectedItem !== item));
	};

	const handleKeyDown = (event) => {
		if (event.key !== 'Enter') return;
		event.preventDefault();
		addFromInput();
	};

	const canAdd = Boolean(trimmedQuery) && selected.length < maxItems;
	
	// Protection pour label - si undefined ou null, utiliser une chaîne vide
	const safeLabel = label || '';

	return (
		<div className="space-y-3">
			{safeLabel && <Label htmlFor={id}>{safeLabel}</Label>}
			<div className="flex gap-2">
				<div className="relative flex-1">
					<Input
						id={id}
						type="text"
						value={query}
						placeholder={placeholder}
						autoComplete="off"
						onChange={(event) => {
							setQuery(event.target.value);
							setMessage('');
						}}
						onKeyDown={handleKeyDown}
						disabled={selected.length >= maxItems}
					/>
					{isLoading ? (
						<Loader2
							className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-neutral-400"
							aria-hidden="true"
						/>
					) : null}
				</div>
				<Button
					type="button"
					variant="outline"
					onClick={addFromInput}
					disabled={!canAdd}
					aria-label={safeLabel ? `Add ${safeLabel.toLowerCase()}` : 'Add item'}
				>
					<Plus className="h-4 w-4" aria-hidden="true" />
				</Button>
			</div>

			{suggestions.length > 0 ? (
				<div className="flex flex-wrap gap-2">
					{suggestions.map((suggestion) => {
						const value = suggestionValue(suggestion);
						if (!value) return null;
						return (
							<button
								key={`${suggestion.id}-${value}`}
								type="button"
								onClick={() => addCanonical(value)}
								className="rounded-md border border-neutral-200 bg-white px-2.5 py-1 text-xs font-medium text-neutral-700 transition hover:border-blue-300 hover:text-blue-700"
							>
								{value}
							</button>
						);
					})}
				</div>
			) : null}

			{message ? (
				<p className="text-sm text-amber-700" role="status" aria-live="polite">
					{message}
				</p>
			) : null}

			{selected.length > 0 ? (
				<div className="flex flex-wrap gap-2">
					{selected.map((item) => (
						<Badge key={item} variant="secondary" className="py-1.5 pl-3 pr-1">
							{item}
							<button
								type="button"
								onClick={() => removeItem(item)}
								className="ml-2 rounded-full p-0.5 hover:bg-neutral-200"
								aria-label={`Remove ${item}`}
							>
								<X className="h-3 w-3" aria-hidden="true" />
							</button>
						</Badge>
					))}
				</div>
			) : emptyText ? (
				<p className="text-sm italic text-neutral-500">{emptyText}</p>
			) : null}
		</div>
	);
};

export default ProfileAutocompleteInput;
