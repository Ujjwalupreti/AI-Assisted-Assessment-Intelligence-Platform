import React, { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import Navbar from '../components/Navbar';
import PageHeader from '../components/common/PageHeader';
import { Users, FileText, BarChart2, Plus, Trash2 } from 'lucide-react';

const AdminDashboard = () => {
  const { user, API_BASE_URL, getHeaders } = useAuth();
  
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState({ users: 0, exams: 0, results: 0 });
  const [view, setView] = useState('list'); // 'list' or 'create'
  
  // Form State
  const [formData, setFormData] = useState({ 
    username: '', password: '', role: 'student', enrollment_id: '' 
  });

  // 1. Fetch Data
  const fetchData = async () => {
    try {
        // Get Users
        const userRes = await fetch(`${API_BASE_URL}/admin/users`, { headers: getHeaders() });
        if(userRes.ok) setUsers(await userRes.json());

        // Get Stats
        const statRes = await fetch(`${API_BASE_URL}/admin/stats`, { headers: getHeaders() });
        if(statRes.ok) setStats(await statRes.json());

    } catch (e) { console.error(e); }
  };

  useEffect(() => { fetchData(); }, []);

  // 2. Create User
  const handleCreate = async (e) => {
    e.preventDefault();
    try {
        const normalizedFormData = {
            ...formData,
            username: formData.username.trim().toLowerCase()
        };

        const res = await fetch(`${API_BASE_URL}/admin/users`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(normalizedFormData)
        });
        const data = await res.json();
        if(res.ok) {
            alert(" User Created!");
            setFormData({ username: '', password: '', role: 'student', enrollment_id: '' });
            setView('list');
            fetchData();
        } else {
            alert(` Error: ${data.detail || data.message || JSON.stringify(data)}`);
        }
    } catch (e) { alert("Network Error"); }
  };

  // 3. Delete User
  const handleDelete = async (id, username) => {
    if(!window.confirm(`Delete user '${username}'?`)) return;
    try {
        const res = await fetch(`${API_BASE_URL}/admin/users/${id}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        if(res.ok) fetchData();
    } catch (e) { console.error(e); }
  };

  return (
    <div>
      <Navbar title="Admin Panel" />
      <div className="page-container">
        
        <PageHeader 
            title="Admin Dashboard" 
            subtitle="Platform overview and user management." 
            actions={
                <button 
                    className={`btn ${view === 'create' ? 'btn-secondary' : 'btn-primary'}`}
                    onClick={() => setView(view === 'create' ? 'list' : 'create')}
                >
                    {view === 'create' ? "Cancel" : <><Plus size={18} /> Add User</>}
                </button>
            }
        />

        {/* STATS CARDS */}
        <div className="dashboard-stats mb-4">
            <div className="card" style={{ backgroundColor: 'rgba(2, 132, 199, 0.1)', borderColor: 'var(--info)' }}>
                <div className="card-body" style={{ textAlign: 'center', padding: '1.5rem' }}>
                    <h3 style={{ fontSize: '2rem', margin: 0, color: 'var(--info)' }} className="d-flex align-items-center justify-content-center gap-2">
                        <Users size={32} /> {stats.users}
                    </h3>
                    <small style={{ color: 'var(--text-secondary)' }}>Total Users</small>
                </div>
            </div>
            <div className="card" style={{ backgroundColor: 'rgba(34, 197, 94, 0.1)', borderColor: 'var(--success)' }}>
                <div className="card-body" style={{ textAlign: 'center', padding: '1.5rem' }}>
                    <h3 style={{ fontSize: '2rem', margin: 0, color: 'var(--success)' }} className="d-flex align-items-center justify-content-center gap-2">
                        <FileText size={32} /> {stats.exams}
                    </h3>
                    <small style={{ color: 'var(--text-secondary)' }}>Active Exams</small>
                </div>
            </div>
            <div className="card" style={{ backgroundColor: 'rgba(245, 158, 11, 0.1)', borderColor: 'var(--warning)' }}>
                <div className="card-body" style={{ textAlign: 'center', padding: '1.5rem' }}>
                    <h3 style={{ fontSize: '2rem', margin: 0, color: 'var(--warning)' }} className="d-flex align-items-center justify-content-center gap-2">
                        <BarChart2 size={32} /> {stats.results}
                    </h3>
                    <small style={{ color: 'var(--text-secondary)' }}>Submissions</small>
                </div>
            </div>
        </div>

        {/* VIEW: CREATE USER FORM */}
        {view === 'create' && (
            <div className="card mb-4">
                <div className="card-header">
                    <h5 className="card-title">Add New User</h5>
                </div>
                <div className="card-body" style={{ padding: '1.25rem' }}>
                    <form onSubmit={handleCreate}>
                        <div className="dashboard-grid mb-3">
                            <div className="form-group">
                                <label>Username</label>
                                <input className="form-control" required value={formData.username} onChange={e=>setFormData({...formData, username:e.target.value})} />
                            </div>
                            <div className="form-group">
                                <label>Password</label>
                                <input className="form-control" required value={formData.password} onChange={e=>setFormData({...formData, password:e.target.value})} />
                            </div>
                            <div className="form-group">
                                <label>Role</label>
                                <select className="form-select" value={formData.role} onChange={e=>setFormData({...formData, role:e.target.value})}>
                                    <option value="student">Student</option>
                                    <option value="teacher">Teacher</option>
                                    <option value="admin">Admin</option>
                                </select>
                            </div>
                            <div className="form-group">
                                <label>Enrollment ID / Staff ID</label>
                                <input className="form-control" value={formData.enrollment_id} onChange={e=>setFormData({...formData, enrollment_id:e.target.value})} />
                            </div>
                        </div>
                        <button className="btn btn-success" style={{ width: '100%' }}>Create User</button>
                    </form>
                </div>
            </div>
        )}

        {/* VIEW: USER LIST */}
        <div className="card">
            <div className="card-body" style={{ padding: 0, overflowX: 'auto' }}>
                <table className="table table-striped mb-0 align-middle" style={{ width: '100%', minWidth: '600px', borderCollapse: 'collapse' }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid var(--border)' }}>
                            <th style={{ padding: '1rem' }}>ID</th>
                            <th style={{ padding: '1rem' }}>Username</th>
                            <th style={{ padding: '1rem' }}>Role</th>
                            <th style={{ padding: '1rem' }}>Enrollment</th>
                            <th style={{ padding: '1rem', textAlign: 'right' }}>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users.map(u => (
                            <tr key={u.id} style={{ borderBottom: '1px solid var(--border)' }}>
                                <td style={{ padding: '1rem' }}>{u.id}</td>
                                <td style={{ padding: '1rem', fontWeight: 600 }}>{u.username}</td>
                                <td style={{ padding: '1rem' }}>
                                    <span className={`badge ${u.role==='admin'?'badge-danger':u.role==='teacher'?'badge-info':'badge-success'}`}>
                                        {u.role.toUpperCase()}
                                    </span>
                                </td>
                                <td style={{ padding: '1rem' }}>{u.enrollment_id || '-'}</td>
                                <td style={{ padding: '1rem', textAlign: 'right' }}>
                                    <button onClick={()=>handleDelete(u.id, u.username)} className="btn btn-ghost btn-sm" style={{ padding: '0.25rem', color: 'var(--danger)' }} title="Delete"><Trash2 size={18} /></button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>

      </div>
    </div>
  );
};

export default AdminDashboard;