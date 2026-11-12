import React, { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import { encryptText, hashText } from '../utils/encryption'; //  IMPORT ENCRYPTION & HASHING
import QuestionAnalysisPanel from './QuestionAnalysisPanel';

const AddQuestionForm = ({ examId, hasPassword, examPassword, onCancel, editingQuestion, onSuccess, clearEditing }) => {
  const { API_BASE_URL, getHeaders } = useAuth();
  
  const [formData, setFormData] = useState({
    text: '', option_a: '', option_b: '', option_c: '', option_d: '', correct_option: 'A',
    topic: '', difficulty: 'Medium', bloom_level: 'Remember', ai_quality_score: 0.0, is_subjective: false, duplicate_score: 0.0,
    reference_answer: '', question_type: 'MCQ', max_marks: 1
  });
  const [msg, setMsg] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [aiAnalysisData, setAiAnalysisData] = useState(null);

  // Load editing question if provided
  useEffect(() => {
    if (editingQuestion) {
      setFormData({
        text: editingQuestion.text,
        option_a: editingQuestion.options?.A || '',
        option_b: editingQuestion.options?.B || '',
        option_c: editingQuestion.options?.C || '',
        option_d: editingQuestion.options?.D || '',
        correct_option: 'A', // Requires re-selection since backend stores hash
        topic: editingQuestion.topic || '',
        difficulty: editingQuestion.difficulty || 'Medium',
        bloom_level: editingQuestion.bloom_level || 'Remember',
        ai_quality_score: editingQuestion.ai_quality_score || 0.0,
        is_subjective: editingQuestion.is_subjective || (editingQuestion.question_type === 'SUBJECTIVE'),
        question_type: editingQuestion.question_type || (editingQuestion.is_subjective ? 'SUBJECTIVE' : 'MCQ'),
        duplicate_score: 0.0,
        reference_answer: editingQuestion.reference_answer || '',
        max_marks: editingQuestion.max_marks || 1
      });
      setMsg("✏️ Editing Question (Note: Re-select the Correct Answer below)");
    } else {
      resetForm();
    }
  }, [editingQuestion]);

  // 2. Handle Form Change
  const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });

  // ✨ 2b. Handle AI Analysis
  const handleAnalyze = async () => {
    if (!formData.text) {
      setMsg(" Please enter a question text to analyze.");
      return;
    }
    setIsAnalyzing(true);
    setAiAnalysisData(null);
    try {
      // Calls QIS pipeline for comprehensive classification & quality analysis
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
        setMsg(aiData.review?.required ? " AI suggests manual review." : " AI Analysis Complete!");
      } else {
        setMsg(" Error connecting to AI Service.");
      }
    } catch (e) {
      console.error(e);
      setMsg(" Error connecting to AI Service.");
    }
    setIsAnalyzing(false);
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
      is_subjective: (aiAnalysisData.classification?.question_type?.label === 'SUBJECTIVE' || prev.is_subjective),
      duplicate_score: aiAnalysisData.duplicate?.risk || 0.0
    }));
    setAiAnalysisData(null);
    setMsg(" AI Metadata accepted and applied.");
  };

  const handleIgnoreAnalysis = () => {
    setAiAnalysisData(null);
    setMsg("ℹ️ AI suggestions ignored.");
  };

  // 3. Encrypt & Submit (Add or Update)
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // SECURITY CHECK: Require password
    if (hasPassword && !examPassword) {
        setMsg(" Error: You must enter an Encryption Key to secure questions!");
        return;
    }
    
    const isSubj = formData.question_type === 'SUBJECTIVE';
    if (isSubj && (!formData.reference_answer || formData.reference_answer.trim() === '')) {
        setMsg(" Error: Reference answer is required for subjective questions.");
        return;
    }

    const url = editingQuestion 
      ? `${API_BASE_URL}/exams/question/${editingQuestion.id}` // PUT
      : `${API_BASE_URL}/exams/${examId}/questions`;  // POST
    
    const method = editingQuestion ? 'PUT' : 'POST';

    //  SECURE PAYLOAD: Encrypt text and Hash the answer before sending
    const securePayload = {
        text: hasPassword ? encryptText(formData.text, examPassword) : formData.text,
        option_a: hasPassword ? encryptText(formData.option_a, examPassword) : formData.option_a,
        option_b: hasPassword ? encryptText(formData.option_b, examPassword) : formData.option_b,
        option_c: hasPassword ? encryptText(formData.option_c, examPassword) : formData.option_c,
        option_d: hasPassword ? encryptText(formData.option_d, examPassword) : formData.option_d,
        correct_option_hash: hashText(String(formData.correct_option).trim().toUpperCase()), //  ONE-WAY HASH
        topic: formData.topic,
        difficulty: formData.difficulty,
        bloom_level: formData.bloom_level,
        ai_quality_score: formData.ai_quality_score,
        is_subjective: formData.question_type === 'SUBJECTIVE',
        question_type: formData.question_type,
        max_marks: parseFloat(formData.max_marks) || 1,
        reference_answer: (formData.question_type === 'SUBJECTIVE') ? (hasPassword ? encryptText(formData.reference_answer, examPassword) : formData.reference_answer) : null
    };

    try {
      const res = await fetch(url, {
        method: method,
        headers: getHeaders(), 
        body: JSON.stringify(securePayload) // Send encrypted data
      });

      if (res.ok) {
        setMsg(editingQuestion ? " Encrypted & Updated!" : " Encrypted & Added!");
        if (onSuccess) onSuccess();
        resetForm();
      } else {
        const err = await res.json();
        setMsg(` Error: ${err.message}`);
      }
    } catch (e) { console.error(e); }
  };

  function resetForm() {
    if (clearEditing) clearEditing();
    setFormData({ 
      text: '', option_a: '', option_b: '', option_c: '', option_d: '', correct_option: 'A',
      topic: '', difficulty: 'Medium', bloom_level: 'Remember', ai_quality_score: 0.0, is_subjective: false, duplicate_score: 0.0,
      reference_answer: '', question_type: 'MCQ', max_marks: 1
    });
    setMsg('');
  };

  return (
    <div style={{ flex: '2 1 400px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h5 style={{ color: 'var(--accent)', margin: 0 }}>{editingQuestion ? "Edit Question" : "Add New Question"}</h5>
            {editingQuestion && <button onClick={resetForm} className="btn btn-secondary btn-sm">Cancel Edit</button>}
        </div>
        
        {msg && <div style={{ padding: '0.75rem', borderRadius: '6px', fontSize: '0.875rem', marginBottom: '1rem', backgroundColor: msg.includes('Error') ? 'rgba(239, 68, 68, 0.15)' : 'rgba(34, 197, 94, 0.15)', color: msg.includes('Error') ? 'var(--danger)' : 'var(--success)' }}>{msg}</div>}

        <form onSubmit={handleSubmit}>
            <div className="form-group mb-4">
                <label>Question Text</label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <textarea 
                        name="text" style={{ flex: 1, padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-primary)' }} rows="3" required placeholder="Type question here..."
                        value={formData.text} onChange={handleChange}
                    ></textarea>
                    <button type="button" className="btn btn-secondary" onClick={handleAnalyze} disabled={isAnalyzing}>
                        {isAnalyzing ? "..." : "✨ AI Analyze"}
                    </button>
                </div>
            </div>

            {aiAnalysisData ? (
                <QuestionAnalysisPanel 
                    aiData={aiAnalysisData}
                    onAccept={handleAcceptAnalysis}
                    onEdit={() => setAiAnalysisData(null)}
                    onIgnore={handleIgnoreAnalysis}
                />
            ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', background: 'var(--surface-secondary)', padding: '1rem', borderRadius: '8px', marginBottom: '1rem' }}>
                    <div className="form-group m-0">
                        <label>Topic</label>
                        <input type="text" name="topic" value={formData.topic} onChange={handleChange} placeholder="e.g. Databases" />
                    </div>
                    <div className="form-group m-0">
                        <label>Difficulty</label>
                        <select name="difficulty" value={formData.difficulty} onChange={handleChange}>
                            <option>Easy</option><option>Medium</option><option>Hard</option>
                        </select>
                    </div>
                    <div className="form-group m-0">
                        <label>Bloom Level</label>
                        <select name="bloom_level" value={formData.bloom_level} onChange={handleChange}>
                            <option>Remember</option><option>Understand</option><option>Apply</option>
                            <option>Analyze</option><option>Evaluate</option><option>Create</option>
                        </select>
                    </div>
                    <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
                        <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>AI Quality: <strong style={{ color: formData.ai_quality_score < 0.6 ? 'var(--danger)' : 'var(--success)' }}>{formData.ai_quality_score}/1.0</strong></span>
                        {formData.duplicate_score > 0 && <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--warning)' }}>Duplicate Risk: {(formData.duplicate_score * 100).toFixed(0)}%</span>}
                        <div className="form-group m-0">
                            <label>Question Type</label>
                            <select name="question_type" value={formData.question_type} onChange={handleChange} style={{ padding: '0.375rem 0.75rem', borderRadius: '4px', border: '1px solid var(--border)' }}>
                                <option value="MCQ">MCQ (Multiple Choice)</option>
                                <option value="SUBJECTIVE">Subjective</option>
                            </select>
                        </div>
                        <div className="form-group m-0" style={{ maxWidth: '100px' }}>
                            <label>Marks</label>
                            <input type="number" min="1" step="0.5" name="max_marks" value={formData.max_marks} onChange={handleChange} style={{ padding: '0.375rem 0.75rem', borderRadius: '4px', border: '1px solid var(--border)', width: '100%' }} />
                        </div>
                    </div>
                </div>
            )}

            {formData.question_type === 'SUBJECTIVE' ? (
                <div className="form-group mb-4">
                    <label>Reference Answer (For AI Grading)</label>
                    <textarea 
                        name="reference_answer" rows="4" required placeholder="Type the ideal answer here. The AI will use this to grade students."
                        value={formData.reference_answer} onChange={handleChange}
                    ></textarea>
                </div>
            ) : (
                <>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                    <input type="text" name="option_a" placeholder="Option A" required value={formData.option_a} onChange={handleChange} />
                    <input type="text" name="option_b" placeholder="Option B" required value={formData.option_b} onChange={handleChange} />
                    <input type="text" name="option_c" placeholder="Option C" required value={formData.option_c} onChange={handleChange} />
                    <input type="text" name="option_d" placeholder="Option D" required value={formData.option_d} onChange={handleChange} />
                </div>

                <div className="form-group mb-4">
                    <label>Correct Answer</label>
                    <select name="correct_option" value={formData.correct_option} onChange={handleChange}>
                        <option value="A">Option A</option>
                        <option value="B">Option B</option>
                        <option value="C">Option C</option>
                        <option value="D">Option D</option>
                    </select>
                </div>
                </>
            )}

            <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '0.75rem' }}>
                {editingQuestion 
                    ? (hasPassword ? " Encrypt & Update Question" : "Update Question")
                    : (hasPassword ? " Encrypt & Add Question" : "Add Question")}
            </button>
        </form>
    </div>
  );
};

export default AddQuestionForm;