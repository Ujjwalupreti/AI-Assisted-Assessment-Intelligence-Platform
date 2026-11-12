import React, { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';

const ManageStudents = ({ onClose }) => {
  const { API_BASE_URL, getHeaders } = useAuth();
  const [textInput, setTextInput] = useState('');
  const [statusMsg, setStatusMsg] = useState('');
  const [existingStudents, setExistingStudents] = useState([]);

  // 1. Fetch Students
  const fetchStudents = async () => {
    try {
        const res = await fetch(`${API_BASE_URL}/students/list`, { headers: getHeaders() });
        if (res.ok) setExistingStudents(await res.json());
    } catch (e) { console.error(e); }
  };

  useEffect(() => { fetchStudents(); }, []);

  // 2. Add Students
  const handleBulkAdd = async () => {
    if (!textInput.trim()) return;

    const lines = textInput.split('\n');
    const studentsToAdd = [];
    lines.forEach(line => {
        const parts = line.split(',');
        if (parts.length >= 2) {
            studentsToAdd.push({
                username: parts[0].trim().toLowerCase(),
                password: parts[1].trim(),
                enrollment_id: parts[2] ? parts[2].trim() : ''
            });
        }
    });

    setStatusMsg("Uploading...");
    try {
        const res = await fetch(`${API_BASE_URL}/students/bulk_add`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ students: studentsToAdd })
        });
        const data = await res.json();
        
        if (res.ok) {
            setStatusMsg(` ${data.message}`);
            if(data.errors && data.errors.length > 0) alert("Warnings:\n" + data.errors.join("\n"));
            setTextInput('');
            fetchStudents();
        } else {
            setStatusMsg(` Error: ${data.message}`);
        }
    } catch (e) { setStatusMsg(" Network Error"); }
  };

  // 3. DELETE STUDENT (New Feature)
  const handleDelete = async (id, username) => {
    if(!window.confirm(`Are you sure you want to delete student '${username}'?`)) return;

    try {
        const res = await fetch(`${API_BASE_URL}/students/${id}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        
        if (res.ok) {
            fetchStudents(); // Refresh list
        } else {
            alert("Failed to delete student.");
        }
    } catch(e) { console.error(e); }
  };

  return (
    <div className="card my-3">
      <div className="card-header" style={{ paddingBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h5 className="card-title m-0">Manage Students</h5>
        <button onClick={onClose} className="btn btn-secondary btn-sm">Close</button>
      </div>
      <div className="card-body">
        <div style={{ display: 'flex', flexDirection: 'row', flexWrap: 'wrap', gap: '2rem' }}>
            {/* LEFT: INPUT */}
            <div style={{ flex: '1 1 300px', borderRight: '1px solid var(--border)', paddingRight: '2rem' }}>
                <h6 style={{ fontWeight: 600, color: 'var(--accent)', marginBottom: '0.5rem' }}>Bulk Add</h6>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>Format: <code>username, password, enrollment_id</code></p>
                <textarea 
                    style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--surface-secondary)', color: 'var(--text-primary)', fontFamily: 'monospace', marginBottom: '1rem' }} rows="6"
                    placeholder={`john_doe, pass123, S101\nalice, secure, S102`}
                    value={textInput} onChange={(e) => setTextInput(e.target.value)}
                ></textarea>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <button onClick={handleBulkAdd} className="btn btn-success"> Add Students</button>
                    <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--danger)' }}>{statusMsg}</span>
                </div>
            </div>

            {/* RIGHT: LIST WITH DELETE */}
            <div style={{ flex: '1 1 400px' }}>
                <h6 style={{ fontWeight: 600, marginBottom: '1rem' }}>Existing ({existingStudents.length})</h6>
                <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid var(--border)', borderRadius: '6px' }}>
                    <table className="table table-striped mb-0 align-middle" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                        <thead style={{ background: 'var(--surface-secondary)' }}>
                            <tr style={{ borderBottom: '1px solid var(--border)' }}>
                                <th style={{ padding: '0.5rem 1rem' }}>Username</th>
                                <th style={{ padding: '0.5rem 1rem' }}>ID</th>
                                <th style={{ padding: '0.5rem 1rem', textAlign: 'right' }}>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {existingStudents.map(s => (
                                <tr key={s.id} style={{ borderBottom: '1px solid var(--border)' }}>
                                    <td style={{ padding: '0.5rem 1rem' }}>{s.username}</td>
                                    <td style={{ padding: '0.5rem 1rem' }}>{s.enrollment_id || '-'}</td>
                                    <td style={{ padding: '0.5rem 1rem', textAlign: 'right' }}>
                                        <button 
                                            className="btn btn-ghost btn-sm" 
                                            style={{ padding: '0.25rem 0.5rem', color: 'var(--danger)' }}
                                            title="Delete Student"
                                            onClick={() => handleDelete(s.id, s.username)}
                                        >
                                            ️
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
};

export default ManageStudents;