import { createContext, useContext, useState } from 'react';
import { cn } from './utils';

const TabsContext = createContext();

export function Tabs({ defaultValue, value: controlledValue, onValueChange, className, children, ...props }) {
	const [internalValue, setInternalValue] = useState(defaultValue);
	const isControlled = controlledValue !== undefined;
	const activeValue = isControlled ? controlledValue : internalValue;

	const handleValueChange = (newValue) => {
		if (!isControlled) {
			setInternalValue(newValue);
		}
		onValueChange?.(newValue);
	};

	return (
		<TabsContext.Provider value={{ value: activeValue, onValueChange: handleValueChange }}>
			<div className={cn('w-full', className)} data-slot="tabs" {...props}>
				{children}
			</div>
		</TabsContext.Provider>
	);
}

export function TabsList({ className, children, ...props }) {
	return (
		<div
			role="tablist"
			className={cn(
				'inline-flex h-10 items-center justify-center rounded-md bg-neutral-100 p-1 text-neutral-500',
				className
			)}
			data-slot="tabs-list"
			{...props}
		>
			{children}
		</div>
	);
}

export function TabsTrigger({ value, className, children, ...props }) {
	const context = useContext(TabsContext);
	if (!context) {
		throw new Error('TabsTrigger must be used within Tabs');
	}

	const isActive = context.value === value;

	return (
		<button
			type="button"
			role="tab"
			aria-selected={isActive}
			onClick={() => context.onValueChange(value)}
			className={cn(
				'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-white transition-all',
				'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-950 focus-visible:ring-offset-2',
				'disabled:pointer-events-none disabled:opacity-50',
				isActive
					? 'bg-white text-neutral-950 shadow-sm'
					: 'text-neutral-600 hover:text-neutral-900',
				className
			)}
			data-slot="tabs-trigger"
			{...props}
		>
			{children}
		</button>
	);
}

export function TabsContent({ value, className, children, ...props }) {
	const context = useContext(TabsContext);
	if (!context) {
		throw new Error('TabsContent must be used within Tabs');
	}

	if (context.value !== value) {
		return null;
	}

	return (
		<div
			role="tabpanel"
			className={cn(
				'mt-2 ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-950 focus-visible:ring-offset-2',
				className
			)}
			data-slot="tabs-content"
			{...props}
		>
			{children}
		</div>
	);
}
