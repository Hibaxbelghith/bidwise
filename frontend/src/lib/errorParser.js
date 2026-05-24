/**
 * Parse DRF API error responses into a normalized structure
 * 
 * DRF error format:
 * {
 *   "fieldName": ["error message 1", "error message 2"],
 *   "anotherField": ["error message"],
 *   "non_field_errors": ["global error"]
 * }
 * 
 * @param {Object} errorResponse - The error.response.data from axios
 * @returns {Object} Normalized error structure
 */
export const parseDRFErrors = (errorResponse) => {
  if (!errorResponse || typeof errorResponse !== 'object') {
    return {
      fieldErrors: {},
      nonFieldErrors: [],
      message: 'An error occurred',
    };
  }

  const fieldErrors = {};
  const nonFieldErrors = [];
  let message = null;

  // Special handling for DRF error structure
  Object.entries(errorResponse).forEach(([key, value]) => {
    // Handle non-field errors
    if (key === 'non_field_errors') {
      nonFieldErrors.push(...(Array.isArray(value) ? value : [value]));
      return;
    }

    // Handle detail field (often used for general messages)
    if (key === 'detail' && !Array.isArray(value)) {
      message = value;
      return;
    }

    // Handle field errors
    if (Array.isArray(value)) {
      // Take the first error message for field errors
      if (value.length > 0) {
        fieldErrors[key] = value[0];
      }
    } else if (typeof value === 'string') {
      fieldErrors[key] = value;
    }
  });

  return {
    fieldErrors,
    nonFieldErrors,
    message: message || (nonFieldErrors.length > 0 ? nonFieldErrors[0] : null),
  };
};

/**
 * Get error message from axios error response
 * Returns structured error object for proper handling
 * 
 * @param {Object} axiosError - Error from axios
 * @returns {Object} Parsed error structure
 */
export const getErrorFromResponse = (axiosError) => {
  const status = axiosError?.response?.status;
  const data = axiosError?.response?.data;

  // Handle 400 validation errors
  if (status === 400) {
    return {
      type: 'validation',
      ...parseDRFErrors(data),
    };
  }

  // Handle 403 permission/business logic errors
  if (status === 403) {
    return {
      type: 'action_blocked',
      fieldErrors: {},
      nonFieldErrors: [],
      message: data?.detail || 'Access denied',
    };
  }

  // Handle 401 auth errors
  if (status === 401) {
    return {
      type: 'auth',
      fieldErrors: {},
      nonFieldErrors: [],
      message: 'Unauthorized. Please sign in again.',
    };
  }

  // Handle server errors
  if (status >= 500) {
    return {
      type: 'server',
      fieldErrors: {},
      nonFieldErrors: [],
      message: 'Server error. Please try again.',
    };
  }

  // Handle network errors
  if (!status && axiosError?.request) {
    return {
      type: 'network',
      fieldErrors: {},
      nonFieldErrors: [],
      message: 'Network error. Please check your connection.',
    };
  }

  // Generic fallback
  return {
    type: 'unknown',
    fieldErrors: {},
    nonFieldErrors: [],
    message: data?.detail || 'An error occurred',
  };
};
