// AdminUsersSuspendModal.jsx
import React, { useState, useCallback, useEffect } from 'react';
import { X, AlertCircle } from 'lucide-react';

export const AdminUsersSuspendModal = ({
  isOpen,
  user,
  isLoading = false,
  error,
  onSuspend,
  onClose,
}) => {
  const [reason, setReason] = useState('other');
  const [detail, setDetail] = useState('');
  const [inlineErrors, setInlineErrors] = useState({});

  // Reset form when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setReason('other');
      setDetail('');
      setInlineErrors({});
    }
  }, [isOpen]);

  // Fermer avec Echap
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Merge server errors with client validation errors
  useEffect(() => {
    if (error?.fieldErrors) {
      const serverErrors = {};
      Object.entries(error.fieldErrors).forEach(([key, value]) => {
        // Extract first error message if it's an array
        serverErrors[key] = Array.isArray(value) ? value[0] : value;
      });
      
      setInlineErrors(prevErrors => ({
        ...prevErrors,
        ...serverErrors,
      }));
    }
  }, [error?.fieldErrors]);

  const validateForm = () => {
    const errors = {};
    
    if (reason === 'other' && !detail.trim()) {
      errors.detail = 'Detail is required when reason is "Other".';
    }
    
    setInlineErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    // Clear previous field errors before submit
    setInlineErrors({});
    
    if (!validateForm()) return;
    
    const result = await onSuspend(user, reason, detail.trim());
    
    if (result?.success) {
      setReason('other');
      setDetail('');
      setInlineErrors({});
    }
  };

  const handleClose = () => {
    setInlineErrors({});
    onClose();
  };

  if (!isOpen || !user) return null;

  const REASON_OPTIONS = [
    { value: 'spam', label: 'Spam' },
    { value: 'abuse', label: 'Abuse / Harassment' },
    { value: 'fraud', label: 'Fraud / Scam' },
    { value: 'fake_profile', label: 'Fake Profile' },
    { value: 'other', label: 'Other' },
  ];

  const isDetailRequired = reason === 'other';
  const hasFieldError = Object.keys(inlineErrors).length > 0;
  const hasApiError = error?.nonFieldErrors?.length > 0;

  return (
    <>
      {/* Overlay avec backdrop blur - style moderne */}
      <div
        className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm transition-all duration-200"
        onClick={handleClose}
      />
      
      {/* Modal centré */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="w-full max-w-md transform rounded-xl bg-white shadow-2xl transition-all duration-200"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-neutral-200 px-6 py-4">
            <h2 className="text-lg font-semibold text-neutral-900">
              Suspend User Account
            </h2>
            <button
              onClick={handleClose}
              className="rounded-md p-1 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600"
              disabled={isLoading}
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Body */}
          <div className="p-6">
            {/* User info avec style moderne */}
            <div className="mb-5 rounded-lg bg-amber-50 p-4">
              <div className="flex items-start gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-100">
                  <AlertCircle className="h-4 w-4 text-amber-700" />
                </div>
                <div>
                  <p className="text-sm font-medium text-amber-800">
                    Suspending <span className="font-semibold">{user.email}</span>
                  </p>
                  <p className="mt-1 text-xs text-amber-700">
                    The user will immediately lose access, refresh tokens will be revoked, and this action will be recorded in the audit log.
                  </p>
                </div>
              </div>
            </div>

            {/* API Error (non-field) - displayed as inline warning */}
            {hasApiError && (
              <div className="mb-4 rounded-md bg-red-50 p-3">
                <div className="flex items-start gap-2">
                  <AlertCircle className="mt-0.5 h-4 w-4 text-red-600" />
                  <div>
                    {error.nonFieldErrors.map((err, idx) => (
                      <p key={idx} className="text-sm text-red-700">{err}</p>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Reason select */}
            <div className="mb-4">
              <label className="mb-1.5 block text-sm font-medium text-neutral-700">
                Reason for Suspension
              </label>
              <select
                value={reason}
                onChange={(e) => {
                  setReason(e.target.value);
                  setInlineErrors({});
                }}
                disabled={isLoading}
                className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-neutral-900 transition-colors focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500 disabled:bg-neutral-100"
              >
                {REASON_OPTIONS.map(({ value, label }) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            {/* Detail textarea */}
            <div className="mb-4">
              <label className="mb-1.5 flex items-center text-sm font-medium text-neutral-700">
                Additional Details
                {isDetailRequired && <span className="ml-1 text-red-500">*</span>}
              </label>
              <textarea
                value={detail}
                onChange={(e) => {
                  setDetail(e.target.value);
                  if (inlineErrors.detail) setInlineErrors({});
                }}
                disabled={isLoading}
                placeholder="Provide context for this suspension..."
                maxLength={500}
                rows={3}
                className={`w-full rounded-lg border px-3 py-2 text-neutral-900 placeholder:text-neutral-400 transition-colors focus:outline-none focus:ring-1 disabled:bg-neutral-100 ${
                  inlineErrors.detail
                    ? 'border-red-500 focus:border-red-500 focus:ring-red-500'
                    : 'border-neutral-300 focus:border-red-500 focus:ring-red-500'
                }`}
              />
              <div className="mt-1 flex justify-between">
                <span className="text-xs text-neutral-400">
                  {detail.length}/500
                </span>
                {inlineErrors.detail && (
                  <span className="text-xs text-red-600">{inlineErrors.detail}</span>
                )}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="flex gap-3 border-t border-neutral-200 px-6 py-4">
            <button
              onClick={handleClose}
              disabled={isLoading}
              className="flex-1 rounded-lg bg-neutral-100 px-4 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-200 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={isLoading}
              className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Suspending...
                </span>
              ) : (
                'Suspend User'
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

AdminUsersSuspendModal.displayName = 'AdminUsersSuspendModal';
