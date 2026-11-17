import React, { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import { encryptText, hashText } from '../utils/encryption';
import QuestionAnalysisPanel from './QuestionAnalysisPanel';
import { Sparkles, Calculator, AlertCircle, CheckCircle, X, HelpCircle } from 'lucide-react';

const QUESTION_TYPES = [
  { value: 'MCQ', label: 'Multiple Choice (MCQ)', group: 'Objective' },
  { value: 'SHORT_ANSWER', label: 'Short Answer (Descriptive)', group: 'Subjective' },
  { value: 'LONG_ANSWER', label: 'Long Answer / Essay', group: 'Subjective' },
  { value: 'CONCEPTUAL', label: 'Conceptual & Theoretical', group: 'Subjective' },
  { value: 'MATH_PROBLEM', label: 'Mathematical Problem-Solving', group: 'STEM & Math' },
  { value: 'DERIVATION', label: 'Step-by-Step Derivation', group: 'STEM & Math' },
  { value: 'NUMERICAL', label: 'Numerical Problem', group: 'STEM & Math' },
  { value: 'PROOF', label: 'Proof-Based Question', group: 'STEM & Math' },
  { value: 'ALGORITHM', label: 'Programming & Algorithm Explanation', group: 'Computing' },
  { value: 'DFA_NFA', label: 'DFA / NFA Automata Design', group: 'Computing' },
  { value: 'STATE_TRANSITION', label: 'State-Transition Diagram / Table', group: 'Computing' },
  { value: 'GRAPH', label: 'Graph & Network Question', group: 'Diagrams' },
  { value: 'FLOWCHART', label: 'Flowchart & Block Diagram', group: 'Diagrams' },
  { value: 'TABLE', label: 'Table-Based Question', group: 'Structured' },
  { value: 'MIXED', label: 'Mixed-Format Question', group: 'Other' },
];

const MATH_SYMBOLS = ['x^2', '\\frac{a}{b}', '\\sqrt{x}', '\\int', '\\sum', '\\times', '\\pm', '\\le', '\\ge', '\\pi', '\\alpha', '\\beta', '\\Sigma', '\\delta', '\\in'];

const AddQuestionForm = ({ examId, hasPassword, examPassword, onCancel, editingQuestion, onSuccess, clearEditing }) => {
  const { API_BASE_URL, getHeaders } = useAuth();
  
  const [formData, setFormData] = useState({
    text: '', option_a: '', option_b: '', option_c: '', option_d: '', correct_option: 'A',
    topic: '', difficulty: 'Medium', bloom_level: 'Remember', ai_quality_score: 0.0, is_subjective: false, duplicate_score: 0.0,
    reference_answer: '', rubric: '', question_type: 'MCQ', max_marks: 1
  });
  const [msg, setMsg] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [aiAnalysisData, setAiAnalysisData] = useState(null);
  
  // AI Assistance & Improvement States
  const [isAssisting, setIsAssisting] = useState(false);
  const [aiAssistData, setAiAssistData] = useState(null);

  // Load editing question if provided
  useEffect(() => {
    if (editingQuestion) {
      const qType = editingQuestion.question_type || (editingQuestion.is_subjective ? 'SHORT_ANSWER' : 'MCQ');
      const isSubj = qType !== 'MCQ';
      setFormData({
        text: editingQuestion.text || '',
        option_a: editingQuestion.options?.A || '',
        option_b: editingQuestion.options?.B || '',
        option_c: editingQuestion.options?.C || '',
        option_d: editingQuestion.options?.D || '',
        correct_option: 'A',
        topic: editingQuestion.topic || '',
        difficulty: editingQuestion.difficulty || 'Medium',
        bloom_level: editingQuestion.bloom_level || 'Remember',
        ai_quality_score: editingQuestion.ai_quality_score || 0.0,
        is_subjective: isSubj,
        question_type: qType,
        duplicate_score: 0.0,
        reference_answer: editingQuestion.reference_answer || '',
        rubric: editingQuestion.rubric || '',
        max_marks: editingQuestion.max_marks || (isSubj ? 5 : 1)
      });
      setMsg("✏️ Editing Question (Note: If MCQ, re-select correct option below)");
    } else {
      resetForm();
    }
  }, [editingQuestion]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    if (name === 'question_type') {
      const isSubj = value !== 'MCQ';
      setFormData(prev => ({
        ...prev,
        question_type: value,
        is_subjective: isSubj,
        max_marks: prev.max_marks === 1 && isSubj ? 5 : prev.max_marks
      }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  const insertMathSymbol = (sym) => {
    setFormData(prev => ({
      ...prev,
      text: (prev.text || '') + (prev.text && !prev.text.endsWith(' ') ? ' ' : '') + sym + ' '
    }));
  };

  // AI Quality & Bloom Analysis
  const handleAnalyze = async () => {
    if (!formData.text) {
      setMsg("Please enter question text to analyze.");
      return;
    }
    setIsAnalyzing(true);
    setAiAnalysisData(null);
    try {
      const res = await fetch(`${API_BASE_URL}/ai/questions/analyze`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ 
          text: formData.text,
          option_a: formData.option_a,
          option_b: formData.option_b,
          option_c: formData.option_c,
          option_d: formData.option_d,
          correct_option: formData.correct_option,
          expected_topic: formData.topic,
          expected_bloom: formData.bloom_level,
          expected_difficulty: formData.difficulty
        })
      });
      if (res.ok) {
        const aiData = await res.json();
        setAiAnalysisData(aiData);
        setMsg(aiData.review?.required ? "AI suggests review." : "AI Analysis Complete!");
      } else {
        setMsg("Error connecting to AI Analysis Service.");
      }
    } catch (e) {
      console.error(e);
      setMsg("Error connecting to AI Analysis Service.");
    }
    setIsAnalyzing(false);
  };

  // AI Assist & Question Improvement
  const handleAiAssist = async () => {
    if (!formData.text) {
      setMsg("Please enter question statement to generate AI improvements.");
      return;
    }
    setIsAssisting(true);
    setAiAssistData(null);
    try {
      const res = await fetch(`${API_BASE_URL}/ai/questions/assist`, {
        method: 'POST',
        headers: { ...getHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: formData.text,
          question_type: formData.question_type,
          topic: formData.topic,
          difficulty: formData.difficulty,
          bloom_level: formData.bloom_level,
          max_marks: parseFloat(formData.max_marks) || 5.0,
          reference_answer: formData.reference_answer
        })
      });
      if (res.ok) {
        const assistData = await res.json();
        setAiAssistData(assistData);
        setMsg("✨ AI generated suggestions! Review and apply below.");
      } else {
        setMsg("Error connecting to AI Assist service.");
      }
    } catch (err) {
      console.error(err);
      setMsg("Failed to generate AI suggestions.");
    }
    setIsAssisting(false);
  };

  const handleApplyAiAssist = () => {
    if (!aiAssistData) return;
    setFormData(prev => ({
      ...prev,
      text: aiAssistData.suggested_version || prev.text,
      reference_answer: aiAssistData.suggested_reference_answer || prev.reference_answer,
      rubric: aiAssistData.suggested_rubric || prev.rubric,
      bloom_level: aiAssistData.suggested_bloom || prev.bloom_level,
      difficulty: aiAssistData.suggested_difficulty || prev.difficulty,
      topic: (aiAssistData.keywords && aiAssistData.keywords[0]) || prev.topic
    }));
    setAiAssistData(null);
    setMsg("✅ AI improvements applied to form!");
  };

  const handleAcceptAnalysis = () => {
    if (!aiAnalysisData) return;
    setFormData(prev => ({
      ...prev,
      topic: aiAnalysisData.classification?.topic?.label || prev.topic,
      difficulty: aiAnalysisData.classification?.difficulty?.label || prev.difficulty,
      bloom_level: aiAnalysisData.classification?.bloom?.label || prev.bloom_level,
      ai_quality_score: aiAnalysisData.quality?.overall_score || 0.0,
      question_type: aiAnalysisData.classification?.question_type?.label || prev.question_type,
      is_subjective: (aiAnalysisData.classification?.question_type?.label !== 'MCQ' || prev.is_subjective),
      duplicate_score: aiAnalysisData.duplicate?.risk || 0.0
    }));
    setAiAnalysisData(null);
    setMsg("AI Metadata accepted and applied.");
  };

  const handleIgnoreAnalysis = () => {
    setAiAnalysisData(null);
    setMsg("AI suggestions ignored.");
  };

  // Submit (Add or Update)
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (hasPassword && !examPassword) {
        setMsg("Error: You must enter an Encryption Key to secure questions!");
        return;
    }
    
    const isSubj = formData.question_type !== 'MCQ';
    if (isSubj && (!formData.reference_answer || formData.reference_answer.trim() === '')) {
        setMsg("Error: Reference answer is required for subjective questions.");
        return;
    }

    const url = editingQuestion 
      ? `${API_BASE_URL}/exams/question/${editingQuestion.id}`
      : `${API_BASE_URL}/exams/${examId}/questions`;
    
    const method = editingQuestion ? 'PUT' : 'POST';

    const securePayload = {
        text: hasPassword ? encryptText(formData.text, examPassword) : formData.text,
        option_a: (!isSubj && hasPassword) ? encryptText(formData.option_a, examPassword) : formData.option_a,
        option_b: (!isSubj && hasPassword) ? encryptText(formData.option_b, examPassword) : formData.option_b,
        option_c: (!isSubj && hasPassword) ? encryptText(formData.option_c, examPassword) : formData.option_c,
        option_d: (!isSubj && hasPassword) ? encryptText(formData.option_d, examPassword) : formData.option_d,
        correct_option_hash: !isSubj ? hashText(String(formData.correct_option).trim().toUpperCase()) : null,
        topic: formData.topic,
        difficulty: formData.difficulty,
        bloom_level: formData.bloom_level,
        ai_quality_score: formData.ai_quality_score,
        is_subjective: isSubj,
        question_type: formData.question_type,
        max_marks: parseFloat(formData.max_marks) || 1,
        reference_answer: isSubj ? (hasPassword ? encryptText(formData.reference_answer, examPassword) : formData.reference_answer) : null,
        rubric: (isSubj && formData.rubric) ? (hasPassword ? encryptText(formData.rubric, examPassword) : formData.rubric) : null
    };

    try {
      const res = await fetch(url, {
        method: method,
        headers: getHeaders(), 
        body: JSON.stringify(securePayload)
      });

      if (res.ok) {
        setMsg(editingQuestion ? "Question updated successfully!" : "Question added successfully!");
        if (onSuccess) onSuccess();
        resetForm();
      } else {
        const err = await res.json();
        setMsg(`Error: ${err.message}`);
      }
    } catch (e) { 
      console.error(e);
      setMsg("Network error saving question.");
    }
  };

  function resetForm() {
    if (clearEditing) clearEditing();
    setFormData({ 
      text: '', option_a: '', option_b: '', option_c: '', option_d: '', correct_option: 'A',
      topic: '', difficulty: 'Medium', bloom_level: 'Remember', ai_quality_score: 0.0, is_subjective: false, duplicate_score: 0.0,
      reference_answer: '', rubric: '', question_type: 'MCQ', max_marks: 1
    });
    setMsg('');
    setAiAssistData(null);
    setAiAnalysisData(null);
  }

  const isSubj = formData.question_type !== 'MCQ';

  return (
    <div style={{ flex: '2 1 400px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <h5 style={{ color: 'var(--accent)', margin: 0, fontWeight: 600 }}>
              {editingQuestion ? "Edit Question" : "Add New Question"}
            </h5>
            {editingQuestion && <button onClick={resetForm} className="btn btn-secondary btn-sm">Cancel Edit</button>}
        </div>
        
        {msg && (
          <div style={{ 
            padding: '0.75rem', 
            borderRadius: '6px', 
            fontSize: '0.875rem', 
            marginBottom: '1rem', 
            backgroundColor: msg.includes('Error') ? 'rgba(239, 68, 68, 0.15)' : 'rgba(34, 197, 94, 0.15)', 
            color: msg.includes('Error') ? 'var(--danger)' : 'var(--success)' 
          }}>
            {msg}
          </div>
        )}

        <form onSubmit={handleSubmit}>
            {/* Question Type Selector */}
            <div className="form-group mb-3">
                <label className="fw-bold small text-muted d-block mb-1">Question Type (14 Subjective Formats Supported)</label>
                <select 
                    name="question_type" 
                    value={formData.question_type} 
                    onChange={handleChange} 
                    className="form-control"
                    style={{ padding: '0.5rem 0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-primary)', width: '100%' }}
                >
                    {QUESTION_TYPES.map(t => (
                        <option key={t.value} value={t.value}>[{t.group}] {t.label}</option>
                    ))}
                </select>
            </div>

            {/* Question Text with Math Toolbar & AI Assist */}
            <div className="form-group mb-3">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                    <label className="fw-bold small text-muted m-0">Question Statement</label>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button type="button" className="btn btn-sm btn-outline-primary" onClick={handleAiAssist} disabled={isAssisting}>
                            <Sparkles size={14} className="me-1 inline" /> {isAssisting ? "Generating..." : "✨ AI Assist & Rubric"}
                        </button>
                        <button type="button" className="btn btn-sm btn-outline-secondary" onClick={handleAnalyze} disabled={isAnalyzing}>
                            {isAnalyzing ? "..." : "Analyze Quality"}
                        </button>
                    </div>
                </div>

                {/* Math helper toolbar for STEM/Math/Automata questions */}
                {['MATH_PROBLEM', 'DERIVATION', 'NUMERICAL', 'PROOF', 'DFA_NFA', 'STATE_TRANSITION'].includes(formData.question_type) && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', marginBottom: '0.5rem', background: 'var(--surface-secondary)', padding: '0.35rem', borderRadius: '4px' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', alignSelf: 'center', marginRight: '0.25rem' }}>Symbols:</span>
                    {MATH_SYMBOLS.map(sym => (
                      <button 
                        key={sym} 
                        type="button" 
                        onClick={() => insertMathSymbol(sym)}
                        style={{ padding: '0.15rem 0.4rem', fontSize: '0.75rem', border: '1px solid var(--border)', borderRadius: '3px', background: 'var(--surface)', cursor: 'pointer' }}
                      >
                        {sym}
                      </button>
                    ))}
                  </div>
                )}

                <textarea 
                    name="text" 
                    style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-primary)' }} 
                    rows="3" 
                    required 
                    placeholder="Enter the full question statement..."
                    value={formData.text} 
                    onChange={handleChange}
                ></textarea>
            </div>

            {/* AI Assistant Suggestions Panel (Collapsible with Human Approval) */}
            {aiAssistData && (
              <div style={{ background: 'rgba(59, 130, 246, 0.08)', border: '1px solid #3b82f6', borderRadius: '8px', padding: '1rem', marginBottom: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <h6 style={{ color: '#2563eb', margin: 0, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <Sparkles size={16} /> AI Suggested Improvements & Rubric
                  </h6>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => setAiAssistData(null)} style={{ padding: '0.2rem' }}>
                    <X size={16} />
                  </button>
                </div>

                {/* Identified Issues */}
                {aiAssistData.identified_issues && aiAssistData.identified_issues.length > 0 && (
                  <div style={{ marginBottom: '0.75rem' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Identified Quality Items:</span>
                    <ul style={{ margin: '0.25rem 0', paddingLeft: '1.25rem', fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                      {aiAssistData.identified_issues.map((iss, i) => (
                        <li key={i}>
                          <span className={`badge ${iss.severity === 'high' ? 'bg-danger' : 'bg-warning text-dark'}`} style={{ fontSize: '0.7rem', marginRight: '0.35rem' }}>
                            {iss.type}
                          </span>
                          {iss.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Suggested Version */}
                {aiAssistData.suggested_version && aiAssistData.suggested_version !== formData.text && (
                  <div style={{ marginBottom: '0.5rem', fontSize: '0.85rem' }}>
                    <strong style={{ color: '#1d4ed8' }}>Suggested Phrasing:</strong>
                    <div style={{ background: 'var(--surface)', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)', marginTop: '0.25rem' }}>
                      {aiAssistData.suggested_version}
                    </div>
                  </div>
                )}

                {/* Suggested Reference Answer */}
                {aiAssistData.suggested_reference_answer && (
                  <div style={{ marginBottom: '0.5rem', fontSize: '0.85rem' }}>
                    <strong style={{ color: '#1d4ed8' }}>Suggested Reference Solution:</strong>
                    <div style={{ background: 'var(--surface)', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)', marginTop: '0.25rem' }}>
                      {aiAssistData.suggested_reference_answer}
                    </div>
                  </div>
                )}

                {/* Suggested Rubric */}
                {aiAssistData.suggested_rubric && (
                  <div style={{ marginBottom: '0.75rem', fontSize: '0.85rem' }}>
                    <strong style={{ color: '#1d4ed8' }}>Generated Marking Rubric:</strong>
                    <pre style={{ background: 'var(--surface)', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)', marginTop: '0.25rem', whiteSpace: 'pre-wrap', fontSize: '0.8rem', margin: 0 }}>
                      {aiAssistData.suggested_rubric}
                    </pre>
                  </div>
                )}

                <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '0.75rem' }}>
                  <button type="button" className="btn btn-sm btn-secondary" onClick={() => setAiAssistData(null)}>
                    Discard
                  </button>
                  <button type="button" className="btn btn-sm btn-primary" onClick={handleApplyAiAssist}>
                    <CheckCircle size={14} className="me-1 inline" /> Apply to Form
                  </button>
                </div>
              </div>
            )}

            {/* AI Quality Analysis Panel */}
            {aiAnalysisData && (
                <QuestionAnalysisPanel 
                    aiData={aiAnalysisData}
                    onAccept={handleAcceptAnalysis}
                    onEdit={() => setAiAnalysisData(null)}
                    onIgnore={handleIgnoreAnalysis}
                />
            )}

            {/* Metadata Grid: Topic, Difficulty, Bloom, Marks */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem', background: 'var(--surface-secondary)', padding: '0.85rem', borderRadius: '8px', marginBottom: '1rem' }}>
                <div className="form-group m-0">
                    <label className="small text-muted mb-1">Topic / Module</label>
                    <input type="text" name="topic" value={formData.topic} onChange={handleChange} placeholder="e.g. Automata / Calculus" className="form-control form-control-sm" />
                </div>
                <div className="form-group m-0">
                    <label className="small text-muted mb-1">Difficulty</label>
                    <select name="difficulty" value={formData.difficulty} onChange={handleChange} className="form-control form-control-sm">
                        <option>Easy</option><option>Medium</option><option>Hard</option>
                    </select>
                </div>
                <div className="form-group m-0">
                    <label className="small text-muted mb-1">Bloom's Taxonomy</label>
                    <select name="bloom_level" value={formData.bloom_level} onChange={handleChange} className="form-control form-control-sm">
                        <option>Remember</option><option>Understand</option><option>Apply</option>
                        <option>Analyze</option><option>Evaluate</option><option>Create</option>
                    </select>
                </div>
                <div className="form-group m-0">
                    <label className="small text-muted mb-1">Maximum Marks</label>
                    <input type="number" min="0.5" step="0.5" name="max_marks" value={formData.max_marks} onChange={handleChange} className="form-control form-control-sm" />
                </div>
            </div>

            {/* Subjective Fields: Reference Answer & Evaluation Rubric */}
            {isSubj ? (
                <>
                <div className="form-group mb-3">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                      <label className="fw-bold small text-muted m-0">Expected Answer / Reference Solution (Required)</label>
                      <small className="text-secondary" style={{ fontSize: '0.75rem' }}>Used by AI engines (SymPy, Automata BFS, MiniLM) for grading</small>
                    </div>
                    <textarea 
                        name="reference_answer" 
                        rows="4" 
                        required 
                        className="form-control"
                        placeholder="Provide ideal solution, proof, derivation steps, equation, or table JSON..."
                        value={formData.reference_answer} 
                        onChange={handleChange}
                    ></textarea>
                </div>

                <div className="form-group mb-3">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                      <label className="fw-bold small text-muted m-0">Evaluation Rubric & Partial Marking Criteria (Optional)</label>
                      <small className="text-secondary" style={{ fontSize: '0.75rem' }}>Define step-wise marks distribution or concepts</small>
                    </div>
                    <textarea 
                        name="rubric" 
                        rows="3" 
                        className="form-control font-monospace"
                        placeholder="e.g. 1. Formulation: 2 marks&#10;2. Derivation steps: 2 marks&#10;3. Final answer: 1 mark"
                        value={formData.rubric} 
                        onChange={handleChange}
                        style={{ fontSize: '0.85rem' }}
                    ></textarea>
                </div>
                </>
            ) : (
                /* MCQ Option Fields */
                <>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
                    <div>
                      <label className="small text-muted">Option A</label>
                      <input type="text" name="option_a" required value={formData.option_a} onChange={handleChange} className="form-control form-control-sm" />
                    </div>
                    <div>
                      <label className="small text-muted">Option B</label>
                      <input type="text" name="option_b" required value={formData.option_b} onChange={handleChange} className="form-control form-control-sm" />
                    </div>
                    <div>
                      <label className="small text-muted">Option C</label>
                      <input type="text" name="option_c" required value={formData.option_c} onChange={handleChange} className="form-control form-control-sm" />
                    </div>
                    <div>
                      <label className="small text-muted">Option D</label>
                      <input type="text" name="option_d" required value={formData.option_d} onChange={handleChange} className="form-control form-control-sm" />
                    </div>
                </div>

                <div className="form-group mb-3">
                    <label className="fw-bold small text-muted d-block mb-1">Correct Answer</label>
                    <select name="correct_option" value={formData.correct_option} onChange={handleChange} className="form-control form-control-sm">
                        <option value="A">Option A</option>
                        <option value="B">Option B</option>
                        <option value="C">Option C</option>
                        <option value="D">Option D</option>
                    </select>
                </div>
                </>
            )}

            <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '0.75rem', fontWeight: 600 }}>
                {editingQuestion 
                    ? (hasPassword ? "🔒 Encrypt & Update Question" : "Update Question")
                    : (hasPassword ? "🔒 Encrypt & Add Question" : "Add Question")}
            </button>
        </form>
    </div>
  );
};

export default AddQuestionForm;
