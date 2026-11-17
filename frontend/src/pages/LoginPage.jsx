import React, { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { Eye, EyeOff, Lock, User, Mail, AlertCircle, CheckCircle, ArrowRight, ShieldCheck } from 'lucide-react';

const Login = () => {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  
  const [error, setError] = useState('');
  const [unverifiedEmail, setUnverifiedEmail] = useState('');
  const [resendStatus, setResendStatus] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isResending, setIsResending] = useState(false);
  
  const { login, user, API_BASE_URL } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('expired')) {
      setError("Your session has expired or is unauthorized. Please sign in again.");
    }
    if (params.get('verified')) {
      setSuccessMsg("Email successfully verified! You may now log in.");
    }
    if (params.get('reset')) {
      setSuccessMsg("Password successfully reset! Please sign in with your new password.");
    }
  }, [location]);

  // If already logged in, redirect away from login page
  useEffect(() => {
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
    setSuccessMsg('');
    setUnverifiedEmail('');
    setResendStatus('');
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          identifier: identifier.trim().toLowerCase(),
          password,
          remember_me: rememberMe
        })
      });

      const data = await res.json();
      
      if (res.ok) {
        login(data.user, data.access_token || data.token, data.refresh_token, rememberMe);
        const role = data.user.role?.toLowerCase() || '';
        if (role === 'admin') navigate('/admin-dashboard');
        else if (role === 'teacher') navigate('/teacher-dashboard');
        else navigate('/student-dashboard');
      } else {
        if (res.status === 403 && data.unverified) {
          setUnverifiedEmail(data.email || identifier.trim());
          setError(data.message || "Please verify your email address before logging in.");
        } else {
          setError(data.detail || data.message || 'Invalid username/email or password.');
        }
      }
    } catch (e) {
      console.error("Login Error:", e);
      setError(`Connection failed: ${e.message}. Please verify the server is running.`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendVerification = async () => {
    if (!unverifiedEmail) return;
    setIsResending(true);
    setResendStatus('');
    try {
      const res = await fetch(`${API_BASE_URL}/auth/resend-verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: unverifiedEmail })
      });
      const data = await res.json();
      if (res.ok) {
        setResendStatus(data.message || "A new verification email has been dispatched.");
      } else {
        setResendStatus(data.detail || "Unable to resend verification email at this moment.");
      }
    } catch (e) {
      setResendStatus("Network error trying to resend verification link.");
    } finally {
      setIsResending(false);
    }
  };

  const handleFastDevVerify = async () => {
    if (!unverifiedEmail) return;
    try {
      setIsResending(true);
      const res = await fetch(`${API_BASE_URL}/auth/dev-verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: unverifiedEmail })
      });
      const data = await res.json();
      if (res.ok) {
        setError('');
        setSuccessMsg(data.message || 'Account successfully verified! Please click Sign In now.');
        setUnverifiedEmail('');
      } else {
        setError(data.detail || 'Failed to verify account.');
      }
    } catch (e) {
      setError(`Error verifying: ${e.message}`);
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className="page-container" style={{ alignItems: 'center', justifyContent: 'center', minHeight: '100vh', display: 'flex', padding: '1.5rem' }}>
      <div className="card" style={{ maxWidth: '440px', width: '100%', padding: '2.5rem 2rem', borderRadius: '12px', boxShadow: 'var(--shadow-md)' }}>
        
        {/* Brand Header */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '48px', height: '48px', borderRadius: '12px', backgroundColor: 'rgba(37, 99, 235, 0.1)', color: 'var(--accent)', marginBottom: '1rem' }}>
            <ShieldCheck size={28} />
          </div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.25rem', color: 'var(--text-primary)' }}>
            QIS Platform
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: 0 }}>
            Assessment Intelligence & Proctoring System
          </p>
        </div>

        {/* Notifications & Status Alerts */}
        {successMsg && (
          <div style={{ backgroundColor: 'rgba(22, 163, 74, 0.1)', color: 'var(--success)', border: '1px solid rgba(22, 163, 74, 0.3)', padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1.25rem', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <CheckCircle size={18} style={{ flexShrink: 0 }} />
            <span>{successMsg}</span>
          </div>
        )}

        {error && (
          <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1.25rem', fontSize: '0.875rem', display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
            <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1 }}>
              <div>{error}</div>
              {unverifiedEmail && (
                <div style={{ marginTop: '0.65rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
                  <button
                    type="button"
                    onClick={handleFastDevVerify}
                    disabled={isResending}
                    className="btn btn-sm"
                    style={{ backgroundColor: '#16a34a', color: '#fff', fontSize: '0.75rem', fontWeight: '600', padding: '0.3rem 0.6rem', border: 'none', borderRadius: '4px' }}
                  >
                    ⚡ Instant Verify (Dev Mode)
                  </button>
                  <button
                    type="button"
                    onClick={handleResendVerification}
                    disabled={isResending}
                    className="btn btn-sm"
                    style={{ backgroundColor: 'var(--accent)', color: '#fff', fontSize: '0.75rem', padding: '0.3rem 0.6rem', border: 'none', borderRadius: '4px' }}
                  >
                    {isResending ? "Sending..." : "Resend Link"}
                  </button>
                  {resendStatus && (
                    <div style={{ width: '100%', marginTop: '0.35rem', fontSize: '0.75rem', color: 'var(--text-primary)' }}>
                      {resendStatus}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit}>
          <div className="form-group" style={{ marginBottom: '1.25rem' }}>
            <label htmlFor="login-identifier" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <User size={15} style={{ color: 'var(--text-secondary)' }} />
              Username or Email
            </label>
            <input 
              id="login-identifier"
              type="text" 
              placeholder="e.g. student1 or student@exam.com" 
              value={identifier} 
              onChange={e => setIdentifier(e.target.value)} 
              required 
              autoComplete="username"
            />
          </div>

          <div className="form-group" style={{ marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label htmlFor="login-password" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', margin: 0 }}>
                <Lock size={15} style={{ color: 'var(--text-secondary)' }} />
                Password
              </label>
              <Link to="/forgot-password" style={{ fontSize: '0.75rem', color: 'var(--accent)', fontWeight: '500' }}>
                Forgot Password?
              </Link>
            </div>
            <div style={{ position: 'relative' }}>
              <input 
                id="login-password"
                type={showPassword ? "text" : "password"} 
                placeholder="Enter your password" 
                value={password} 
                onChange={e => setPassword(e.target.value)} 
                required 
                autoComplete="current-password"
                style={{ paddingRight: '2.5rem' }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
                aria-label={showPassword ? "Hide password" : "Show password"}
                style={{
                  position: 'absolute',
                  right: '0.75rem',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  padding: 0,
                  display: 'flex',
                  alignItems: 'center'
                }}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
            <label className="form-check" style={{ cursor: 'pointer', margin: 0, fontSize: '0.8125rem' }}>
              <input 
                type="checkbox" 
                checked={rememberMe} 
                onChange={e => setRememberMe(e.target.checked)}
                style={{ width: 'auto', marginRight: '0.5rem' }} 
              />
              Keep me signed in
            </label>
          </div>

          <button 
            type="submit" 
            className="btn btn-primary" 
            style={{ width: '100%', padding: '0.75rem', fontWeight: '600', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }} 
            disabled={isLoading}
          >
            {isLoading ? "Signing in..." : "Sign In"}
            {!isLoading && <ArrowRight size={16} />}
          </button>
        </form>

        {/* Link to Registration */}
        <div style={{ textAlign: 'center', marginTop: '1.75rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Don't have an account?{' '}
          <Link to="/register" style={{ color: 'var(--accent)', fontWeight: '600' }}>
            Register here
          </Link>
        </div>

        {/* Developer / Demo Credentials Helper */}
        <details style={{ marginTop: '1.5rem', padding: '0.75rem', backgroundColor: 'var(--surface-secondary)', borderRadius: '8px', fontSize: '0.75rem', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
          <summary style={{ cursor: 'pointer', fontWeight: '600', color: 'var(--text-primary)' }}>
            Demo Test Accounts
          </summary>
          <div style={{ marginTop: '0.5rem', lineHeight: '1.6' }}>
            <div>• <strong>Teacher:</strong> <code>teacher</code> / <code>Teacher123!</code></div>
            <div>• <strong>Student:</strong> <code>student</code> / <code>Student123!</code></div>
            <div>• <strong>Admin:</strong> <code>admin</code> / <code>adminpass</code></div>
          </div>
        </details>

      </div>
    </div>
  );
};

export default Login;
