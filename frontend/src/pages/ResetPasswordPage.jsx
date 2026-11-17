import React, { useState, useEffect, useMemo } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { Eye, EyeOff, Lock, CheckCircle, AlertCircle, ArrowRight, ShieldCheck, Check, X } from 'lucide-react';

const ResetPasswordPage = () => {
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [tokenStatus, setTokenStatus] = useState('checking'); // 'checking', 'valid', 'invalid'
  const [tokenMessage, setTokenMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const { API_BASE_URL } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  // Password criteria check
  const passwordCriteria = useMemo(() => {
    return {
      minLength: newPassword.length >= 8,
      hasUpper: /[A-Z]/.test(newPassword),
      hasLower: /[a-z]/.test(newPassword),
      hasNumber: /[0-9]/.test(newPassword),
      hasSpecial: /[!@#$%^&*(),.?":{}|<>\-_=+[\]\\/]/.test(newPassword),
    };
  }, [newPassword]);

  const passwordScore = useMemo(() => {
    return Object.values(passwordCriteria).filter(Boolean).length;
  }, [passwordCriteria]);

  const passwordStrengthLabel = useMemo(() => {
    if (newPassword.length === 0) return { label: '', color: '' };
    if (passwordScore <= 2) return { label: 'Weak', color: '#dc2626' };
    if (passwordScore === 3) return { label: 'Fair', color: '#d97706' };
    if (passwordScore === 4) return { label: 'Good', color: '#2563eb' };
    return { label: 'Strong', color: '#16a34a' };
  }, [newPassword, passwordScore]);

  const isPasswordValid = passwordScore === 5;
  const isMatch = newPassword && confirmPassword && newPassword === confirmPassword;

  // Extract and verify token on mount
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const tokenParam = params.get('token');
    if (!tokenParam) {
      setTokenStatus('invalid');
      setTokenMessage('No password reset token was provided. Please request a new link.');
      return;
    }
    setToken(tokenParam);

    // Verify token with backend
    fetch(`${API_BASE_URL}/auth/verify-reset-token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: tokenParam.trim() })
    })
      .then(res => res.json())
      .then(data => {
        if (data.valid) {
          setTokenStatus('valid');
        } else {
          setTokenStatus('invalid');
          setTokenMessage(data.message || 'This reset link has expired or has already been used.');
        }
      })
      .catch(err => {
        setTokenStatus('invalid');
        setTokenMessage('Could not verify reset link due to a network error.');
      });
  }, [location.search, API_BASE_URL]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!isPasswordValid) {
      setError("Please ensure your new password satisfies all complexity criteria.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: token.trim(),
          new_password: newPassword,
          confirm_password: confirmPassword
        })
      });

      const data = await res.json();
      if (res.ok) {
        setIsSuccess(true);
      } else {
        setError(data.detail || data.message || "Failed to reset password.");
      }
    } catch (err) {
      setError(`Connection error: ${err.message}.`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="page-container" style={{ alignItems: 'center', justifyContent: 'center', minHeight: '100vh', display: 'flex', padding: '1.5rem' }}>
      <div className="card" style={{ maxWidth: '460px', width: '100%', padding: '2.5rem 2rem', borderRadius: '12px', boxShadow: 'var(--shadow-md)' }}>
        
        {/* Brand Header */}
        <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '52px', height: '52px', borderRadius: '12px', backgroundColor: 'rgba(37, 99, 235, 0.1)', color: 'var(--accent)', marginBottom: '0.75rem' }}>
            <ShieldCheck size={28} />
          </div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.25rem', color: 'var(--text-primary)' }}>
            Choose New Password
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: 0 }}>
            Set a strong, unique password for your account
          </p>
        </div>

        {/* Checking Token State */}
        {tokenStatus === 'checking' && (
          <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
            <div className="spinner-border text-primary" role="status" style={{ width: '2rem', height: '2rem', marginBottom: '1rem' }} />
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Verifying reset link...</div>
          </div>
        )}

        {/* Invalid Token State */}
        {tokenStatus === 'invalid' && (
          <div style={{ textAlign: 'center' }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '60px', height: '60px', borderRadius: '50%', backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', marginBottom: '1.25rem' }}>
              <AlertCircle size={32} />
            </div>
            <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
              {tokenMessage}
            </div>
            <Link to="/forgot-password" className="btn btn-primary" style={{ width: '100%', padding: '0.75rem', fontWeight: '600' }}>
              Request New Reset Link
            </Link>
            <div style={{ marginTop: '1rem', fontSize: '0.875rem' }}>
              <Link to="/login" style={{ color: 'var(--text-secondary)' }}>
                &larr; Back to Sign In
              </Link>
            </div>
          </div>
        )}

        {/* Success State */}
        {isSuccess && (
          <div style={{ textAlign: 'center' }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '64px', height: '64px', borderRadius: '50%', backgroundColor: 'rgba(22, 163, 74, 0.1)', color: 'var(--success)', marginBottom: '1.25rem' }}>
              <CheckCircle size={36} />
            </div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: '700', marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
              Password Reset Complete!
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: '1.6', marginBottom: '1.5rem' }}>
              Your password has been securely updated. You can now log in using your new credentials.
            </p>
            <Link to="/login?reset=1" className="btn btn-primary" style={{ width: '100%', padding: '0.75rem', fontWeight: '600', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
              Proceed to Sign In
              <ArrowRight size={16} />
            </Link>
          </div>
        )}

        {/* Valid Form State */}
        {tokenStatus === 'valid' && !isSuccess && (
          <form onSubmit={handleSubmit}>
            {error && (
              <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1.25rem', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertCircle size={18} style={{ flexShrink: 0 }} />
                <span>{error}</span>
              </div>
            )}

            {/* New Password */}
            <div className="form-group" style={{ marginBottom: '1.25rem' }}>
              <label htmlFor="reset-new-password" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Lock size={15} style={{ color: 'var(--text-secondary)' }} />
                New Password *
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="reset-new-password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your new password"
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  required
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
                    padding: 0
                  }}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>

              {/* Password Strength Meter */}
              {newPassword.length > 0 && (
                <div style={{ marginTop: '0.5rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Strength:</span>
                    <span style={{ fontWeight: '600', color: passwordStrengthLabel.color }}>{passwordStrengthLabel.label}</span>
                  </div>
                  <div style={{ height: '4px', backgroundColor: 'var(--border)', borderRadius: '2px', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${(passwordScore / 5) * 100}%`,
                      backgroundColor: passwordStrengthLabel.color,
                      transition: 'width 0.3s ease, background-color 0.3s ease'
                    }} />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.25rem', marginTop: '0.5rem', fontSize: '0.72rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: passwordCriteria.minLength ? 'var(--success)' : 'var(--text-secondary)' }}>
                      {passwordCriteria.minLength ? <Check size={12} /> : <X size={12} />} 8+ Characters
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: passwordCriteria.hasUpper ? 'var(--success)' : 'var(--text-secondary)' }}>
                      {passwordCriteria.hasUpper ? <Check size={12} /> : <X size={12} />} Uppercase (A-Z)
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: passwordCriteria.hasLower ? 'var(--success)' : 'var(--text-secondary)' }}>
                      {passwordCriteria.hasLower ? <Check size={12} /> : <X size={12} />} Lowercase (a-z)
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: passwordCriteria.hasNumber ? 'var(--success)' : 'var(--text-secondary)' }}>
                      {passwordCriteria.hasNumber ? <Check size={12} /> : <X size={12} />} Number (0-9)
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: passwordCriteria.hasSpecial ? 'var(--success)' : 'var(--text-secondary)', gridColumn: 'span 2' }}>
                      {passwordCriteria.hasSpecial ? <Check size={12} /> : <X size={12} />} Special Symbol (!@#$%^&*)
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Confirm New Password */}
            <div className="form-group" style={{ marginBottom: '1.5rem' }}>
              <label htmlFor="reset-confirm-password" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Lock size={15} style={{ color: 'var(--text-secondary)' }} />
                Confirm New Password *
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="reset-confirm-password"
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="Re-enter your new password"
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  required
                  style={{ paddingRight: '2.5rem' }}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  tabIndex={-1}
                  aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                  style={{
                    position: 'absolute',
                    right: '0.75rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    padding: 0
                  }}
                >
                  {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {confirmPassword && (
                <div style={{ fontSize: '0.75rem', marginTop: '0.25rem', color: isMatch ? 'var(--success)' : 'var(--danger)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                  {isMatch ? <Check size={14} /> : <X size={14} />}
                  {isMatch ? "Passwords match" : "Passwords do not match"}
                </div>
              )}
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', padding: '0.75rem', fontWeight: '600' }}
              disabled={isLoading || !isPasswordValid || !isMatch}
            >
              {isLoading ? "Updating Password..." : "Update Password"}
            </button>
          </form>
        )}

      </div>
    </div>
  );
};

export default ResetPasswordPage;

