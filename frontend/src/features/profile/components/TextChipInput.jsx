import { useState } from 'react';
import { Plus, X } from 'lucide-react';
import { Badge } from '../../../components/ui/badge.jsx';
import { Button } from '../../../components/ui/button.jsx';
import { Input } from '../../../components/ui/input.jsx';
import { Label } from '../../../components/ui/label.jsx';
import { normalizeTermKey } from '../profileValidation.js';

const TextChipInput = ({
	id,
	label,
	value,
	onChange,
	placeholder = '',
	emptyText = '',
	maxItems = 20,
}) => {
	const selected = Array.isArray(value) ? value : [];
	const [input, setInput] = useState('');
	const [message, setMessage] = useState('');

	const addItem = () => {
		const text = input.trim().replace(/\s+/g, ' ');
		const key = normalizeTermKey(text);
		if (!text || selected.length >= maxItems) return;
		if (selected.some((item) => normalizeTermKey(item) === key)) {
			setMessage(`${text} is already added.`);
			setInput('');
			return;
		}
		onChange([...selected, text]);
		setInput('');
		setMessage('');
	};

	const removeItem = (item) => {
		onChange(selected.filter((selectedItem) => selectedItem !== item));
	};

	return (
		<div className="space-y-3">
			<Label htmlFor={id}>{label}</Label>
			<div className="flex gap-2">
				<Input
					id={id}
					type="text"
					value={input}
					placeholder={placeholder}
					onChange={(event) => {
						setInput(event.target.value);
						setMessage('');
					}}
					onKeyDown={(event) => {
						if (event.key === 'Enter') {
							event.preventDefault();
							addItem();
						}
					}}
				/>
				<Button
					type="button"
					variant="outline"
					onClick={addItem}
					disabled={!input.trim() || selected.length >= maxItems}
					aria-label={`Add ${label.toLocaleLowerCase()}`}
				>
					<Plus className="h-4 w-4" aria-hidden="true" />
				</Button>
			</div>
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

export default TextChipInput;
