// frontend/src/services/api.js

export const API_BASE_URL = '/api';

export const getHeaders = (includeContentType = true) => {
    const token = localStorage.getItem('token');
    const headers = {};
    if (token && token.trim() !== '' && token !== 'null' && token !== 'undefined') {
        headers['Authorization'] = `Bearer ${token}`;
    }
    if (includeContentType) {
        headers['Content-Type'] = 'application/json';
    }
    return headers;
};

/**
 * Generic API fetch wrapper to handle JSON and throw standardized errors.
 */
export const apiFetch = async (endpoint, options = {}) => {
    const url = `${API_BASE_URL}${endpoint}`;
    
    // Auto-attach standard headers if not provided
    if (!options.headers) {
        const isFormData = options.body instanceof FormData;
        options.headers = getHeaders(!isFormData);
    }

    try {
        const response = await fetch(url, options);
        
        // Handle session expiry or unauthorized status globally
        if (response.status === 401) {
            localStorage.removeItem('user');
            localStorage.removeItem('token');
            if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
                window.location.href = '/login?expired=1';
                return null;
            }
        }
        
        let data;
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            data = await response.json();
        } else {
            data = await response.text();
        }

        if (!response.ok) {
            const errorMsg = data?.message || data?.detail || (typeof data === 'object' ? JSON.stringify(data) : data) || `Request failed with status ${response.status}`;
            throw new Error(errorMsg);
        }

        return data;
    } catch (error) {
        console.error(`API Error on ${url}:`, error);
        throw error;
    }
};
