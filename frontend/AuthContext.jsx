import React, { createContext, useState, useContext, useEffect } from 'react';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
        try { 
            const parsed = JSON.parse(storedUser);
            // If the user state is a string (like a JWT token saved by mistake), wipe it!
            if (typeof parsed !== 'object' || parsed === null || !parsed.role) {
                localStorage.removeItem('user');
                localStorage.removeItem('token');
                return null;
            }
            return parsed; 
        } 
        catch (e) { localStorage.removeItem('user'); return null; }
    }
    return null;
  });
  
// Automatically uses 'localhost' if you typed localhost, 
// or uses your IP address if you connected from your phone!
const API_BASE_URL = '/api';

  useEffect(() => {
      // keeping useEffect empty since state is initialized synchronously now
  }, []);

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

  const getHeaders = () => {
    const token = localStorage.getItem('token') || '';
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, API_BASE_URL, getHeaders }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);