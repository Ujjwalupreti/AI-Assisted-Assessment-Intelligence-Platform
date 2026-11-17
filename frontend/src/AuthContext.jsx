import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    try {
      const storedUser = localStorage.getItem('user') || sessionStorage.getItem('user');
      const storedToken = localStorage.getItem('token') || sessionStorage.getItem('token');
      
      if (storedUser && storedToken && storedToken.trim() !== '' && storedToken !== 'null' && storedToken !== 'undefined') {
        const parsed = JSON.parse(storedUser);
        if (typeof parsed === 'object' && parsed !== null && parsed.role) {
          return parsed;
        }
      }
    } catch (e) {
      console.warn("Failed to parse initial user session:", e);
    }
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    sessionStorage.removeItem('user');
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('refresh_token');
    return null;
  });

  const API_BASE_URL = '/api';

  const login = (userData, accessToken, refreshToken = null, rememberMe = true) => {
    setUser(userData);
    const storage = rememberMe ? localStorage : sessionStorage;
    
    // Clear other storage to avoid conflict
    if (rememberMe) {
      sessionStorage.removeItem('user');
      sessionStorage.removeItem('token');
      sessionStorage.removeItem('refresh_token');
    } else {
      localStorage.removeItem('user');
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
    }

    storage.setItem('user', JSON.stringify(userData));
    storage.setItem('token', accessToken);
    if (refreshToken) {
      storage.setItem('refresh_token', refreshToken);
    }
  };

  const updateUser = (updatedFields) => {
    setUser(prev => {
      if (!prev) return null;
      const updated = { ...prev, ...updatedFields };
      if (localStorage.getItem('user')) {
        localStorage.setItem('user', JSON.stringify(updated));
      }
      if (sessionStorage.getItem('user')) {
        sessionStorage.setItem('user', JSON.stringify(updated));
      }
      return updated;
    });
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken })
      });
    } catch (e) {
      console.debug("Backend logout notification failed:", e);
    } finally {
      setUser(null);
      localStorage.removeItem('user');
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      sessionStorage.removeItem('user');
      sessionStorage.removeItem('token');
      sessionStorage.removeItem('refresh_token');
      window.location.href = '/login';
    }
  };

  const refreshSession = useCallback(async () => {
    const refreshToken = localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');
    if (!refreshToken) return null;

    try {
      const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken })
      });

      if (res.ok) {
        const data = await res.json();
        const isLocalStorage = Boolean(localStorage.getItem('token'));
        const storage = isLocalStorage ? localStorage : sessionStorage;

        storage.setItem('token', data.access_token);
        if (data.refresh_token) {
          storage.setItem('refresh_token', data.refresh_token);
        }
        if (data.user) {
          updateUser(data.user);
        }
        return data.access_token;
      } else {
        // Refresh token invalid or expired -> logout
        logout();
        return null;
      }
    } catch (err) {
      console.error("Session refresh failed:", err);
      return null;
    }
  }, []);

  const handleAuthError = (status) => {
    if (status === 401) {
      logout();
    }
  };

  const getHeaders = (includeContentType = true) => {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    const headers = {};
    if (includeContentType) {
      headers['Content-Type'] = 'application/json';
    }
    if (token && token.trim() !== '' && token !== 'null' && token !== 'undefined') {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  };

  return (
    <AuthContext.Provider value={{
      user,
      login,
      logout,
      updateUser,
      refreshSession,
      API_BASE_URL,
      getHeaders,
      handleAuthError
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
