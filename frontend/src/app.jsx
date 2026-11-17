import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import VerifyEmailPage from './pages/VerifyEmailPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import ProfilePage from './pages/ProfilePage';
import StudentDashboard from './pages/StudentDashboard';
import TeacherDashboard from './pages/TeacherDashboard';
import AdminDashboard from './pages/AdminDashboard';
import { useAuth } from './AuthContext';

// Helper component to protect authenticated routes
const PrivateRoute = ({ children, role }) => {
  const { user } = useAuth();
  const token = typeof window !== 'undefined' 
    ? (localStorage.getItem('token') || sessionStorage.getItem('token')) 
    : null;
  
  // 1. If not logged in or missing token, redirect to Login
  if (!user || !token || token.trim() === '' || token === 'null' || token === 'undefined') {
    return <Navigate to="/login" replace />;
  }

  // 2. If logged in but role mismatch, redirect to user's permitted dashboard
  if (role && user.role?.toLowerCase() !== role.toLowerCase()) {
    const userRole = user.role?.toLowerCase();
    if (userRole === 'admin') return <Navigate to="/admin-dashboard" replace />;
    if (userRole === 'teacher') return <Navigate to="/teacher-dashboard" replace />;
    return <Navigate to="/student-dashboard" replace />;
  }

  // 3. Authorized
  return children;
};

const App = () => {
  return (
    <Routes>
      {/* Public Authentication Routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/oauth/callback" element={<Navigate to="/login" replace />} />

      {/* Root redirect */}
      <Route path="/" element={<Navigate to="/login" replace />} />
      
      {/* Protected Profile Route (Accessible to all authenticated roles) */}
      <Route path="/profile" element={
        <PrivateRoute>
          <ProfilePage />
        </PrivateRoute>
      } />

      {/* Protected Student Route */}
      <Route path="/student-dashboard" element={
        <PrivateRoute role="student">
          <StudentDashboard />
        </PrivateRoute>
      } />
      
      {/* Protected Teacher Route */}
      <Route path="/teacher-dashboard" element={
        <PrivateRoute role="teacher">
          <TeacherDashboard />
        </PrivateRoute>
      } />

      {/* Protected Admin Route */}
      <Route path="/admin-dashboard" element={
        <PrivateRoute role="admin">
          <AdminDashboard />
        </PrivateRoute>
      } />

      {/* Catch-all fallback */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
};

export default App;
