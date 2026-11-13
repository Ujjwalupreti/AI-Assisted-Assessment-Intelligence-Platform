import React, { createContext, useState, useContext, useEffect } from 'react';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const storedUser = localStorage.getItem('user');
    const storedToken = localStorage.getItem('token');
    
    // Both user AND a valid token must exist together
    if (storedUser && storedToken && storedToken.trim() !== '' && storedToken !== 'null' && storedToken !== 'undefined') {
        try { 
            const parsed = JSON.parse(storedUser);
            if (typeof parsed !== 'object' || parsed === null || !parsed.role) {
                localStorage.removeItem('user');
                localStorage.removeItem('token');
                return null;
            }
            return parsed; 
        } 
        catch (e) {
            localStorage.removeItem('user');
            localStorage.removeItem('token');
            return null;
        }
    } else {
        // Clear broken partial credentials
        localStorage.removeItem('user');
        localStorage.removeItem('token');
        return null;
    }
  });
  
  const API_BASE_URL = '/api';

  const login = (userData, token) => {
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
    localStorage.setItem('token', token);
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    window.location.href = '/login';
  };

  const handleAuthError = (status) => {
    if (status === 401) {
      setUser(null);
      localStorage.removeItem('user');
      localStorage.removeItem('token');
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login?expired=1';
      }
    }
  };

  const getHeaders = (includeContentType = true) => {
    const token = localStorage.getItem('token');
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
    <AuthContext.Provider value={{ user, login, logout, API_BASE_URL, getHeaders, handleAuthError }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);