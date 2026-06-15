import { Check } from 'lucide-react';
import { Link } from 'react-router-dom';

const pipelineBenefits = [
	'Multi-source Collection',
	'AI Recommendations',
	'Application Assistance',
	'Tracking',
];

const opportunitySources = [
	{
		name: 'LinkedIn',
		src: '/logos_sites_sources/linkedin_logo_icon.webp',
		imageClassName: 'h-full w-full object-cover',
	},
	{
		name: 'Keejob',
		src: '/logos_sites_sources/keejob_logo.jpg',
		imageClassName: 'h-full w-full object-cover',
	},
	{
		name: 'HAICOP - Marches Publics',
		src: '/logos_sites_sources/HAICOP.png',
		imageClassName: 'h-7 w-7 object-contain',
	}
];

const floatingIcons = [
	{ top: '8%', left: '6%', delay: '0s', duration: '20s', color: 'text-blue-500/70', type: 'briefcase' },
	{ top: '18%', left: '82%', delay: '-4s', duration: '22s', color: 'text-indigo-500/70', type: 'resume' },
	{ top: '62%', left: '10%', delay: '-8s', duration: '26s', color: 'text-sky-500/70', type: 'building' },
	{ top: '72%', left: '78%', delay: '-2s', duration: '24s', color: 'text-blue-600/60', type: 'chart' },
	{ top: '35%', left: '88%', delay: '-6s', duration: '28s', color: 'text-indigo-600/60', type: 'badge' },
	{ top: '82%', left: '45%', delay: '-10s', duration: '21s', color: 'text-sky-600/60', type: 'envelope' },
	{ top: '28%', left: '22%', delay: '-12s', duration: '23s', color: 'text-blue-400/70', type: 'search' },
	{ top: '55%', left: '55%', delay: '-5s', duration: '25s', color: 'text-indigo-400/70', type: 'link' },
];

function JobIcon({ type }) {
	const className = 'h-10 w-10 drop-shadow-sm sm:h-12 sm:w-12';
	const commonProps = {
		viewBox: '0 0 24 24',
		fill: 'none',
		stroke: 'currentColor',
		strokeWidth: '1.6',
		className,
		strokeLinecap: 'round',
		strokeLinejoin: 'round',
	};

	switch (type) {
		case 'briefcase':
			return (
				<svg {...commonProps}>
					<rect x="3" y="7" width="18" height="13" rx="2" />
					<path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18" />
				</svg>
			);
		case 'resume':
			return (
				<svg {...commonProps}>
					<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8M8 17h5" />
				</svg>
			);
		case 'building':
			return (
				<svg {...commonProps}>
					<rect x="4" y="3" width="16" height="18" rx="1.5" />
					<path d="M9 8h.01M15 8h.01M9 12h.01M15 12h.01M9 16h.01M15 16h.01" />
				</svg>
			);
		case 'chart':
			return (
				<svg {...commonProps}>
					<path d="M3 3v18h18M7 15l4-4 3 3 5-6" />
				</svg>
			);
		case 'badge':
			return (
				<svg {...commonProps}>
					<circle cx="12" cy="9" r="6" />
					<path d="M8.5 14l-1.5 7 5-3 5 3-1.5-7M9.5 9l2 2 3-3" />
				</svg>
			);
		case 'envelope':
			return (
				<svg {...commonProps}>
					<rect x="3" y="5" width="18" height="14" rx="2" />
					<path d="M3 7l9 7 9-7" />
				</svg>
			);
		case 'search':
			return (
				<svg {...commonProps}>
					<circle cx="11" cy="11" r="7" />
					<path d="M21 21l-4.3-4.3" />
				</svg>
			);
		default:
			return (
				<svg {...commonProps}>
					<path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1" />
				</svg>
			);
	}
}

function HeroBackground() {
	return (
		<div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
			<div className="gradient-shift absolute inset-0" />
			<div
				className="dot-grid absolute inset-0 opacity-60"
				style={{
					maskImage: 'radial-gradient(ellipse at center, black 40%, transparent 75%)',
					WebkitMaskImage: 'radial-gradient(ellipse at center, black 40%, transparent 75%)',
				}}
			/>
			<div className="slow-drift absolute -left-20 -top-24 h-[22rem] w-[22rem] rounded-full bg-blue-400/18 blur-3xl" />
			<div
				className="slow-drift absolute -bottom-24 -right-20 h-[25rem] w-[25rem] rounded-full bg-indigo-400/18 blur-3xl"
				style={{ animationDelay: '-10s', animationDuration: '26s' }}
			/>

			{floatingIcons.map((item) => (
				<div
					key={item.type}
					className={`job-float absolute ${item.color}`}
					style={{
						top: item.top,
						left: item.left,
						animationDelay: item.delay,
						animationDuration: item.duration,
					}}
				>
					<JobIcon type={item.type} />
				</div>
			))}

			<div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-white/80 to-transparent" />
			<div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-white/60 to-transparent" />
		</div>
	);
}

export default function HomeHero() {
	return (
		<section className="home-hero relative min-h-[calc(100svh-4rem)] overflow-hidden bg-gradient-to-b from-white via-[#eef5ff] to-[#dbeafe]">
			<HeroBackground />

			<div className="relative z-10 mx-auto flex min-h-[calc(100svh-4rem)] max-w-6xl flex-col items-center justify-center px-4 py-8 text-center sm:px-6 sm:py-10 lg:px-8">
				<p className="mb-4 text-xs font-extrabold uppercase tracking-[0.2em] text-blue-600 sm:text-sm">
					Multiple sources. One intelligent platform.
				</p>

				<h1 className="max-w-5xl text-4xl font-black leading-[1.05] tracking-tight text-slate-950 sm:text-6xl lg:text-7xl">
					Stop searching everywhere.
					<br />
					<span className="text-blue-600">Find what matters here.</span>
				</h1>

				<div className="mt-9 flex flex-wrap items-center justify-center gap-x-7 gap-y-4 text-base font-semibold text-slate-800 sm:mt-10 sm:gap-x-10 sm:text-lg">
					{pipelineBenefits.map((benefit) => (
						<div key={benefit} className="flex items-center gap-3">
							<span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 border-blue-500 text-blue-600">
								<Check className="h-4 w-4" strokeWidth={2.5} aria-hidden="true" />
							</span>
							<span>{benefit}</span>
						</div>
					))}
				</div>

				<Link
					to="/opportunities"
					className="mt-9 rounded-xl bg-blue-600 px-10 py-4 text-xs font-extrabold uppercase tracking-[0.18em] text-white shadow-xl shadow-blue-600/30 transition hover:-translate-y-0.5 hover:bg-blue-700 sm:mt-10 sm:px-14 sm:text-sm"
				>
					Explore Opportunities
				</Link>

				<div className="mt-10 flex flex-col items-center sm:mt-12">
					<div className="flex -space-x-2" aria-label="Opportunity sources">
						{opportunitySources.map((source) => (
							<div
								key={source.name}
								className="flex h-11 w-11 items-center justify-center overflow-hidden rounded-full border-4 border-white bg-white shadow-sm sm:h-12 sm:w-12"
								title={source.name}
							>
								<img
									src={source.src}
									alt={`${source.name} logo`}
									className={source.imageClassName}
								/>
							</div>
						))}
					</div>
					<p className="mt-3 max-w-xl px-4 text-sm font-medium leading-6 text-slate-700 sm:text-base">
						LinkedIn, Keejob, public tenders and direct organization posts,
						<br className="hidden sm:block" /> all in one place.
					</p>
				</div>
			</div>
		</section>
	);
}
