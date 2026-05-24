import { useCallback } from 'react';

/**
 * Parse DRF error responses into a normalized structure
 * @param {Object} error - Axios error object
 * @returns {Object} { fieldErrors, nonFieldErrors, message }
 */
export const useApiErrorParser = () => {
  const parseError = useCallback((error) => {
    const response = error?.response;
    const data = response?.data;
    const status = response?.status;

    // Network error (no response from server)
    if (!response) {
      return {
        fieldErrors: {},
        nonFieldErrors: [],
        message: 'Network error. Please check your connection.',
      };
    }

    // 401 Unauthorized
    if (status === 401) {
      return {
        fieldErrors: {},
        nonFieldErrors: ['Unauthorized. Please sign in again.'],
        message: 'Session expired. Please login again.',
      };
    }

    // 403 Forbidden
    if (status === 403) {
      return {
        fieldErrors: {},
        nonFieldErrors: [data?.detail || 'Access denied.'],
        message: data?.detail || 'You do not have permission to perform this action.',
      };
    }

    // 400 Bad Request - DRF validation errors
    if (status === 400) {
      const fieldErrors = {};
      const nonFieldErrors = [];

      // Handle DRF format: { field_name: ["error message"] }
      Object.entries(data).forEach(([key, value]) => {
        const errorMessages = Array.isArray(value) ? value : [value];
        
        if (key === 'non_field_errors' || key === 'detail') {
          nonFieldErrors.push(...errorMessages);
        } else {
          fieldErrors[key] = errorMessages;
        }
      });

      return {
        fieldErrors,
        nonFieldErrors,
        message: nonFieldErrors[0] || Object.values(fieldErrors)[0]?.[0] || 'Validation error.',
      };
    }

    // 500+ Server errors
    if (status >= 500) {
      return {
        fieldErrors: {},
        nonFieldErrors: ['Server error. Please try again later.'],
        message: 'Something went wrong on our end. Please try again.',
      };
    }

    // Fallback for other status codes
    return {
      fieldErrors: {},
      nonFieldErrors: [data?.detail || data?.message || 'An error occurred.'],
      message: data?.detail || 'An unexpected error occurred.',
    };
  }, []);

  return { parseError };
};

export default useApiErrorParser;