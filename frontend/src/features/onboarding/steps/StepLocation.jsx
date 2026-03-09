import { Input } from '../../../components/ui/input.jsx';
import { Label } from '../../../components/ui/label.jsx';
import { MapPin, Building2, Wifi, ArrowLeftRight } from 'lucide-react';

const REMOTE_OPTIONS = [
	{ value: 'ON_SITE', label: 'On-site', description: 'Work from the office', icon: Building2 },
	{ value: 'REMOTE', label: 'Remote', description: 'Work from anywhere', icon: Wifi },
	{ value: 'HYBRID', label: 'Hybrid', description: 'Mix of office and remote', icon: ArrowLeftRight },
];

const StepLocation = ({ data, onChange }) => {
	const selected = data.remote_preference;

	return (
		<div className="space-y-6">
			<div className="space-y-2">
				<Label htmlFor="location">
					<span className="flex items-center gap-1.5">
						<MapPin className="h-4 w-4 text-neutral-400" />
						Preferred location
					</span>
				</Label>
				<Input
					id="location"
					type="text"
					placeholder="e.g. Paris, London, New York"
					value={data.preferred_location || ''}
					onChange={(e) => onChange('preferred_location', e.target.value || null)}
				/>
			</div>

			<div className="space-y-2">
				<Label>Work style</Label>
				<div className="grid grid-cols-3 gap-3">
					{REMOTE_OPTIONS.map((opt) => {
						const isActive = selected === opt.value;
						const Icon = opt.icon;
						return (
							<button
								key={opt.value}
								type="button"
								onClick={() => onChange('remote_preference', isActive ? null : opt.value)}
								className={[
									'flex flex-col items-center gap-1.5 rounded-lg border p-4 text-center transition-all',
									isActive
										? 'border-blue-600 bg-blue-50 text-blue-700 ring-2 ring-blue-600/20'
										: 'border-neutral-200 bg-white text-neutral-700 hover:border-neutral-300 hover:bg-neutral-50',
								].join(' ')}
							>
								<Icon className="h-5 w-5" />
								<span className="text-sm font-medium">{opt.label}</span>
								<span className="text-[11px] leading-tight opacity-60">{opt.description}</span>
							</button>
						);
					})}
				</div>
			</div>
		</div>
	);
};

export default StepLocation;
