import { Eye, EyeOff } from 'lucide-react';

const StepVisibility = ({ data, onChange }) => {
	const isVisible = data.profile_visibility !== false;

	return (
		<div className="space-y-4">
			<button
				type="button"
				onClick={() => onChange('profile_visibility', !isVisible)}
				className={`w-full cursor-pointer rounded-lg border p-6 text-left transition-all ${
					isVisible
						? 'border-blue-600 bg-blue-50 ring-2 ring-blue-600/20'
						: 'border-neutral-200 bg-white hover:border-neutral-300'
				}`}
			>
				<div className="flex items-center justify-between gap-4">
					<div className="flex items-center gap-4">
						<div
							className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${
								isVisible
									? 'bg-blue-100 text-blue-600'
									: 'bg-neutral-100 text-neutral-400'
							}`}
						>
							{isVisible ? (
								<Eye className="h-5 w-5" />
							) : (
								<EyeOff className="h-5 w-5" />
							)}
						</div>
						<div>
							<p className="font-medium text-neutral-900">
								Allow recruiters to view my profile
							</p>
							<p className="mt-1 text-sm text-neutral-500">
								{isVisible
									? 'Your profile is visible to recruiters and hiring managers.'
									: 'Your profile is hidden. Only you can see it.'}
							</p>
						</div>
					</div>

					{/* Toggle switch */}
					<div
						className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${
							isVisible ? 'bg-blue-600' : 'bg-neutral-300'
						}`}
					>
						<div
							className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
								isVisible ? 'translate-x-5' : 'translate-x-0.5'
							}`}
						/>
					</div>
				</div>
			</button>
		</div>
	);
};

export default StepVisibility;
