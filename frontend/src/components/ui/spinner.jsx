// Modern Spinner component
import React from "react";

export function Spinner({ size = 24, color = "#2563eb", className = "" }) {
  return (
    <span
      className={`inline-block animate-spin rounded-full border-2 border-solid border-blue-300 border-t-[${color}] ${className}`}
      style={{ width: size, height: size, borderTopColor: color }}
      aria-label="Loading"
      role="status"
    />
  );
}
