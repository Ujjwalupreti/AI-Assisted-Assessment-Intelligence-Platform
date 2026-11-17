import React from 'react';
import { useAuth } from '../AuthContext';
import { Link } from 'react-router-dom';
import { User, LogOut, CheckCircle, AlertCircle } from 'lucide-react';

const Navbar = ({ title }) => {
  const { user, logout } = useAuth();

  return (
    <nav className="navbar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.875rem 1.5rem', backgroundColor: 'var(--surface)', borderBottom: '1px solid var(--border)', borderRadius: '8px' }}>
      <div className="navbar-brand font-weight-bold h5 mb-0" style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <span>{title}</span>
      </div>
      
      <div className="nav-links" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {/* User Identity Pill */}
        <Link 
          to="/profile" 
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.5rem', 
            textDecoration: 'none', 
            color: 'var(--text-primary)',
            padding: '0.35rem 0.75rem',
            borderRadius: '6px',
            backgroundColor: 'var(--surface-secondary)',
            border: '1px solid var(--border)',
            fontSize: '0.875rem'
          }}
          title="View & Edit Account Settings"
        >
          <div style={{
            width: '26px',
            height: '26px',
            borderRadius: '50%',
            backgroundColor: 'rgba(37, 99, 235, 0.15)',
            color: 'var(--accent)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.75rem',
            fontWeight: '700'
          }}>
            {(user?.full_name || user?.username || 'U')[0].toUpperCase()}
          </div>
          
          <span style={{ fontWeight: '500' }}>
            {user?.full_name || user?.username}
          </span>
          
          <span className="badge" style={{ backgroundColor: 'var(--accent)', color: '#fff', fontSize: '0.7rem', textTransform: 'uppercase', padding: '0.2rem 0.45rem' }}>
            {user?.role}
          </span>

          {user?.is_verified && (
            <span title="Email Verified" style={{ color: 'var(--success)', display: 'inline-flex' }}>
              <CheckCircle size={14} />
            </span>
          )}
        </Link>

        {/* Logout Button */}
        <button 
          onClick={logout} 
          className="btn btn-outline-danger btn-sm" 
          style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontWeight: '500', padding: '0.35rem 0.75rem' }}
          title="Sign out of your account"
        >
          <LogOut size={15} />
          <span>Logout</span>
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
