import React, { useState, useMemo } from 'react';
import { useAuth } from '../AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { Eye, EyeOff, Lock, User, Mail, Hash, AlertCircle, CheckCircle, ArrowRight, ShieldCheck, Check, X } from 'lucide-react';

const RegisterPage = () => {
  const [fullName, setFullName] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [enrollmentId, setEnrollmentId] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [isRegistered, setIsRegistered] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState('');
  const [devVerificationUrl, setDevVerificationUrl] = useState('');

  const { API_BASE_URL } = useAuth();
  const navigate = useNavigate();

  // Real-time password criteria evaluation
  const passwordCriteria = useMemo(() => {
    return {
      minLength: password.length >= 8,
      hasUpper: /[A-Z]/.test(password),
      hasLower: /[a-z]/.test(password),
      hasNumber: /[0-9]/.test(password),
      hasSpecial: /[!@#$%^&*(),.?":{}|<>\-_=+[\]\\/]/.test(password),
    };
  }, [password]);

  // Compute password score from 0 to 5
  const passwordScore = useMemo(() => {
    return Object.values(passwordCriteria).filter(Boolean).length;
  }, [passwordCriteria]);

  const passwordStrengthLabel = useMemo(() => {
    if (password.length === 0) return { label: '', color: '' };
    if (passwordScore <= 2) return { label: 'Weak', color: '#dc2626' };
    if (passwordScore === 3) return { label: 'Fair', color: '#d97706' };
    if (passwordScore === 4) return { label: 'Good', color: '#2563eb' };
    return { label: 'Strong', color: '#16a34a' };
  }, [password, passwordScore]);

  const isPasswordValid = passwordScore === 5;
  const isMatch = password && confirmPassword && password === confirmPassword;

  const validateForm = () => {
    const errors = {};
    if (!fullName.trim() || fullName.trim().length < 2) {
      errors.fullName = "Full name must be at least 2 characters long.";
    }
    if (!username.trim() || username.trim().length < 3) {
      errors.username = "Username must be at least 3 characters long.";
    } else if (!/^[a-zA-Z0-9_]+$/.test(username.trim())) {
      errors.username = "Username may only contain letters, numbers, and underscores.";
    }
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      errors.email = "Please enter a valid email address.";
    }
    if (!isPasswordValid) {
      errors.password = "Password does not meet the complexity requirements.";
    }
    if (password !== confirmPassword) {
      errors.confirmPassword = "Passwords do not match.";
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!validateForm()) return;
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: fullName.trim(),
          username: username.trim().toLowerCase(),
          email: email.trim().toLowerCase(),
          enrollment_id: enrollmentId.trim() || null,
          password,
          confirm_password: confirmPassword,
          role: 'student' // Explicitly student (enforced by backend regardless)
        })
      });

      const data = await res.json();

      if (res.ok) {
        setRegisteredEmail(email.trim().toLowerCase());
        if (data.dev_verification_url) {
          setDevVerificationUrl(data.dev_verification_url);
        }
        setIsRegistered(true);
      } else {
        setError(data.detail || data.message || "Registration failed. Please check your information.");
      }
    } catch (err) {
      console.error("Registration error:", err);
      setError(`Connection failed: ${err.message}. Please verify the server is running.`);
    } finally {
      setIsLoading(false);
    }
  };

  if (isRegistered) {
    return (
      <div className="page-container" style={{ alignItems: 'center', justifyContent: 'center', minHeight: '100vh', display: 'flex', padding: '1.5rem' }}>
        <div className="card" style={{ maxWidth: '480px', width: '100%', padding: '2.5rem 2rem', borderRadius: '12px', textAlign: 'center', boxShadow: 'var(--shadow-md)' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '64px', height: '64px', borderRadius: '50%', backgroundColor: 'rgba(22, 163, 74, 0.1)', color: 'var(--success)', marginBottom: '1.5rem' }}>
            <CheckCircle size={36} />
          </div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.75rem', color: 'var(--text-primary)' }}>
            Registration Successful!
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9375rem', lineHeight: '1.6', marginBottom: '1.5rem' }}>
            We've dispatched a verification link to:<br />
            <strong style={{ color: 'var(--text-primary)' }}>{registeredEmail}</strong>
          </p>
          {devVerificationUrl ? (
            <div style={{ marginBottom: '1.25rem' }}>
              <Link 
                to={devVerificationUrl} 
                className="btn btn-success" 
                style={{ display: 'block', width: '100%', padding: '0.75rem', fontWeight: '700', backgroundColor: '#16a34a', border: 'none', color: '#fff', borderRadius: '8px', marginBottom: '0.75rem', textDecoration: 'none' }}
              >
                ⚡ Verify Account Now (Dev Mode)
              </Link>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Dev Link: <code style={{ wordBreak: 'break-all' }}>{devVerificationUrl}</code>
              </div>
            </div>
          ) : (
            <div style={{ padding: '1rem', backgroundColor: 'var(--surface-secondary)', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '1.5rem', textAlign: 'left' }}>
              <div style={{ fontWeight: '600', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>Next Steps:</div>
              <div>1. Check your email inbox (and spam/promotions folder).</div>
              <div>2. Click the verification link to activate your student account.</div>
              <div>3. Once verified, return to sign in.</div>
            </div>
          )}
          <Link to="/login" className="btn btn-primary" style={{ width: '100%', padding: '0.75rem', fontWeight: '600' }}>
            Proceed to Sign In
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container" style={{ alignItems: 'center', justifyContent: 'center', minHeight: '100vh', display: 'flex', padding: '1.5rem' }}>
      <div className="card" style={{ maxWidth: '480px', width: '100%', padding: '2.5rem 2rem', borderRadius: '12px', boxShadow: 'var(--shadow-md)' }}>
        
        {/* Brand Header */}
        <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '48px', height: '48px', borderRadius: '12px', backgroundColor: 'rgba(37, 99, 235, 0.1)', color: 'var(--accent)', marginBottom: '0.75rem' }}>
            <ShieldCheck size={28} />
          </div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.25rem', color: 'var(--text-primary)' }}>
            Create Student Account
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: 0 }}>
            Join the QIS Assessment Intelligence Platform
          </p>
        </div>

        {error && (
          <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1.25rem', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertCircle size={18} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          {/* Full Name */}
          <div className="form-group" style={{ marginBottom: '1rem' }}>
            <label htmlFor="reg-name" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <User size={15} style={{ color: 'var(--text-secondary)' }} />
              Full Name *
            </label>
            <input
              id="reg-name"
              type="text"
              placeholder="e.g. John Doe"
              value={fullName}
              onChange={e => setFullName(e.target.value)}
              required
            />
            {fieldErrors.fullName && <div className="invalid-feedback">{fieldErrors.fullName}</div>}
          </div>

          {/* Username */}
          <div className="form-group" style={{ marginBottom: '1rem' }}>
            <label htmlFor="reg-username" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <User size={15} style={{ color: 'var(--text-secondary)' }} />
              Username *
            </label>
            <input
              id="reg-username"
              type="text"
              placeholder="e.g. jdoe2026"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
            />
            {fieldErrors.username && <div className="invalid-feedback">{fieldErrors.username}</div>}
          </div>

          {/* Email */}
          <div className="form-group" style={{ marginBottom: '1rem' }}>
            <label htmlFor="reg-email" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Mail size={15} style={{ color: 'var(--text-secondary)' }} />
              Email Address *
            </label>
            <input
              id="reg-email"
              type="email"
              placeholder="name@university.edu"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
            />
            {fieldErrors.email && <div className="invalid-feedback">{fieldErrors.email}</div>}
          </div>

          {/* Enrollment ID (Optional) */}
          <div className="form-group" style={{ marginBottom: '1rem' }}>
            <label htmlFor="reg-enrollment" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Hash size={15} style={{ color: 'var(--text-secondary)' }} />
              Enrollment / Student ID (Optional)
            </label>
            <input
              id="reg-enrollment"
              type="text"
              placeholder="e.g. STU-2026-089"
              value={enrollmentId}
              onChange={e => setEnrollmentId(e.target.value)}
            />
          </div>

          {/* Password */}
          <div className="form-group" style={{ marginBottom: '1rem' }}>
            <label htmlFor="reg-password" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Lock size={15} style={{ color: 'var(--text-secondary)' }} />
              Password *
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="reg-password"
                type={showPassword ? "text" : "password"}
                placeholder="Create a strong password"
                value={password}
                onChange={e => setPassword(e.target.value)}
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

            {/* Password Strength Indicator */}
            {password.length > 0 && (
              <div style={{ marginTop: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Password Strength:</span>
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

                {/* Password Criteria Checklist */}
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
            {fieldErrors.password && <div className="invalid-feedback">{fieldErrors.password}</div>}
          </div>

          {/* Confirm Password */}
          <div className="form-group" style={{ marginBottom: '1.5rem' }}>
            <label htmlFor="reg-confirm-password" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Lock size={15} style={{ color: 'var(--text-secondary)' }} />
              Confirm Password *
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="reg-confirm-password"
                type={showConfirmPassword ? "text" : "password"}
                placeholder="Re-enter your password"
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                required
                style={{ paddingRight: '2.5rem' }}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                tabIndex={-1}
                aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
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
            {fieldErrors.confirmPassword && <div className="invalid-feedback">{fieldErrors.confirmPassword}</div>}
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', padding: '0.75rem', fontWeight: '600', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
            disabled={isLoading}
          >
            {isLoading ? "Creating Account..." : "Create Account"}
            {!isLoading && <ArrowRight size={16} />}
          </button>
        </form>

        {/* Link back to Login */}
        <div style={{ textAlign: 'center', marginTop: '1.75rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: 'var(--accent)', fontWeight: '600' }}>
            Sign In here
          </Link>
        </div>

      </div>
    </div>
  );
};

export default RegisterPage;

