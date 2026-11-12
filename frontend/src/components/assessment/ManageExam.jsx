import React, { useState, useEffect } from 'react';
import { useAuth } from '../../AuthContext';
import Papa from 'papaparse';
import { encryptText, hashText, decryptText } from '../../utils/encryption';
import AddQuestionForm from '../AddQuestionForm';
import QuestionBankPanel from '../QuestionBankPanel';
import ExamSettingsPanel from './ExamSettingsPanel';
import { PenTool, Settings } from 'lucide-react';


const ManageExam = ({ examId, activeExam, onChangeView, togglePublish }) => {
    const { API_BASE_URL, getHeaders } = useAuth();
    
    const [activeMode, setActiveMode] = useState("manual"); // 'manual' or 'bank'
    const [activeTab, setActiveTab] = useState('questions');
    const [questions, setQuestions] = useState([]);
    const [editingQuestion, setEditingQuestion] = useState(null);
    const [bulkPassword, setBulkPassword] = useState('');
    const [refreshKey, setRefreshKey] = useState(0);

    const fetchQuestions = async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/exams/${examId}/questions`, {
                headers: getHeaders() 
            });
            if (res.ok) {
                const rawData = await res.json();
                const decryptedData = rawData.map(q => ({
                    ...q,
                    original_text: q.text,
                    text: activeExam?.has_password ? decryptText(q.text, bulkPassword) : q.text,
                    reference_answer: q.is_subjective ? (activeExam?.has_password && q.reference_answer ? decryptText(q.reference_answer, bulkPassword) : q.reference_answer) : '',
                    options: {
                        A: activeExam?.has_password ? decryptText(q.option_a, bulkPassword) : q.option_a,
                        B: activeExam?.has_password ? decryptText(q.option_b, bulkPassword) : q.option_b,
                        C: activeExam?.has_password ? decryptText(q.option_c, bulkPassword) : q.option_c,
                        D: activeExam?.has_password ? decryptText(q.option_d, bulkPassword) : q.option_d,
                    }
                }));
                setQuestions(decryptedData);
            }
        } catch (e) { console.error(e); }
    };

    useEffect(() => {
        fetchQuestions();
    }, [examId, bulkPassword, refreshKey]);

    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        if (activeExam?.has_password && !bulkPassword) {
            alert(" You must enter the Exam Password in the box above to encrypt the CSV before uploading.");
            e.target.value = null; 
            return;
        }

        Papa.parse(file, {
            header: true,
            skipEmptyLines: true,
            complete: async (results) => {
                try {
                    const encryptedQuestions = results.data.map(row => {
                        const qTypeRaw = String(row.question_type || '').toUpperCase();
                        const isSubjLegacy = (row.is_subjective === 'true' || row.is_subjective === '1');
                        let isSubj = (qTypeRaw === 'SUBJECTIVE' || isSubjLegacy);
                        
                        // Infer subjective if question_type is missing but it has a reference answer and no MCQ options
                        if (!isSubj && row.reference_answer && !row.option_a && !row.correct_option) {
                            isSubj = true;
                        }
                        
                        const qType = isSubj ? 'SUBJECTIVE' : 'MCQ';

                        return {
                            text: activeExam?.has_password ? encryptText(row.question, bulkPassword) : row.question,
                            option_a: activeExam?.has_password ? encryptText(row.option_a, bulkPassword) : row.option_a,
                            option_b: activeExam?.has_password ? encryptText(row.option_b, bulkPassword) : row.option_b,
                            option_c: activeExam?.has_password ? encryptText(row.option_c, bulkPassword) : row.option_c,
                            option_d: activeExam?.has_password ? encryptText(row.option_d, bulkPassword) : row.option_d,
                            correct_option_hash: hashText(String(row.correct_option).trim().toUpperCase()),
                            reference_answer: isSubj ? 
                                (activeExam?.has_password ? encryptText(row.reference_answer || '', bulkPassword) : (row.reference_answer || '')) : null,
                            is_subjective: isSubj,
                            question_type: qType,
                            max_marks: parseFloat(row.marks) || 1.0,
                            topic: row.topic,
                            difficulty: row.difficulty,
                            bloom_level: row.bloom_level
                        };
                    });

                    const res = await fetch(`${API_BASE_URL}/exams/${examId}/bulk_questions`, {
                        method: 'POST',
                        headers: { ...getHeaders(), 'Content-Type': 'application/json' },
                        body: JSON.stringify({ questions: encryptedQuestions })
                    });
                    
                    const data = await res.json();
                    if (res.ok) {
                        alert(` Success: Uploaded securely!`);
                        setRefreshKey(prev => prev + 1); 
                    } else {
                        alert(` Error: ${data.message}`);
                    }
                } catch (error) {
                    console.error("Upload failed", error);
                    alert("Something went wrong uploading the file.");
                }
                e.target.value = null;
            }
        });
    };

    const handleDelete = async (q) => {
        if (activeExam?.has_password && (!bulkPassword || q.text.includes("[Encrypted Data"))) {
            alert(" Error: You must unlock the exam with the correct Encryption Key to delete questions.");
            return;
        }
        if(!window.confirm("Delete this question?")) return;
        try {
            const res = await fetch(`${API_BASE_URL}/exams/question/${q.id}`, { 
                method: 'DELETE',
                headers: getHeaders() 
            });
            if(res.ok) {
                setRefreshKey(prev => prev + 1);
            }
        } catch(e) { console.error(e); }
    };

    const handleEdit = (q) => {
        if (activeExam?.has_password && (!bulkPassword || q.text.includes("[Encrypted Data"))) {
            alert(" Error: You must unlock the exam with the correct Encryption Key to edit questions.");
            return;
        }
        setEditingQuestion(q);
        setActiveMode('manual');
    };

    return (
        <div className="container-fluid p-0">
            <div className="d-flex justify-content-between align-items-center mb-4">
                <h4 className="m-0 text-primary"><Settings size={18} className="me-2" /> Managing Exam #{examId}</h4>
                <button className="btn btn-outline-secondary btn-sm" onClick={() => onChangeView('list')}>← Back to Exams</button>
            </div>
            
            {activeExam?.has_password && (
                <div className="mb-4 p-3 rounded d-flex justify-content-between align-items-center" style={{ backgroundColor: 'rgba(245, 158, 11, 0.1)', border: '1px solid var(--warning)' }}>
                    <span className="text-warning fw-bold"> Exam is encrypted. Enter password to view/edit/add questions:</span>
                    <input 
                        type="text" 
                        placeholder="Exam Password" 
                        className="form-control form-control-sm border-warning" 
                        style={{ maxWidth: '300px' }}
                        value={bulkPassword} 
                        onChange={e => setBulkPassword(e.target.value)} 
                    />
                </div>
            )}

            <ul className="nav nav-tabs mb-4">
                <li className="nav-item">
                    <button className={`nav-link ${activeTab === 'questions' ? 'active' : ''}`} onClick={() => setActiveTab('questions')}>Questions</button>
                </li>
                <li className="nav-item">
                    <button className={`nav-link ${activeTab === 'settings' ? 'active' : ''}`} onClick={() => setActiveTab('settings')}>Settings</button>
                </li>
            </ul>

            {activeTab === 'questions' && (
            <div className="exam-builder-top" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 0.85fr) minmax(320px, 1.35fr)', gap: '20px', marginBottom: '2rem' }}>
                
                {/* LEFT SIDE - ACTIVE WORKSPACE */}
                <div className="card shadow-sm border-0 h-100">
                    <div className="card-header bg-white border-bottom pt-3 pb-3">
                        <h5 className="mb-3"><PenTool size={18} className="me-2" /> Add / Manage Questions</h5>
                        <div className="btn-group w-100" role="group">
                            <button 
                                type="button" 
                                className={`btn ${activeMode === 'manual' ? 'btn-primary' : 'btn-outline-primary'}`}
                                onClick={() => setActiveMode('manual')}
                            >
                                Manual + Bulk Actions
                            </button>
                            <button 
                                type="button" 
                                className={`btn ${activeMode === 'bank' ? 'btn-primary' : 'btn-outline-primary'}`}
                                onClick={() => setActiveMode('bank')}
                            >
                                Question Bank
                            </button>
                        </div>
                    </div>
                    <div className="card-body p-4" style={{ overflowY: 'auto', maxHeight: '800px' }}>
                        {activeMode === 'manual' && (
                            <>
                                <AddQuestionForm 
                                    examId={examId}
                                    hasPassword={activeExam?.has_password}
                                    examPassword={bulkPassword}
                                    editingQuestion={editingQuestion}
                                    onSuccess={() => setRefreshKey(prev => prev + 1)}
                                    clearEditing={() => setEditingQuestion(null)}
                                />
                                
                                <hr className="my-5" />
                                
                                <div className="p-4 rounded border bg-light">
                                    <h6 className="fw-bold mb-2">Bulk Upload Questions</h6>
                                    <p className="text-muted small mb-3">Upload multiple questions at once using a CSV file.</p>
                                    <input 
                                        type="file" 
                                        accept=".csv"
                                        className="form-control"
                                        onChange={handleFileUpload} 
                                    />
                                </div>
                            </>
                        )}
                        
                        {activeMode === 'bank' && (
                            <QuestionBankPanel 
                                examId={examId} 
                                activeExamQuestions={questions}
                                onQuestionAdded={() => setRefreshKey(prev => prev + 1)} 
                            />
                        )}
                    </div>
                </div>

                {/* RIGHT SIDE - OVERVIEW */}
                <div className="card shadow-sm border-0 h-100">
                    <div className="card-header bg-white border-bottom pt-3 pb-3">
                        <h5 className="mb-0"> Overview</h5>
                    </div>
                    <div className="card-body p-0 d-flex flex-column">
                        <div className="p-3 bg-light border-bottom">
                            <h6 className="m-0 fw-bold">Assessment Questions</h6>
                            <small className="text-muted">{questions.length} Questions</small>
                        </div>
                        <div className="p-3" style={{ overflowY: 'auto', maxHeight: '740px' }}>
                            {questions.length === 0 && (
                                <div className="text-center text-muted p-5">
                                    <p>No questions added yet.</p>
                                </div>
                            )}
                            {questions.map((q, idx) => (
                                <div key={q.id} className="mb-3 p-3 rounded border bg-white shadow-sm position-relative">
                                    <div className="d-flex justify-content-between align-items-start mb-2">
                                        <span className="badge bg-primary">Q{idx + 1}</span>
                                        <div className="d-flex gap-1">
                                            <button onClick={() => handleEdit(q)} className="btn btn-sm btn-outline-secondary p-1 px-2" style={{ fontSize: '0.75rem' }}>Edit</button>
                                            <button onClick={() => handleDelete(q)} className="btn btn-sm btn-outline-danger p-1 px-2" style={{ fontSize: '0.75rem' }}>Remove</button>
                                        </div>
                                    </div>
                                    <p className="mb-2 fw-semibold" style={{ fontSize: '0.9rem' }}>{q.text}</p>
                                    <div className="d-flex flex-wrap gap-2">
                                        {q.topic && <span className="badge bg-secondary opacity-75">{q.topic}</span>}
                                        {q.difficulty && <span className="badge bg-secondary opacity-75">{q.difficulty}</span>}
                                        {q.bloom_level && <span className="badge bg-secondary opacity-75">{q.bloom_level}</span>}
                                    </div>
                                </div>
                            ))}
                        </div>
                        
                        <div className="p-3 bg-light border-top mt-auto">
                            <h6 className="fw-bold mb-2">Visibility Status</h6>
                            <div className="d-flex align-items-center gap-3">
                                <span className={`badge ${activeExam?.is_visible ? 'bg-success' : 'bg-secondary'}`}>
                                    {activeExam?.is_visible ? 'Live / Published' : 'Draft / Hidden'}
                                </span>
                                <button 
                                    className={`btn btn-sm ${activeExam?.is_visible ? 'btn-outline-danger' : 'btn-success'}`}
                                    onClick={() => togglePublish(examId, activeExam?.is_visible)}
                                >
                                    {activeExam?.is_visible ? 'Unpublish Exam' : 'Publish Exam'}
                                </button>
                            </div>
                            <p className="text-muted small mt-2 mb-0">Students can only see published exams.</p>
                        </div>
                    </div>
                </div>

            </div>
            )}

            {activeTab === 'settings' && (
                <ExamSettingsPanel examId={examId} onUpdate={() => setRefreshKey(prev => prev + 1)} />
            )}

        </div>
    );
};

export default ManageExam;
