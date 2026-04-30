import React from 'react';

export function Spinner({ size = 24, color = '#2563eb', className = '' }) {
  return (
    <span
      className={`inline-flex items-center justify-center ${className}`}
      aria-label="Loading"
      role="status"
    >
      <svg
        className="animate-[spin_1.1s_linear_infinite]"
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
      >
        <circle
          cx="12"
          cy="12"
          r="9"
          stroke="currentColor"
          strokeWidth="3"
          className="text-neutral-200"
        />
        <path
          d="M21 12a9 9 0 0 0-9-9"
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
    </span>
  );
}
