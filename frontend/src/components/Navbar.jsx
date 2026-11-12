import React from 'react';
import { useAuth } from '../AuthContext';

const Navbar = ({ title }) => {
  const { user, logout } = useAuth();

  return (
    <nav className="navbar">
      <div className="navbar-brand font-weight-bold h5 mb-0" style={{ fontWeight: 600 }}>{title}</div>
      <div className="nav-links">
        <span className="text-secondary">
          {user?.username} <span className="badge badge-secondary" style={{ marginLeft: '0.5rem' }}>{user?.role?.toUpperCase()}</span>
        </span>
        <button onClick={logout} className="btn btn-danger">
          Logout
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
