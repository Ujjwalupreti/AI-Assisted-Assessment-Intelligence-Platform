import React, { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import Navbar from '../components/Navbar';
import CreateExamForm from '../components/CreateExamForm';
import ManageExam from '../components/assessment/ManageExam';
import ManageStudents from '../components/ManageStudents';
import KnowledgeBase from '../components/KnowledgeBase';
import PageHeader from '../components/common/PageHeader';
import { FileEdit, LayoutList, Users, BrainCircuit, Trash2, Settings, BarChart2, FileText, Lock, CheckCircle2, Circle } from 'lucide-react';
import { AlertTriangle, PenTool, XCircle } from 'lucide-react';
import { hashText } from '../utils/encryption';


const TeacherDashboard = () => {
  const { user, API_BASE_URL, getHeaders } = useAuth();
  
  // View State
  const [view, setView] = useState('list'); 
  const [exams, setExams] = useState([]);
  const [selectedExamId, setSelectedExamId] = useState(null);
  const [results, setResults] = useState([]);

  //  A trigger to silently refresh the question list without reloading the browser
  const [refreshKey, setRefreshKey] = useState(0);

  const [viewImageModal, setViewImageModal] = useState(null); 
  
  //  Modal state to view proctoring timeline
  const [proctorModal, setProctorModal] = useState(null);
  const [proctorEvents, setProctorEvents] = useState([]);
  
  //  Modal state to view and grade student review
  const [reviewModal, setReviewModal] = useState(null); 
  


  //  HISTORY API FIX: Safely change views and tell the browser
  const changeView = (newView, examId = null) => {
    setView(newView);
    setSelectedExamId(examId);
    window.history.pushState({ view: newView, examId: examId }, '', `#${newView}`);
  };

  //  HISTORY API FIX: Listen for the Browser's Back Button
  useEffect(() => {
    window.history.replaceState({ view: 'list', examId: null }, '', '#list');

    const handlePopState = (event) => {
      if (event.state) {
        setView(event.state.view || 'list');
        setSelectedExamId(event.state.examId || null);
      } else {
        setView('list');
        setSelectedExamId(null);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const fetchExams = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/exams`, { headers: getHeaders() });
      if (res.ok) setExams(await res.json());
    } catch (e) {}
  };

  useEffect(() => { if (view === 'list') fetchExams(); }, [view]);

  const viewExamResults = async (examId) => {
    try {
        const res = await fetch(`${API_BASE_URL}/exams/${examId}/results`, { headers: getHeaders() });
        if (res.ok) {
            setResults(await res.json());
            changeView('results', examId);
        }
    } catch (e) {}
  };

  const deleteExam = async (examId) => {
    if (!window.confirm("Delete exam?")) return;
    try {
        const res = await fetch(`${API_BASE_URL}/exams/${examId}`, { method: 'DELETE', headers: getHeaders() });
        if (res.ok) fetchExams();
    } catch (e) {}
  };

  const deleteResult = async (resultId) => {
    if (!window.confirm("Delete result?")) return;
    try {
        const res = await fetch(`${API_BASE_URL}/exams/results/${resultId}`, { method: 'DELETE', headers: getHeaders() });
        if (res.ok) viewExamResults(selectedExamId);
    } catch (e) {}
  };

  // Find the active exam for password logic
  const activeExam = exams.find(e => e.id === selectedExamId);



  // ---  TOGGLE PUBLISH ---
  const togglePublish = async (examId, currentStatus) => {
      try {
          const res = await fetch(`${API_BASE_URL}/exams/${examId}/toggle_publish`, { 
              method: 'PUT', 
              headers: getHeaders() 
          });
          if (res.ok) {
              fetchExams();
          } else {
              alert(" Failed to toggle visibility.");
          }
      } catch(e) { console.error(e); }
  };

  // ---  TRIGGER AI EVALUATION ---
  const triggerAIEvaluation = async (examId) => {
      if (!window.confirm("Trigger AI Evaluation for all subjective answers? This may take some time.")) return;
      
      const useRag = window.confirm("Do you want to ground the AI grading strictly using your Knowledge Base (RAG)? (Click OK for Yes, Cancel for No)");
      
      try {
          const res = await fetch(`${API_BASE_URL}/exams/${examId}/evaluate`, {
              method: 'POST',
              headers: { ...getHeaders(), 'Content-Type': 'application/json' },
              body: JSON.stringify({ use_rag: useRag })
          });
          if (res.ok) {
              alert(" AI Evaluation complete!");
              viewExamResults(examId); // refresh results
          } else {
              alert(" Failed to evaluate answers.");
          }
      } catch (e) { console.error(e); }
  };

  // --- 🔎 VIEW PROCTORING EVENTS ---
  const handleViewProctorEvents = async (result) => {
      setProctorModal(result);
      try {
          const res = await fetch(`${API_BASE_URL}/exams/${selectedExamId}/proctoring_events/${result.student_id}`, { headers: getHeaders() });
          if (res.ok) {
              setProctorEvents(await res.json());
          }
      } catch(e) {
          console.error(e);
      }
  };

  // --- 📝 VIEW REVIEW MODAL (GRADING) ---
  const viewStudentReview = async (examId, studentId, studentName) => {
      try {
          const res = await fetch(`${API_BASE_URL}/exams/${examId}/review/${studentId}`, { headers: getHeaders() });
          if (res.ok) {
              const data = await res.json();
              setReviewModal({ ...data, studentName, studentId, examId });
          }
      } catch (e) { console.error(e); }
  };

  const overrideGrade = async (answerId, marks, feedback) => {
      try {
          const res = await fetch(`${API_BASE_URL}/exams/answers/${answerId}/grade`, {
              method: 'PUT',
              headers: { ...getHeaders(), 'Content-Type': 'application/json' },
              body: JSON.stringify({ marks, feedback })
          });
          if (res.ok) {
              alert(" Grade updated!");
              // Refresh the review modal data
              viewStudentReview(reviewModal.examId, reviewModal.studentId, reviewModal.studentName);
          } else {
              alert(" Failed to update grade.");
          }
      } catch (e) { console.error(e); }
  };

  return (
    <div>
      <Navbar title="Teacher Portal" />

      {/*   3-PANEL IMAGE VIEWER MODAL */}
      {viewImageModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0,0,0,0.85)', zIndex: 9999, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
            <button className="btn btn-light rounded-circle mb-4" onClick={() => setViewImageModal(null)} style={{width:'50px', height:'50px', fontSize:'20px'}}>✕</button>
            
            <h3 className="text-white mb-4 fw-bold">Identity Verification: {viewImageModal.student_name}</h3>
            
            <div className="d-flex gap-4 flex-wrap justify-content-center">
                <div className="text-center">
                    <h5 className="text-white mb-3">1. Official ID</h5>
                    {viewImageModal.id_card_url ? 
                        <img src={`${API_BASE_URL}${viewImageModal.id_card_url}`} alt="ID Card" style={{height: '250px', width: '320px', borderRadius: '10px', border: '2px solid white', objectFit: 'cover'}} />
                        : <div className="text-muted bg-dark rounded d-flex align-items-center justify-content-center" style={{height: '250px', width: '320px'}}>No Image</div>
                    }
                </div>
                <div className="text-center">
                    <h5 className="text-white mb-3">2. Pre-Exam Face</h5>
                    {viewImageModal.face_photo_url ? 
                        <img src={`${API_BASE_URL}${viewImageModal.face_photo_url}`} alt="Face" style={{height: '250px', width: '320px', borderRadius: '10px', border: '2px solid white', objectFit: 'cover'}} />
                        : <div className="text-muted bg-dark rounded d-flex align-items-center justify-content-center" style={{height: '250px', width: '320px'}}>No Image</div>
                    }
                </div>
                <div className="text-center">
                    <h5 className="text-warning mb-3 fw-bold">3. Mid-Exam Secret Capture</h5>
                    {viewImageModal.mid_exam_photo_url ? 
                        <img src={`${API_BASE_URL}${viewImageModal.mid_exam_photo_url}`} alt="Secret" style={{height: '250px', width: '320px', borderRadius: '10px', border: '3px solid #ffc107', objectFit: 'cover'}} />
                        : <div className="text-muted bg-dark rounded d-flex align-items-center justify-content-center" style={{height: '250px', width: '320px'}}>No Capture Yet</div>
                    }
                </div>
            </div>
        </div>
      )}

      {/* --- PROCTORING TIMELINE MODAL --- */}
      {proctorModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', background: 'rgba(0,0,0,0.85)', zIndex: 9999, display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: '5vh' }}>
            <button className="btn btn-light rounded-circle mb-4" onClick={() => setProctorModal(null)} style={{width:'50px', height:'50px', fontSize:'20px'}}>✕</button>
            <h3 className="text-white mb-2 fw-bold">Proctoring Timeline: {proctorModal.student_name}</h3>
            
            <div className="card w-75 p-4" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
                <div className="d-flex justify-content-between mb-4 border-bottom pb-3">
                    <div>
                        <h4 className="m-0">Integrity Score: <strong>{proctorModal.integrity_score}%</strong></h4>
                        <span className={`badge ${proctorModal.integrity_score < 40 ? 'bg-danger' : proctorModal.integrity_score < 80 ? 'bg-warning text-dark' : 'bg-success'}`}>{proctorModal.integrity_label || 'GOOD'}</span>
                    </div>
                </div>

                {proctorEvents.length === 0 ? (
                    <p className="text-muted text-center py-5">No suspicious events recorded.</p>
                ) : (
                    <div className="timeline">
                        {proctorEvents.map(e => (
                            <div key={e.id} className="d-flex mb-3 p-3 border rounded shadow-sm bg-light">
                                <div className="me-3 text-muted" style={{ minWidth: '80px' }}>
                                    {new Date(e.timestamp).toLocaleTimeString()}
                                </div>
                                <div className="flex-grow-1">
                                    <h6 className="fw-bold mb-1">
                                        {e.event_type} 
                                        <span className={`badge ms-2 ${e.severity === 'HIGH' ? 'bg-danger' : e.severity === 'MEDIUM' ? 'bg-warning text-dark' : 'bg-secondary'}`}>
                                            {e.severity} RISK
                                        </span>
                                    </h6>
                                    {e.evidence_url && (
                                        <img src={e.evidence_url} alt="Evidence" style={{ height: '150px', borderRadius: '5px', marginTop: '10px' }} />
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
      )}

      {/* --- STUDENT REVIEW MODAL --- */}
      {reviewModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0,0,0,0.85)', zIndex: 9999, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '20px'}}>
            <div className="bg-white rounded shadow-lg d-flex flex-column" style={{width: '90%', maxWidth: '800px', height: '90%', overflow: 'hidden'}}>
                <div className="p-3 border-bottom d-flex justify-content-between align-items-center bg-light">
                    <h4 className="m-0 fw-bold">Review: {reviewModal.studentName}</h4>
                    <div className="d-flex align-items-center gap-3">
                        <span className="badge bg-primary fs-6">Score: {reviewModal.score} / {reviewModal.total}</span>
                        <button className="btn btn-outline-dark rounded-circle fw-bold" onClick={() => { setReviewModal(null); viewExamResults(selectedExamId); }} style={{width:'40px', height:'40px'}}>✕</button>
                    </div>
                </div>
                <div className="p-4 overflow-auto flex-grow-1">
                    {reviewModal.questions.map((q, idx) => (
                        <div key={idx} className="card border-0 shadow-sm mb-4">
                            <div className="card-body">
                                <h6 className="fw-bold mb-3">Q{idx+1}: {q.question_text}</h6>
                                
                                {q.is_subjective ? (
                                    <div className="bg-light p-3 rounded border">
                                        <div className="row">
                                            <div className="col-md-6 mb-3">
                                                <span className="fw-bold small text-muted d-block mb-1">Student's Answer:</span>
                                                <div className="p-2 bg-white rounded border h-100">{q.student_answer || <i className="text-muted">No answer provided</i>}</div>
                                            </div>
                                            <div className="col-md-6 mb-3">
                                                <span className="fw-bold small text-success d-block mb-1">Reference Answer:</span>
                                                <div className="p-2 bg-white rounded border border-success h-100">{q.reference_answer}</div>
                                            </div>
                                        </div>
                                        
                                        <div className={`bg-white p-3 rounded border mb-3 ${q.ai_confidence < 0.70 ? 'border-warning' : 'border-info'}`}>
                                            <div className="d-flex justify-content-between align-items-center mb-1">
                                                <span className={`fw-bold small ${q.ai_confidence < 0.70 ? 'text-warning' : 'text-info'}`}>
                                                    {q.ai_confidence < 0.70 ? ' Low Confidence AI Evaluation:' : ' AI Evaluation:'}
                                                </span>
                                                {q.ai_confidence && (
                                                    <span className="badge bg-secondary" title="AI Confidence Score">
                                                        Confidence: {Math.round(q.ai_confidence * 100)}%
                                                    </span>
                                                )}
                                            </div>
                                            <div className="d-flex justify-content-between align-items-start">
                                                <p className="m-0 small text-secondary">{q.ai_explanation || <i>Not evaluated by AI yet</i>}</p>
                                                <span className={`badge ms-3 fs-6 ${q.ai_confidence < 0.70 ? 'bg-warning text-dark' : 'bg-info'}`}>
                                                    Suggested: {q.ai_suggested_marks !== null ? q.ai_suggested_marks : '?'} / 1.0
                                                </span>
                                            </div>
                                        </div>
                                        
                                        <div className="border-top pt-3 mt-2 d-flex align-items-end gap-2">
                                            <div className="flex-grow-1">
                                                <label className="small fw-bold text-muted">Teacher Feedback (Optional)</label>
                                                <input type="text" className="form-control form-control-sm" id={`feedback_${q.id}`} defaultValue={q.teacher_feedback || ''} placeholder="Add comments..." />
                                            </div>
                                            <div style={{width: '100px'}}>
                                                <label className="small fw-bold text-muted">Marks</label>
                                                <input type="number" step="0.1" max="1" min="0" className="form-control form-control-sm" id={`marks_${q.id}`} defaultValue={q.marks_awarded !== null ? q.marks_awarded : (q.ai_suggested_marks || 0)} />
                                            </div>
                                            <button className="btn btn-sm btn-primary" onClick={() => {
                                                const marks = document.getElementById(`marks_${q.id}`).value;
                                                const feedback = document.getElementById(`feedback_${q.id}`).value;
                                                overrideGrade(q.id, marks, feedback);
                                            }}>Save Grade</button>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="ms-2">
                                        {['A', 'B', 'C', 'D'].map(opt => {
                                            const hashedOpt = hashText(opt);
                                            let isCorrectAns = q.correct_option === hashedOpt;
                                            let isStudentChoice = q.student_answer === hashedOpt;
                                            
                                            let optClass = "text-muted";
                                            let icon = "";
                                            
                                            if (isCorrectAns) {
                                                optClass = "text-success fw-bold bg-success bg-opacity-10 rounded p-1";
                                                icon = "";
                                            } else if (isStudentChoice && !isCorrectAns) {
                                                optClass = "text-danger fw-bold bg-danger bg-opacity-10 rounded p-1";
                                                icon = " (Student Choice)";
                                            } else if (isStudentChoice) {
                                                icon = "(Student Choice)";
                                            }
                                            
                                            return (
                                                <div key={opt} className={`mb-1 ${optClass}`}>
                                                    {opt}: {q.options[opt]} {icon}
                                                </div>
                                            );
                                        })}
                                        {!q.student_answer && <div className="text-warning fw-bold mt-2"><AlertTriangle size={18} className="me-2" /> Not answered</div>}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
      )}

      <div className="page-container">
        
        {/* TOP HEADER */}
        <PageHeader 
            title={` Hello, ${user?.username}`} 
            subtitle="Manage your exams and students efficiently." 
            actions={
                <>
                    <button className={`btn ${view === 'create' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => changeView('create')}>
                        <FileEdit size={18} /> Create Exam
                    </button>
                    <button className={`btn ${view === 'list' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => changeView('list')}>
                        <LayoutList size={18} /> My Exams
                    </button>
                    <button className={`btn ${view === 'students' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => changeView('students')}>
                        <Users size={18} /> Students
                    </button>
                    <button className={`btn ${view === 'knowledge' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => changeView('knowledge')}>
                        <BrainCircuit size={18} /> Knowledge Base
                    </button>
                </>
            }
        />

        {/* --- VIEW 1: CREATE EXAM --- */}
        {view === 'create' && (
           <CreateExamForm onSuccess={() => { changeView('list'); fetchExams(); }} />
        )}

        {/* --- VIEW: KNOWLEDGE BASE --- */}
        {view === 'knowledge' && (
            <div className="card">
                <KnowledgeBase />
            </div>
        )}

        {/* --- VIEW 2: LIST EXAMS --- */}
        {view === 'list' && !selectedExamId && (
          <div className="dashboard-grid">
            {exams.length === 0 && (
                <div className="empty-state" style={{ gridColumn: '1 / -1' }}>
                    <h4>No exams found. Start by creating one! </h4>
                </div>
            )}
            
            {exams.map(exam => (
              <div key={exam.id} className="card">
                <div className="card-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <FileText size={20} className="text-primary" />
                        <h5 className="card-title m-0">
                            {exam.title} {exam.has_password && <Lock size={16} title="Password Protected" />}
                        </h5>
                    </div>
                    <div className="d-flex gap-2">
                        <button 
                            className={`btn btn-sm ${exam.is_visible ? 'btn-success' : 'btn-secondary'}`} 
                            onClick={() => togglePublish(exam.id, exam.is_visible)}
                            title={exam.is_visible ? "Unpublish Exam" : "Publish Exam"}
                            style={{ padding: '0.25rem 0.75rem', borderRadius: '50px' }}
                        >
                            {exam.is_visible ? <CheckCircle2 size={14} /> : <Circle size={14} />}
                            {exam.is_visible ? "Live" : "Draft"}
                        </button>
                        <button className="btn btn-ghost" style={{ padding: '0.35rem', color: 'var(--danger)' }} onClick={() => deleteExam(exam.id)} title="Delete Exam"><Trash2 size={18} /></button>
                    </div>
                </div>
                
                <div className="card-body">
                    <p className="text-muted small mb-3">
                        ⏱️ {exam.duration} mins <br/> 
                        📅 {new Date(exam.start_date).toLocaleDateString()} <br/>
                        {exam.question_count === 0 ? (
                            <span className="badge badge-danger mt-2">
                                <AlertTriangle size={18} className="me-2" /> 0 Questions (Hidden from Students)
                            </span>
                        ) : (
                            <span className="badge badge-success mt-2">
                                 {exam.question_count} Question(s)
                            </span>
                        )}
                    </p>
                    
                    <div className="d-flex gap-2 mt-3">
                        <button className="btn btn-secondary flex-grow-1" onClick={() => changeView('list', exam.id)}>
                            <Settings size={16} /> Questions
                        </button>
                        <button className="btn btn-primary flex-grow-1" onClick={() => viewExamResults(exam.id)}>
                            <BarChart2 size={16} /> Results
                        </button>
                    </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* --- VIEW 3: MANAGE EXAM (NEW LAYOUT) --- */}
        {view === 'list' && selectedExamId && (
            <ManageExam 
                examId={selectedExamId} 
                activeExam={activeExam} 
                onChangeView={changeView} 
                togglePublish={togglePublish}
            />
        )}

        {/* --- VIEW 4: RESULTS TABLE --- */}
        {view === 'results' && (
            <div className="card overflow-hidden">
                <div className="p-3 border-bottom d-flex justify-content-between align-items-center" style={{background: 'rgba(255,107,107,0.1)'}}>
                    <h5 className="m-0 fw-bold text-danger"> Results: Exam #{selectedExamId}</h5>
                    <div className="d-flex gap-2">
                        <button className="btn btn-sm btn-info text-white fw-bold shadow-sm" onClick={() => triggerAIEvaluation(selectedExamId)}>
                            ✨ Grade Subjective with AI
                        </button>
                        <button className="btn btn-sm btn-outline-danger" onClick={() => changeView('list')}>← Back</button>
                    </div>
                </div>
                <div className="table-responsive p-0">
                    <table className="table table-hover mb-0 align-middle">
                        <thead style={{ background: 'var(--surface-secondary)' }}>
                            <tr>
                                <th className="ps-4">Student</th>
                                <th>Score</th>
                                <th>Status</th>
                                <th>Auth Identity</th>
                                <th>AI Proctor Report</th>
                                <th>Date</th>
                                <th className="text-end pe-4">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {results.length === 0 ? (
                                <tr><td colSpan="7" className="text-center py-5 text-muted">No students have taken this exam yet.</td></tr>
                            ) : (
                                results.map((r, idx) => (
                                    <tr key={idx}>
                                        <td className="ps-4 fw-bold">{r.student_name}</td>
                                        
                                        <td><span className="badge bg-primary rounded-pill px-3">{r.score} / {r.total_questions}</span></td>
                                        
                                        <td>
                                            {((activeExam?.cutoff_type === 'marks' && r.score >= activeExam?.cutoff_value) || 
                                              (activeExam?.cutoff_type !== 'marks' && r.score / r.total_marks >= (activeExam?.cutoff_value || 50) / 100)) 
                                                ? <span className="text-success fw-bold">Pass ✨</span> 
                                                : <span className="text-danger fw-bold">Fail <XCircle size={18} className="me-2" /></span>}
                                        </td>

                                        {/*  VIEW AUTH BUTTON */}
                                        <td>
                                            <button className="btn btn-sm text-primary fw-bold" style={{background: '#e3f2fd'}} onClick={() => setViewImageModal(r)}>
                                                 Verify Identity
                                            </button>
                                        </td>

                                        {/*  AI PROCTOR BADGES */}
                                        <td>
                                            <div className="d-flex align-items-center mb-1">
                                                <div style={{width: '100px', background: '#e9ecef', borderRadius: '10px', height: '10px', marginRight: '10px'}}>
                                                    <div style={{width: `${r.integrity_score}%`, background: r.integrity_score < 40 ? 'red' : r.integrity_score < 80 ? 'orange' : 'green', height: '100%', borderRadius: '10px'}}></div>
                                                </div>
                                                <strong>{r.integrity_score}%</strong>
                                            </div>
                                            <span className={`badge ${r.integrity_score < 40 ? 'bg-danger' : r.integrity_score < 80 ? 'bg-warning text-dark' : 'bg-success'}`}>
                                                {r.integrity_label || 'GOOD'}
                                            </span>
                                            <button className="btn btn-sm btn-link text-primary ms-2 p-0" onClick={() => handleViewProctorEvents(r)}>
                                                View Timeline
                                            </button>
                                        </td>

                                        <td className="text-muted small">{r.date_taken ? new Date(r.date_taken).toLocaleDateString() : 'N/A'}</td>
                                        
                                        <td className="text-end pe-4">
                                            <div className="d-flex justify-content-end gap-2">
                                                <button className="btn btn-sm btn-warning text-dark fw-bold rounded-pill px-3" onClick={() => viewStudentReview(selectedExamId, r.student_id, r.student_name)}>
                                                    <PenTool size={18} className="me-2" />️ Grade
                                                </button>
                                                <button className="btn btn-sm btn-outline-danger rounded-pill px-3" onClick={() => deleteResult(r.id)}>
                                                    Retake ↺
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        )}

        {/* --- VIEW 5: MANAGE STUDENTS --- */}
        {view === 'students' && (
            <div className="card p-4">
                <ManageStudents onClose={() => changeView('list')} />
            </div>
        )}

      </div>
    </div>
  );
};

export default TeacherDashboard;