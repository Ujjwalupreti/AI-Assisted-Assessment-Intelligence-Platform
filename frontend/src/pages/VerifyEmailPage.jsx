import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { CheckCircle, AlertCircle, RefreshCw, ArrowRight, ShieldCheck, Mail } from 'lucide-react';

const VerifyEmailPage = () => {
  const [token, setToken] = useState('');
  const [status, setStatus] = useState('initial'); // 'initial', 'verifying', 'success', 'error'
  const [message, setMessage] = useState('');
  const [resendEmail, setResendEmail] = useState('');
  const [resendStatus, setResendStatus] = useState('');
  const [isResending, setIsResending] = useState(false);
  const [cooldownSeconds, setCooldownSeconds] = useState(0);

  const { API_BASE_URL } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  // Cooldown countdown timer
  useEffect(() => {
    if (cooldownSeconds <= 0) return;
    const interval = setInterval(() => {
      setCooldownSeconds(prev => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [cooldownSeconds]);

  // Read token from URL query string
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const tokenParam = params.get('token');
    if (tokenParam) {
      setToken(tokenParam);
      executeVerification(tokenParam);
    }
  }, [location.search]);

  const executeVerification = async (verifyToken) => {
    if (!verifyToken) return;
    setStatus('verifying');
    setMessage('Verifying your email address...');

    try {
      const res = await fetch(`${API_BASE_URL}/auth/verify-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: verifyToken.trim() })
      });

      const data = await res.json();

      if (res.ok) {
        setStatus('success');
        setMessage(data.message || 'Email verified successfully! You may now sign in.');
      } else {
        setStatus('error');
        setMessage(data.detail || data.message || 'Verification token is invalid or has expired.');
      }
    } catch (err) {
      setStatus('error');
      setMessage(`Network error: ${err.message}. Please check your connection.`);
    }
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (token.trim()) {
      executeVerification(token.trim());
    }
  };

  const handleResend = async (e) => {
    e.preventDefault();
    if (!resendEmail.trim() || cooldownSeconds > 0) return;
    setIsResending(true);
    setResendStatus('');

    try {
      const res = await fetch(`${API_BASE_URL}/auth/resend-verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: resendEmail.trim().toLowerCase() })
      });

      const data = await res.json();
      if (res.ok) {
        setResendStatus(data.message || 'If an unverified account exists, a new link has been sent.');
        setCooldownSeconds(60);
      } else {
        setResendStatus(data.detail || 'Unable to resend verification email.');
        if (res.status === 429) {
          setCooldownSeconds(60);
        }
      }
    } catch (err) {
      setResendStatus(`Network error: ${err.message}`);
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className="page-container" style={{ alignItems: 'center', justifyContent: 'center', minHeight: '100vh', display: 'flex', padding: '1.5rem' }}>
      <div className="card" style={{ maxWidth: '460px', width: '100%', padding: '2.5rem 2rem', borderRadius: '12px', textAlign: 'center', boxShadow: 'var(--shadow-md)' }}>
        
        {/* Brand Icon */}
        <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '56px', height: '56px', borderRadius: '12px', backgroundColor: 'rgba(37, 99, 235, 0.1)', color: 'var(--accent)', marginBottom: '1.25rem' }}>
          <ShieldCheck size={32} />
        </div>

        <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
          Email Verification
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.75rem' }}>
          QIS Account Activation
        </p>

        {/* State 1: Verifying */}
        {status === 'verifying' && (
          <div style={{ padding: '2rem 1rem' }}>
            <div className="spinner-border text-primary" role="status" style={{ width: '2.5rem', height: '2.5rem', marginBottom: '1rem' }} />
            <div style={{ color: 'var(--text-primary)', fontWeight: '500' }}>Verifying your token...</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.8125rem', marginTop: '0.25rem' }}>Please wait while we confirm your email.</div>
          </div>
        )}

        {/* State 2: Success */}
        {status === 'success' && (
          <div>
            <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '64px', height: '64px', borderRadius: '50%', backgroundColor: 'rgba(22, 163, 74, 0.1)', color: 'var(--success)', marginBottom: '1.25rem' }}>
              <CheckCircle size={36} />
            </div>
            <div style={{ backgroundColor: 'rgba(22, 163, 74, 0.1)', color: 'var(--success)', border: '1px solid rgba(22, 163, 74, 0.3)', padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
              {message}
            </div>
            <Link to="/login?verified=1" className="btn btn-primary" style={{ width: '100%', padding: '0.75rem', fontWeight: '600', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
              Proceed to Sign In
              <ArrowRight size={16} />
            </Link>
          </div>
        )}

        {/* State 3: Error */}
        {status === 'error' && (
          <div>
            <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '64px', height: '64px', borderRadius: '50%', backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', marginBottom: '1.25rem' }}>
              <AlertCircle size={36} />
            </div>
            <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
              {message}
            </div>

            {/* Resend Form */}
            <div style={{ padding: '1.25rem', backgroundColor: 'var(--surface-secondary)', borderRadius: '8px', border: '1px solid var(--border)', textAlign: 'left', marginBottom: '1.5rem' }}>
              <div style={{ fontWeight: '600', fontSize: '0.875rem', color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
                Need a new verification link?
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                Enter your registered email address below to receive a fresh verification link.
              </p>
              <form onSubmit={handleResend}>
                <div className="form-group" style={{ marginBottom: '0.75rem' }}>
                  <input
                    type="email"
                    placeholder="Enter your email"
                    value={resendEmail}
                    onChange={e => setResendEmail(e.target.value)}
                    required
                  />
                </div>
                <button
                  type="submit"
                  disabled={isResending || cooldownSeconds > 0}
                  className="btn btn-sm btn-primary"
                  style={{ width: '100%', padding: '0.5rem' }}
                >
                  {isResending ? "Sending..." : cooldownSeconds > 0 ? `Resend in ${cooldownSeconds}s` : "Resend Verification Link"}
                </button>
              </form>
              {resendStatus && (
                <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--text-primary)' }}>
                  {resendStatus}
                </div>
              )}
            </div>

            <Link to="/login" style={{ color: 'var(--accent)', fontSize: '0.875rem', fontWeight: '500' }}>
              &larr; Return to Sign In
            </Link>
          </div>
        )}

        {/* State 4: Initial without token */}
        {status === 'initial' && !token && (
          <div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
              Please paste your verification token below or check your email for the activation link.
            </p>
            <form onSubmit={handleManualSubmit}>
              <div className="form-group" style={{ marginBottom: '1rem', textAlign: 'left' }}>
                <label>Verification Token</label>
                <input
                  type="text"
                  placeholder="Paste verification token here"
                  value={token}
                  onChange={e => setToken(e.target.value)}
                  required
                />
              </div>
              <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '0.75rem', fontWeight: '600' }}>
                Verify Token
              </button>
            </form>

            <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border)', textAlign: 'left' }}>
              <div style={{ fontSize: '0.8125rem', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                ⚡ Quick Dev Verification (No SMTP required)
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input 
                  type="email"
                  placeholder="Enter email to verify"
                  value={resendEmail}
                  onChange={e => setResendEmail(e.target.value)}
                  style={{ fontSize: '0.8125rem', padding: '0.4rem 0.6rem', flex: 1 }}
                />
                <button
                  type="button"
                  className="btn btn-sm btn-success"
                  style={{ whiteSpace: 'nowrap', fontSize: '0.8125rem', padding: '0.4rem 0.75rem', backgroundColor: '#16a34a', color: '#fff', border: 'none', borderRadius: '6px', fontWeight: '600' }}
                  onClick={async () => {
                    if (!resendEmail.trim()) return;
                    try {
                      const res = await fetch(`${API_BASE_URL}/auth/dev-verify`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email: resendEmail.trim() })
                      });
                      const d = await res.json();
                      if (res.ok) {
                        setStatus('success');
                        setMessage(d.message || 'Account verified successfully! You may now sign in.');
                      } else {
                        alert(d.detail || 'Could not verify account');
                      }
                    } catch(e) { alert(e.message); }
                  }}
                >
                  Verify Now
                </button>
              </div>
            </div>

            <div style={{ marginTop: '1.5rem', fontSize: '0.875rem' }}>
              <Link to="/login" style={{ color: 'var(--accent)', fontWeight: '500' }}>
                &larr; Return to Sign In
              </Link>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default VerifyEmailPage;

