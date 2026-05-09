import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from '../../../components/ui/card.jsx';
import { cn } from '../../../components/ui/utils.js';

const ProfileSection = ({
	title,
	description,
	defaultOpen = true,
	children,
	actions = null,
}) => {
	const [isOpen, setIsOpen] = useState(defaultOpen);
	const contentId = `${title.toLocaleLowerCase().replace(/[^a-z0-9]+/g, '-')}-section`;

	return (
		<Card>
			<CardHeader className="gap-3 sm:flex-row sm:items-start sm:justify-between">
				<button
					type="button"
					className="flex flex-1 items-start justify-between gap-4 text-left"
					aria-expanded={isOpen}
					aria-controls={contentId}
					onClick={() => setIsOpen((value) => !value)}
				>
					<div>
						<CardTitle>{title}</CardTitle>
						{description ? (
							<CardDescription>{description}</CardDescription>
						) : null}
					</div>
					<ChevronDown
						className={cn(
							'mt-1 h-5 w-5 shrink-0 text-neutral-400 transition-transform',
							isOpen ? 'rotate-180' : ''
						)}
						aria-hidden="true"
					/>
				</button>
				{actions}
			</CardHeader>
			{isOpen ? (
				<CardContent id={contentId} className="space-y-5">
					{children}
				</CardContent>
			) : null}
		</Card>
	);
};

export default ProfileSection;
