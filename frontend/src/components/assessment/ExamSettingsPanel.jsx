import React, { useState, useEffect } from 'react';
import { Save, Settings, AlertTriangle } from 'lucide-react';
import { useAuth } from '../../AuthContext';

const ExamSettingsPanel = ({ examId, onUpdate }) => {
    const { API_BASE_URL, getHeaders } = useAuth();
    const [settings, setSettings] = useState({
        duration: 60,
        start_date: '',
        end_date: '',
        cutoff_type: 'percentage',
        cutoff_value: 50.0,
        description: '',
        tags: '',
        slotting_enabled: false,
        pooling_enabled: false,
        pool_size: 0,
        questions_per_student: 0,
        randomize_questions: true
    });

    const [slots, setSlots] = useState([]);
    const [newSlot, setNewSlot] = useState({ slot_name: '', start_time: '', end_time: '', capacity: 100 });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchSettings();
        fetchSlots();
    }, [examId]);

    const fetchSettings = async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/exams/${examId}/details`, { headers: getHeaders() });
            if (res.ok) {
                const data = await res.json();
                setSettings({
                    duration: data.duration || 60,
                    start_date: data.start_date ? data.start_date.substring(0, 16) : '',
                    end_date: data.end_date ? data.end_date.substring(0, 16) : '',
                    cutoff_type: data.cutoff_type || 'percentage',
                    cutoff_value: data.cutoff_value || 50.0,
                    description: data.description || '',
                    tags: data.tags ? data.tags : (data.topics && data.topics.length > 0 ? data.topics.join(', ') : ''),
                    slotting_enabled: data.slotting_enabled || false,
                    pooling_enabled: data.pooling_enabled || false,
                    pool_size: data.pool_size || 0,
                    questions_per_student: data.questions_per_student || 0,
                    randomize_questions: data.randomize_questions !== false
                });
            }
        } catch (error) {
            console.error("Error fetching settings:", error);
        } finally {
            setLoading(false);
        }
    };

    const fetchSlots = async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/exams/${examId}/slots`, { headers: getHeaders() });
            if (res.ok) {
                setSlots(await res.json());
            }
        } catch (error) {
            console.error("Error fetching slots:", error);
        }
    };

    const handleSaveSettings = async () => {
        try {
            const payload = {
                ...settings,
                start_date: settings.start_date || null,
                end_date: settings.end_date || null
            };
            const res = await fetch(`${API_BASE_URL}/exams/${examId}/settings`, {
                method: 'PUT',
                headers: getHeaders(),
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                alert("Settings saved successfully.");
                if (onUpdate) onUpdate();
            } else {
                alert("Error saving settings");
            }
        } catch (error) {
            console.error("Save error:", error);
            alert("Save failed");
        }
    };

    const handleAddSlot = async () => {
        if (!newSlot.start_time || !newSlot.end_time) {
            alert("Please provide both start and end times for the slot.");
            return;
        }
        try {
            const payload = {
                slot_name: newSlot.slot_name || `Slot ${slots.length + 1}`,
                start_time: newSlot.start_time,
                end_time: newSlot.end_time,
                capacity: parseInt(newSlot.capacity) || 100
            };
            const res = await fetch(`${API_BASE_URL}/exams/${examId}/slots`, {
                method: 'POST',
                headers: getHeaders(),
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                fetchSlots();
                setNewSlot({ slot_name: '', start_time: '', end_time: '', capacity: 100 });
            }
        } catch (error) {
            console.error("Slot add error:", error);
        }
    };

    const handleDeleteSlot = async (slotId) => {
        if(!window.confirm("Delete this slot?")) return;
        try {
            const res = await fetch(`${API_BASE_URL}/exams/${examId}/slots/${slotId}`, {
                method: 'DELETE',
                headers: getHeaders()
            });
            if (res.ok) fetchSlots();
        } catch (error) {
            console.error("Slot delete error:", error);
        }
    };

    const handleAutoAssign = async () => {
        if(!window.confirm("This will clear existing assignments and randomly distribute students across all slots. Continue?")) return;
        try {
            const res = await fetch(`${API_BASE_URL}/exams/${examId}/slots/auto-assign`, {
                method: 'POST',
                headers: getHeaders()
            });
            if (res.ok) {
                alert("Auto-assignment complete.");
                fetchSlots();
            } else {
                alert("Auto-assignment failed.");
            }
        } catch (error) {
            console.error("Auto assign error:", error);
        }
    };

    if (loading) return <div className="p-4 text-center">Loading settings...</div>;

    return (
        <div className="card shadow-sm border-0 mb-4 p-4">
            <h5 className="mb-4 text-primary d-flex align-items-center">
                <Settings size={20} className="me-2" /> Exam Settings
            </h5>
            <p className="text-muted mb-4">Configure how this assessment is conducted.</p>
            
            <hr />

            {/* EXAM INFORMATION */}
            <h6 className="fw-bold mb-3">Exam Information</h6>
            <div className="row mb-4">
                <div className="col-md-12 mb-3">
                    <label className="form-label text-muted small fw-bold">Description</label>
                    <textarea 
                        className="form-control" 
                        rows="2" 
                        value={settings.description} 
                        onChange={e => setSettings({...settings, description: e.target.value})}
                        placeholder="Brief overview of the exam..."
                    ></textarea>
                </div>
                <div className="col-md-12">
                    <label className="form-label text-muted small fw-bold">Tags (Comma separated)</label>
                    <input 
                        type="text" 
                        className="form-control" 
                        value={settings.tags} 
                        onChange={e => setSettings({...settings, tags: e.target.value})}
                        placeholder="e.g. DBMS, SQL, Normalization"
                    />
                </div>
            </div>

            <hr />

            {/* PASSING CRITERIA */}
            <h6 className="fw-bold mb-3">Passing Criteria</h6>
            <div className="row mb-4">
                <div className="col-md-6 mb-3">
                    <label className="form-label text-muted small fw-bold">Cut-off Type</label>
                    <select 
                        className="form-select" 
                        value={settings.cutoff_type} 
                        onChange={e => setSettings({...settings, cutoff_type: e.target.value})}
                    >
                        <option value="percentage">Percentage (%)</option>
                        <option value="marks">Marks</option>
                    </select>
                </div>
                <div className="col-md-6 mb-3">
                    <label className="form-label text-muted small fw-bold">Cut-off Value</label>
                    <input 
                        type="number" 
                        className="form-control" 
                        value={settings.cutoff_value} 
                        onChange={e => setSettings({...settings, cutoff_value: parseFloat(e.target.value)})}
                    />
                </div>
            </div>

            <hr />

            {/* EXAM SCHEDULE & SLOTTING */}
            <div className="d-flex justify-content-between align-items-center mb-3">
                <h6 className="fw-bold m-0">Exam Schedule & Slotting</h6>
                <div className="form-check form-switch">
                    <input 
                        className="form-check-input" 
                        type="checkbox" 
                        checked={settings.slotting_enabled} 
                        onChange={e => setSettings({...settings, slotting_enabled: e.target.checked})}
                    />
                    <label className="form-check-label text-muted small">Enable Slotting</label>
                </div>
            </div>

            <div className="row mb-4">
                <div className="col-md-4 mb-3">
                    <label className="form-label text-muted small fw-bold">Opens At {settings.slotting_enabled && "(Default)"}</label>
                    <input 
                        type="datetime-local" 
                        className="form-control" 
                        value={settings.start_date} 
                        onChange={e => setSettings({...settings, start_date: e.target.value})}
                        disabled={settings.slotting_enabled}
                    />
                </div>
                <div className="col-md-4 mb-3">
                    <label className="form-label text-muted small fw-bold">Closes At {settings.slotting_enabled && "(Default)"}</label>
                    <input 
                        type="datetime-local" 
                        className="form-control" 
                        value={settings.end_date} 
                        onChange={e => setSettings({...settings, end_date: e.target.value})}
                        disabled={settings.slotting_enabled}
                    />
                </div>
                <div className="col-md-4 mb-3">
                    <label className="form-label text-muted small fw-bold">Duration (Minutes)</label>
                    <input 
                        type="number" 
                        className="form-control" 
                        value={settings.duration} 
                        onChange={e => setSettings({...settings, duration: parseInt(e.target.value)})}
                    />
                </div>
            </div>

            {settings.slotting_enabled && (
                <div className="bg-light p-3 rounded mb-4 border border-primary">
                    <p className="text-muted small mb-3 fw-bold"><AlertTriangle size={14} className="me-1 text-primary" /> Slotting Enabled: Students will only be able to start the exam during their specifically assigned slot time. The default Opens/Closes times above will be overridden.</p>
                    {slots.map((s, idx) => (
                        <div key={s.id} className="d-flex align-items-center bg-white p-2 rounded border mb-2 shadow-sm">
                            <div className="flex-grow-1">
                                <strong>{s.slot_name}</strong>: {new Date(s.start_time).toLocaleString()} - {new Date(s.end_time).toLocaleString()}
                                <span className="ms-3 badge bg-info text-dark">Capacity: {s.capacity}</span>
                                <span className="ms-2 badge bg-secondary">Assigned: {s.assigned_count}</span>
                            </div>
                            <button className="btn btn-sm btn-outline-danger" onClick={() => handleDeleteSlot(s.id)}>Remove</button>
                        </div>
                    ))}

                    <div className="row mt-3 g-2">
                        <div className="col-md-3">
                            <input type="text" className="form-control form-control-sm" placeholder="Slot Name" value={newSlot.slot_name} onChange={e => setNewSlot({...newSlot, slot_name: e.target.value})} />
                        </div>
                        <div className="col-md-3">
                            <input type="datetime-local" className="form-control form-control-sm" value={newSlot.start_time} onChange={e => setNewSlot({...newSlot, start_time: e.target.value})} />
                        </div>
                        <div className="col-md-3">
                            <input type="datetime-local" className="form-control form-control-sm" value={newSlot.end_time} onChange={e => setNewSlot({...newSlot, end_time: e.target.value})} />
                        </div>
                        <div className="col-md-2">
                            <input type="number" className="form-control form-control-sm" placeholder="Capacity" value={newSlot.capacity} onChange={e => setNewSlot({...newSlot, capacity: e.target.value})} />
                        </div>
                        <div className="col-md-1">
                            <button className="btn btn-sm btn-primary w-100" onClick={handleAddSlot}>Add</button>
                        </div>
                    </div>

                    <div className="mt-3">
                        <button className="btn btn-sm btn-outline-primary me-2" onClick={handleSaveSettings}>Save Schedule State</button>
                        <button className="btn btn-sm btn-secondary" onClick={handleAutoAssign}>Auto Assign Students</button>
                    </div>
                </div>
            )}

            <div className="mb-4">
                <button className="btn btn-primary btn-sm" onClick={handleSaveSettings}>
                    <Save size={16} className="me-2" /> Save Settings
                </button>
            </div>

            {/* QUESTION POOLING TEMPORARILY REMOVED AS PER USER REQUEST */}
            {/*
            <div className="d-flex justify-content-between align-items-center mb-3">
                <h6 className="fw-bold m-0">Question Pooling</h6>
                <div className="form-check form-switch">
                    <input 
                        className="form-check-input" 
                        type="checkbox" 
                        checked={settings.pooling_enabled} 
                        onChange={e => setSettings({...settings, pooling_enabled: e.target.checked})}
                    />
                    <label className="form-check-label text-muted small">Enable Question Pooling</label>
                </div>
            </div>

            {settings.pooling_enabled && (
                <div className="bg-light p-3 rounded mb-4">
                    <p className="text-muted small mb-3">Students receive different questions from the selected question pool. This reduces question sharing while keeping the same assessment structure.</p>
                    
                    <div className="row mb-3">
                        <div className="col-md-4">
                            <label className="form-label text-muted small fw-bold">Total Pool Size</label>
                            <input 
                                type="number" 
                                className="form-control form-control-sm" 
                                placeholder="Total available" 
                                value={settings.pool_size || ''} 
                                onChange={e => setSettings({...settings, pool_size: parseInt(e.target.value) || 0})}
                            />
                        </div>
                        <div className="col-md-4">
                            <label className="form-label text-muted small fw-bold">Questions per Student</label>
                            <input 
                                type="number" 
                                className="form-control form-control-sm" 
                                value={settings.questions_per_student || ''} 
                                onChange={e => setSettings({...settings, questions_per_student: parseInt(e.target.value) || 0})}
                            />
                        </div>
                        <div className="col-md-4 d-flex align-items-end pb-1">
                            <div className="form-check mt-auto">
                                <input 
                                    className="form-check-input" 
                                    type="checkbox" 
                                    checked={settings.randomize_questions} 
                                    onChange={e => setSettings({...settings, randomize_questions: e.target.checked})}
                                />
                                <label className="form-check-label text-muted small fw-bold">Randomize Order</label>
                            </div>
                        </div>
                    </div>
                    
                    <button className="btn btn-sm btn-outline-primary" onClick={handleSaveSettings}>Save Pooling Settings</button>
                </div>
            )}
            */}
        </div>
    );
};

export default ExamSettingsPanel;
