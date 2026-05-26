import { Children, isValidElement } from 'react';
import { cn } from './utils.js';

export const Select = ({ value, defaultValue, onValueChange, children }) => {
  let triggerProps = {};
  let placeholder = '';
  const items = [];

  Children.forEach(children, (child) => {
    if (!isValidElement(child)) return;

    if (child.type === SelectTrigger) {
      triggerProps = child.props || {};
      const triggerChildren = Children.toArray(child.props.children);
      triggerChildren.forEach((triggerChild) => {
        if (isValidElement(triggerChild) && triggerChild.type === SelectValue) {
          placeholder = triggerChild.props?.placeholder || '';
        }
      });
    }

    if (child.type === SelectContent) {
      const contentChildren = Children.toArray(child.props.children);
      contentChildren.forEach((contentChild) => {
        if (isValidElement(contentChild) && contentChild.type === SelectItem) {
          items.push({
            value: contentChild.props.value,
            label: contentChild.props.children,
          });
        }
      });
    }
  });

  return (
    <div className="relative">
      <select
        className={cn(
          'h-10 w-full rounded-md border border-neutral-200 bg-white px-3 text-sm text-neutral-900 ' +
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
          triggerProps.className
        )}
        id={triggerProps.id}
        disabled={triggerProps.disabled}
        aria-label={triggerProps['aria-label']}
        value={value}
        defaultValue={defaultValue}
        onChange={(event) => onValueChange?.(event.target.value)}
      >
        {placeholder ? (
          <option value="" disabled hidden>
            {placeholder}
          </option>
        ) : null}
        {items.map((item) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
      </select>
    </div>
  );
};

export const SelectTrigger = ({ children }) => children;
export const SelectValue = () => null;
export const SelectContent = () => null;
export const SelectItem = () => null;
