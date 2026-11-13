import React, { useState } from 'react';
import { useAuth } from '../AuthContext';
import { useNavigate } from 'react-router-dom';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('expired')) {
        return "Session expired or unauthorized. Please sign in to continue.";
      }
    }
    return '';
  });
  const [isLoading, setIsLoading] = useState(false);
  
  const { login, user, API_BASE_URL } = useAuth();
  const navigate = useNavigate();

  // If already logged in, redirect away from login page
  React.useEffect(() => {
    if (user) {
        const role = user.role?.toLowerCase() || '';
        if (role === 'admin') navigate('/admin-dashboard');
        else if (role === 'teacher') navigate('/teacher-dashboard');
        else navigate('/student-dashboard');
    }
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      console.log(` Connecting to: ${API_BASE_URL}/auth/login`);
      
      const res = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim().toLowerCase(), password })
      });

      const data = await res.json();
      
      if (res.ok) {
        login(data.user, data.token);
        const role = data.user.role?.toLowerCase() || '';
        if (role === 'admin') navigate('/admin-dashboard');
        else if (role === 'teacher') navigate('/teacher-dashboard');
        else navigate('/student-dashboard');
      } else {
        setError(data.message || 'Invalid credentials');
      }
    } catch (e) {
        console.error("Login Error:", e);
        // SHOW THE REAL ERROR ON SCREEN
        setError(`Connection Failed: ${e.message}. (Check Console)`);
    } finally {
        setIsLoading(false);
    }
  };

  return (
    <div className="page-container" style={{ alignItems: 'center', justifyContent: 'center', minHeight: '100vh', display: 'flex' }}>
      <div className="card" style={{ maxWidth: '400px', width: '100%', padding: '2rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
            AI-Assisted Assessment Intelligence Platform
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Sign in to continue
          </p>
        </div>

        {error && (
          <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.15)', color: 'var(--danger)', padding: '0.75rem', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.875rem' }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username / Email</label>
            <input 
              type="text" 
              placeholder="Enter your username" 
              value={username} 
              onChange={e => setUsername(e.target.value)} 
              required 
            />
          </div>

          <div className="form-group" style={{ marginBottom: '2rem' }}>
            <label>Password</label>
            <input 
              type="password" 
              placeholder="Enter your password" 
              value={password} 
              onChange={e => setPassword(e.target.value)} 
              required 
            />
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={isLoading}>
            {isLoading ? "Verifying..." : "Login"}
          </button>
        </form>

        <div style={{ marginTop: '1.5rem', padding: '0.75rem', backgroundColor: 'var(--bg-secondary, #f8fafc)', borderRadius: '6px', fontSize: '0.75rem', color: 'var(--text-secondary, #64748b)' }}>
          <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>Default Test Accounts:</div>
          <div>• <strong>Teacher:</strong> <code>teacher</code> / <code>Teacher123!</code> (or <code>ujjwal1</code>)</div>
          <div>• <strong>Student:</strong> <code>student</code> / <code>Student123!</code> (or <code>student1</code>)</div>
          <div>• <strong>Admin:</strong> <code>admin</code> / <code>adminpass</code></div>
        </div>
      </div>
    </div>
  );
};

export default Login;