import { useState } from 'react';
import { Input } from '../ui/input.jsx';
import { Label } from '../ui/label.jsx';
import { Badge } from '../ui/badge.jsx';
import { Button } from '../ui/button.jsx';
import { Plus, X } from 'lucide-react';

const MAX_ROLES = 5;

const StepTargetRoles = ({ data, onChange }) => {
	const [input, setInput] = useState('');
	const roles = data.target_roles || [];

	const addRole = () => {
		const trimmed = input.trim();
		if (!trimmed || roles.length >= MAX_ROLES || roles.includes(trimmed)) return;
		onChange('target_roles', [...roles, trimmed]);
		setInput('');
	};

	const removeRole = (index) => {
		onChange('target_roles', roles.filter((_, i) => i !== index));
	};

	const handleKeyDown = (e) => {
		if (e.key === 'Enter') {
			e.preventDefault();
			addRole();
		}
	};

	return (
		<div className="space-y-4">
			<div className="space-y-2">
				<Label htmlFor="role-input">Add a target role</Label>
				<div className="flex gap-2">
					<Input
						id="role-input"
						type="text"
						placeholder="e.g. Frontend Developer, Data Scientist"
						value={input}
						onChange={(e) => setInput(e.target.value)}
						onKeyDown={handleKeyDown}
						disabled={roles.length >= MAX_ROLES}
					/>
					<Button
						type="button"
						variant="outline"
						onClick={addRole}
						disabled={!input.trim() || roles.length >= MAX_ROLES}
					>
						<Plus className="h-4 w-4" />
					</Button>
				</div>
			</div>

			{roles.length > 0 && (
				<div className="flex flex-wrap gap-2">
					{roles.map((role, i) => (
						<Badge
							key={i}
							variant="secondary"
							className="inline-flex items-center gap-1.5 py-1.5 pl-3 pr-2 text-sm"
						>
							{role}
							<button
								type="button"
								onClick={() => removeRole(i)}
								className="rounded-full p-0.5 hover:bg-neutral-300/50"
							>
								<X className="h-3 w-3" />
							</button>
						</Badge>
					))}
				</div>
			)}

			<p className="text-xs text-neutral-400">
				{roles.length}/{MAX_ROLES} roles — press Enter or click + to add
			</p>
		</div>
	);
};

export default StepTargetRoles;
