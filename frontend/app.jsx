import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/LoginPage';
import StudentDashboard from './pages/StudentDashboard';
import TeacherDashboard from './pages/TeacherDashboard';
import AdminDashboard from './pages/AdminDashboard'; // <--- Admin Import
import { useAuth } from './AuthContext';

// Helper component to protect routes
const PrivateRoute = ({ children, role }) => {
  const { user } = useAuth();
  
  // 1. If not logged in, go to Login
  if (!user) {
      return <Navigate to="/login" />;
  }

  // 2. If logged in but wrong role, go back to Login (or could be 403 page)
  if (role && user.role?.toLowerCase() !== role.toLowerCase()) {
      return <Navigate to="/login" />;
  }

  // 3. Authorized
  return children;
};

const App = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Navigate to="/login" />} />
      
      {/* Student Route */}
      <Route path="/student-dashboard" element={
        <PrivateRoute role="student">
            <StudentDashboard />
        </PrivateRoute>
      } />
      
      {/* Teacher Route */}
      <Route path="/teacher-dashboard" element={
        <PrivateRoute role="teacher">
            <TeacherDashboard />
        </PrivateRoute>
      } />

      {/* Admin Route (The new feature) */}
      <Route path="/admin-dashboard" element={
        <PrivateRoute role="admin">
            <AdminDashboard />
        </PrivateRoute>
      } />
    </Routes>
  );
};

export default App;