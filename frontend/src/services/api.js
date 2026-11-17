// frontend/src/services/api.js

export const API_BASE_URL = '/api';

export const getHeaders = (includeContentType = true) => {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
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
 * Generic API fetch wrapper to handle JSON and throw standardized errors,
 * with automatic silent token refresh on 401 responses.
 */
export const apiFetch = async (endpoint, options = {}) => {
    const url = `${API_BASE_URL}${endpoint}`;
    
    // Auto-attach standard headers if not provided
    if (!options.headers) {
        const isFormData = options.body instanceof FormData;
        options.headers = getHeaders(!isFormData);
    }

    try {
        let response = await fetch(url, options);
        
        // Handle session expiry and attempt silent refresh
        if (response.status === 401 && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh') && !endpoint.includes('/auth/logout')) {
            const refreshToken = localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');
            if (refreshToken) {
                try {
                    const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ refresh_token: refreshToken })
                    });
                    if (refreshRes.ok) {
                        const refreshData = await refreshRes.json();
                        const isLocal = Boolean(localStorage.getItem('token'));
                        const storage = isLocal ? localStorage : sessionStorage;
                        storage.setItem('token', refreshData.access_token);
                        if (refreshData.refresh_token) {
                            storage.setItem('refresh_token', refreshData.refresh_token);
                        }
                        // Retry request with fresh access token
                        const isFormData = options.body instanceof FormData;
                        const retryHeaders = getHeaders(!isFormData);
                        options.headers = { ...options.headers, ...retryHeaders };
                        response = await fetch(url, options);
                    } else {
                        // Refresh token expired or revoked -> clear session
                        localStorage.clear();
                        sessionStorage.clear();
                        if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
                            window.location.href = '/login?expired=1';
                            return null;
                        }
                    }
                } catch (refreshErr) {
                    console.error("Token refresh attempt error:", refreshErr);
                }
            } else {
                localStorage.clear();
                sessionStorage.clear();
                if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
                    window.location.href = '/login?expired=1';
                    return null;
                }
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
