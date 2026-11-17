import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import {
  User,
  Mail,
  ShieldCheck,
  Lock,
  Hash,
  CheckCircle,
  AlertCircle,
  KeyRound,
  Eye,
  EyeOff,
  ArrowLeft,
  Check,
  X
} from 'lucide-react';

const ProfilePage = () => {
  const { user, updateUser, API_BASE_URL, getHeaders } = useAuth();
  const navigate = useNavigate();

  // Profile Form State
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [enrollmentId, setEnrollmentId] = useState(user?.enrollment_id || '');
  const [profileSuccess, setProfileSuccess] = useState('');
  const [profileError, setProfileError] = useState('');
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);

  // Password Form State
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);

  // Active tab: 'profile' or 'security'
  const [activeTab, setActiveTab] = useState('profile');

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '');
      setEnrollmentId(user.enrollment_id || '');
    }
  }, [user]);

  // Password criteria
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

  // Handle Profile Update
  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setProfileSuccess('');
    setProfileError('');
    setIsUpdatingProfile(true);

    try {
      const res = await fetch(`${API_BASE_URL}/auth/profile`, {
        method: 'PUT',
        headers: getHeaders(true),
        body: JSON.stringify({
          full_name: fullName.trim(),
          enrollment_id: enrollmentId.trim() || null
        })
      });

      const data = await res.json();
      if (res.ok) {
        setProfileSuccess("Profile updated successfully!");
        updateUser(data.user);
      } else {
        setProfileError(data.detail || data.message || "Failed to update profile.");
      }
    } catch (err) {
      setProfileError(`Network error: ${err.message}`);
    } finally {
      setIsUpdatingProfile(false);
    }
  };

  // Handle Password Change
  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setPasswordSuccess('');
    setPasswordError('');

    if (!isPasswordValid) {
      setPasswordError("New password does not satisfy complexity requirements.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match.");
      return;
    }

    setIsUpdatingPassword(true);

    try {
      const res = await fetch(`${API_BASE_URL}/auth/change-password`, {
        method: 'POST',
        headers: getHeaders(true),
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword
        })
      });

      const data = await res.json();
      if (res.ok) {
        setPasswordSuccess("Password updated successfully! Other sessions have been revoked.");
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
      } else {
        setPasswordError(data.detail || data.message || "Failed to change password.");
      }
    } catch (err) {
      setPasswordError(`Network error: ${err.message}`);
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  const dashboardRoute = user?.role === 'admin'
    ? '/admin-dashboard'
    : user?.role === 'teacher'
    ? '/teacher-dashboard'
    : '/student-dashboard';

  return (
    <div className="page-container" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar title="User Profile & Account Settings" />

      <div style={{ maxWidth: '800px', width: '100%', margin: '1.5rem auto' }}>
        
        {/* Navigation & Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
          <button
            onClick={() => navigate(dashboardRoute)}
            className="btn btn-outline-secondary btn-sm"
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <ArrowLeft size={16} />
            Back to Dashboard
          </button>
        </div>

        {/* User Identity Card */}
        <div className="card" style={{ padding: '1.5rem', borderRadius: '12px', marginBottom: '1.5rem', display: 'flex', flexDirection: 'row', alignItems: 'center', gap: '1.25rem' }}>
          <div style={{
            width: '64px',
            height: '64px',
            borderRadius: '50%',
            backgroundColor: 'rgba(37, 99, 235, 0.1)',
            color: 'var(--accent)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.5rem',
            fontWeight: '700',
            flexShrink: 0
          }}>
            {(user?.full_name || user?.username || 'U')[0].toUpperCase()}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                {user?.full_name || user?.username}
              </h3>
              <span className="badge" style={{ backgroundColor: 'var(--accent)', color: '#fff', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                {user?.role}
              </span>
              {user?.is_verified ? (
                <span className="badge" style={{ backgroundColor: 'rgba(22, 163, 74, 0.15)', color: 'var(--success)', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                  <CheckCircle size={12} /> Email Verified
                </span>
              ) : (
                <span className="badge" style={{ backgroundColor: 'rgba(239, 68, 68, 0.15)', color: 'var(--danger)', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                  <AlertCircle size={12} /> Email Unverified
                </span>
              )}
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              @{user?.username} &bull; {user?.email}
            </div>
          </div>
        </div>

        {/* Tab Selector */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', marginBottom: '1.5rem' }}>
          <button
            type="button"
            onClick={() => setActiveTab('profile')}
            style={{
              padding: '0.75rem 1.25rem',
              fontWeight: '600',
              fontSize: '0.875rem',
              color: activeTab === 'profile' ? 'var(--accent)' : 'var(--text-secondary)',
              borderBottom: activeTab === 'profile' ? '2px solid var(--accent)' : '2px solid transparent',
              background: 'none',
              borderTop: 'none',
              borderLeft: 'none',
              borderRight: 'none',
              cursor: 'pointer'
            }}
          >
            Personal Details
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('security')}
            style={{
              padding: '0.75rem 1.25rem',
              fontWeight: '600',
              fontSize: '0.875rem',
              color: activeTab === 'security' ? 'var(--accent)' : 'var(--text-secondary)',
              borderBottom: activeTab === 'security' ? '2px solid var(--accent)' : '2px solid transparent',
              background: 'none',
              borderTop: 'none',
              borderLeft: 'none',
              borderRight: 'none',
              cursor: 'pointer'
            }}
          >
            Security & Password
          </button>
        </div>

        {/* TAB 1: Profile Details */}
        {activeTab === 'profile' && (
          <div className="card" style={{ padding: '2rem', borderRadius: '12px' }}>
            <h4 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '1.25rem', color: 'var(--text-primary)' }}>
              Edit Profile Information
            </h4>

            {profileSuccess && (
              <div style={{ backgroundColor: 'rgba(22, 163, 74, 0.1)', color: 'var(--success)', border: '1px solid rgba(22, 163, 74, 0.3)', padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1.25rem', fontSize: '0.875rem' }}>
                {profileSuccess}
              </div>
            )}
            {profileError && (
              <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1.25rem', fontSize: '0.875rem' }}>
                {profileError}
              </div>
            )}

            <form onSubmit={handleProfileSubmit}>
              <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label>Username</label>
                <input type="text" value={user?.username || ''} disabled style={{ backgroundColor: 'var(--surface-secondary)' }} />
                <div className="form-text">Usernames are permanently linked to your system identity and cannot be altered.</div>
              </div>

              <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label>Email Address</label>
                <input type="email" value={user?.email || ''} disabled style={{ backgroundColor: 'var(--surface-secondary)' }} />
                <div className="form-text">Primary contact and institutional communication address.</div>
              </div>

              <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label>Full Display Name</label>
                <input
                  type="text"
                  placeholder="Enter your full name"
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                <label>Student / Enrollment ID</label>
                <input
                  type="text"
                  placeholder="e.g. STU-2026-089"
                  value={enrollmentId}
                  onChange={e => setEnrollmentId(e.target.value)}
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                disabled={isUpdatingProfile}
                style={{ fontWeight: '600', padding: '0.625rem 1.25rem' }}
              >
                {isUpdatingProfile ? "Saving Changes..." : "Save Changes"}
              </button>
            </form>
          </div>
        )}

        {/* TAB 2: Security & Password */}
        {activeTab === 'security' && (
          <div className="card" style={{ padding: '2rem', borderRadius: '12px' }}>
            <h4 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '1.25rem', color: 'var(--text-primary)' }}>
              Change Account Password
            </h4>

            {passwordSuccess && (
              <div style={{ backgroundColor: 'rgba(22, 163, 74, 0.1)', color: 'var(--success)', border: '1px solid rgba(22, 163, 74, 0.3)', padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1.25rem', fontSize: '0.875rem' }}>
                {passwordSuccess}
              </div>
            )}
            {passwordError && (
              <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1.25rem', fontSize: '0.875rem' }}>
                {passwordError}
              </div>
            )}

            <form onSubmit={handlePasswordSubmit}>
              {/* Current Password */}
              <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label>Current Password</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showCurrentPassword ? "text" : "password"}
                    placeholder="Enter current password"
                    value={currentPassword}
                    onChange={e => setCurrentPassword(e.target.value)}
                    required
                    style={{ paddingRight: '2.5rem' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    tabIndex={-1}
                    style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: 0 }}
                  >
                    {showCurrentPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              {/* New Password */}
              <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label>New Password</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showNewPassword ? "text" : "password"}
                    placeholder="Enter new strong password"
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                    required
                    style={{ paddingRight: '2.5rem' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    tabIndex={-1}
                    style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: 0 }}
                  >
                    {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
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
                <label>Confirm New Password</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    placeholder="Confirm new password"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    required
                    style={{ paddingRight: '2.5rem' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    tabIndex={-1}
                    style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: 0 }}
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
                disabled={isUpdatingPassword || !isPasswordValid || !isMatch}
                style={{ fontWeight: '600', padding: '0.625rem 1.25rem' }}
              >
                {isUpdatingPassword ? "Updating Password..." : "Update Password"}
              </button>
            </form>
          </div>
        )}

      </div>
    </div>
  );
};

export default ProfilePage;

