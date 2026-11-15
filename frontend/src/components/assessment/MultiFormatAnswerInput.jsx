import React, { useState, useEffect, useRef } from 'react';
import { Type, Calculator, GitCommit, UploadCloud, CheckCircle2, AlertTriangle, FileText } from 'lucide-react';

const MultiFormatAnswerInput = ({ 
    question, 
    examId, 
    initialAnswer, 
    onAnswerChange, 
    apiBaseUrl, 
    getHeaders 
}) => {
    // Determine initial format
    const [activeTab, setActiveTab] = useState(() => {
        if (typeof initialAnswer === 'object' && initialAnswer?.answer_type) {
            return initialAnswer.answer_type;
        }
        return 'TEXT';
    });

    // Content states
    const [textContent, setTextContent] = useState(() => {
        if (typeof initialAnswer === 'string') return initialAnswer;
        return initialAnswer?.text || '';
    });
    const [mathContent, setMathContent] = useState(() => {
        return initialAnswer?.answer_type === 'MATH_EQUATION' ? (initialAnswer.text || '') : '';
    });
    
    // Automata State
    const [automataData, setAutomataData] = useState(() => {
        if (initialAnswer?.structured_answer) {
            try {
                return JSON.parse(initialAnswer.structured_answer);
            } catch (e) {}
        }
        return {
            type: 'DFA',
            states: ['q0', 'q1'],
            alphabet: ['0', '1'],
            initial_state: 'q0',
            final_states: ['q1'],
            transitions: [
                { from: 'q0', symbol: '0', to: 'q0' },
                { from: 'q0', symbol: '1', to: 'q1' }
            ]
        };
    });

    // File State
    const [uploadedFile, setUploadedFile] = useState(() => {
        if (initialAnswer?.file_reference) {
            return {
                url: initialAnswer.file_url || initialAnswer.file_reference,
                filename: initialAnswer.filename || 'Uploaded File',
                hash: initialAnswer.file_hash
            };
        }
        return null;
    });

    const [saveStatus, setSaveStatus] = useState('saved'); // 'saving', 'saved', 'error'
    const [lastSavedTime, setLastSavedTime] = useState(null);
    const [pasteWarning, setPasteWarning] = useState('');
    const autosaveTimerRef = useRef(null);

    // Sync state up to parent
    const triggerParentUpdate = (type, text, structured, fileObj) => {
        const payload = {
            answer_type: type,
            text: text,
            structured_answer: structured ? JSON.stringify(structured) : null,
            file_reference: fileObj?.reference || null,
            file_url: fileObj?.url || null,
            file_hash: fileObj?.hash || null,
            filename: fileObj?.filename || null
        };
        onAnswerChange(question.id, payload);

        // Schedule backend autosave (debounced by 1.5 seconds)
        if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
        setSaveStatus('saving');
        autosaveTimerRef.current = setTimeout(async () => {
            try {
                const res = await fetch(`${apiBaseUrl}/exams/${examId}/answer_autosave`, {
                    method: 'POST',
                    headers: { ...getHeaders(), 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        question_id: question.id,
                        answer_text: text,
                        answer_type: type,
                        structured_answer: structured ? JSON.stringify(structured) : null,
                        file_reference: fileObj?.reference || null,
                        file_hash: fileObj?.hash || null
                    })
                });
                if (res.ok) {
                    setSaveStatus('saved');
                    setLastSavedTime(new Date().toLocaleTimeString());
                } else {
                    setSaveStatus('error');
                }
            } catch (err) {
                console.error("Autosave error:", err);
                setSaveStatus('error');
            }
        }, 1500);
    };

    // Paste event interceptor
    const handlePaste = async (e) => {
        const pastedText = e.clipboardData.getData('text');
        const charCount = pastedText ? pastedText.length : 0;
        if (charCount > 50) {
            setPasteWarning(`Paste detected (${charCount} characters). Activity logged.`);
            setTimeout(() => setPasteWarning(''), 4000);
            try {
                await fetch(`${apiBaseUrl}/exams/${examId}/integrity_event`, {
                    method: 'POST',
                    headers: { ...getHeaders(), 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        event_type: 'PASTE_DETECTED',
                        question_id: question.id,
                        character_count: charCount,
                        metadata: { length: charCount }
                    })
                });
            } catch (err) {}
        }
    };

    // Math quick symbols
    const insertMathSymbol = (sym) => {
        const next = mathContent + sym;
        setMathContent(next);
        triggerParentUpdate('MATH_EQUATION', next, null, uploadedFile);
    };

    // Automata Helpers
    const handleAutomataTypeChange = (t) => {
        const updated = { ...automataData, type: t };
        setAutomataData(updated);
        triggerParentUpdate('AUTOMATA_GRAPH', `[Automata ${t}]`, updated, uploadedFile);
    };

    const addTransition = () => {
        const updated = {
            ...automataData,
            transitions: [
                ...automataData.transitions,
                { from: automataData.states[0] || 'q0', symbol: automataData.alphabet[0] || '0', to: automataData.states[0] || 'q0' }
            ]
        };
        setAutomataData(updated);
        triggerParentUpdate('AUTOMATA_GRAPH', `[Automata ${automataData.type}]`, updated, uploadedFile);
    };

    const updateTransition = (idx, field, val) => {
        const nextTransitions = [...automataData.transitions];
        nextTransitions[idx] = { ...nextTransitions[idx], [field]: val };
        const updated = { ...automataData, transitions: nextTransitions };
        setAutomataData(updated);
        triggerParentUpdate('AUTOMATA_GRAPH', `[Automata ${automataData.type}]`, updated, uploadedFile);
    };

    const removeTransition = (idx) => {
        const nextTransitions = automataData.transitions.filter((_, i) => i !== idx);
        const updated = { ...automataData, transitions: nextTransitions };
        setAutomataData(updated);
        triggerParentUpdate('AUTOMATA_GRAPH', `[Automata ${automataData.type}]`, updated, uploadedFile);
    };

    // File Upload Handler
    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        setSaveStatus('saving');
        
        try {
            const res = await fetch(`${apiBaseUrl}/exams/${examId}/upload_answer_file`, {
                method: 'POST',
                headers: { 'Authorization': getHeaders()['Authorization'] },
                body: formData
            });
            if (res.ok) {
                const data = await res.json();
                const fileObj = {
                    reference: data.file_reference,
                    url: data.file_url,
                    filename: data.filename,
                    hash: data.file_hash
                };
                setUploadedFile(fileObj);
                setSaveStatus('saved');
                setLastSavedTime(new Date().toLocaleTimeString());
                triggerParentUpdate(activeTab, `[File Attached: ${file.name}]`, null, fileObj);
            } else {
                const err = await res.json();
                alert(`Upload failed: ${err.message}`);
                setSaveStatus('error');
            }
        } catch (err) {
            console.error("Upload error:", err);
            setSaveStatus('error');
        }
    };

    return (
        <div className="multi-format-answer-container border rounded p-3 bg-light">
            {/* Header: Mode Selector & Autosave Status */}
            <div className="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom">
                <div className="btn-group btn-group-sm" role="group">
                    <button 
                        type="button" 
                        className={`btn ${activeTab === 'TEXT' ? 'btn-primary' : 'btn-outline-secondary'}`}
                        onClick={() => { setActiveTab('TEXT'); triggerParentUpdate('TEXT', textContent, null, uploadedFile); }}
                    >
                        <Type size={14} className="me-1" /> Text Answer
                    </button>
                    <button 
                        type="button" 
                        className={`btn ${activeTab === 'MATH_EQUATION' ? 'btn-primary' : 'btn-outline-secondary'}`}
                        onClick={() => { setActiveTab('MATH_EQUATION'); triggerParentUpdate('MATH_EQUATION', mathContent, null, uploadedFile); }}
                    >
                        <Calculator size={14} className="me-1" /> Math / LaTeX
                    </button>
                    <button 
                        type="button" 
                        className={`btn ${activeTab === 'AUTOMATA_GRAPH' ? 'btn-primary' : 'btn-outline-secondary'}`}
                        onClick={() => { setActiveTab('AUTOMATA_GRAPH'); triggerParentUpdate('AUTOMATA_GRAPH', `[Automata ${automataData.type}]`, automataData, uploadedFile); }}
                    >
                        <GitCommit size={14} className="me-1" /> DFA / NFA
                    </button>
                    <button 
                        type="button" 
                        className={`btn ${activeTab === 'FILE_UPLOAD' ? 'btn-primary' : 'btn-outline-secondary'}`}
                        onClick={() => { setActiveTab('FILE_UPLOAD'); triggerParentUpdate('FILE_UPLOAD', uploadedFile?.filename || '[File Attached]', null, uploadedFile); }}
                    >
                        <UploadCloud size={14} className="me-1" /> Upload PDF / Image
                    </button>
                </div>

                <div className="d-flex align-items-center gap-2 small">
                    {saveStatus === 'saving' && (
                        <span className="text-muted"><span className="spinner-border spinner-border-sm me-1"></span>Saving...</span>
                    )}
                    {saveStatus === 'saved' && (
                        <span className="text-success"><CheckCircle2 size={14} className="me-1 inline" />Saved {lastSavedTime ? `at ${lastSavedTime}` : ''}</span>
                    )}
                    {saveStatus === 'error' && (
                        <span className="text-danger"><AlertTriangle size={14} className="me-1 inline" />Autosave Failed</span>
                    )}
                </div>
            </div>

            {pasteWarning && (
                <div className="alert alert-warning py-1 px-2 small mb-2 d-flex align-items-center">
                    <AlertTriangle size={14} className="me-1 text-warning" /> {pasteWarning}
                </div>
            )}

            {/* TAB 1: PLAIN / RICH TEXT */}
            {activeTab === 'TEXT' && (
                <div>
                    <textarea
                        className="form-control"
                        rows="6"
                        placeholder="Type your explanation or descriptive answer here..."
                        value={textContent}
                        onPaste={handlePaste}
                        onChange={(e) => {
                            setTextContent(e.target.value);
                            triggerParentUpdate('TEXT', e.target.value, null, uploadedFile);
                        }}
                    ></textarea>
                </div>
            )}

            {/* TAB 2: MATHEMATICAL / LATEX EQUATIONS */}
            {activeTab === 'MATH_EQUATION' && (
                <div>
                    {/* Math Quick Toolbar */}
                    <div className="btn-toolbar gap-1 mb-2">
                        {['x^2', '\\frac{a}{b}', '\\sqrt{x}', '\\int', '\\sum', '\\times', '\\pm', '\\le', '\\ge', '\\pi', '\\alpha', '\\beta'].map((sym) => (
                            <button
                                key={sym}
                                type="button"
                                className="btn btn-sm btn-white bg-white border px-2 py-0"
                                onClick={() => insertMathSymbol(sym)}
                            >
                                {sym}
                            </button>
                        ))}
                    </div>
                    <textarea
                        className="form-control font-monospace"
                        rows="4"
                        placeholder="e.g. (x - 2)(x - 3) = 0 or \int_{0}^{\pi} \sin(x)dx"
                        value={mathContent}
                        onPaste={handlePaste}
                        onChange={(e) => {
                            setMathContent(e.target.value);
                            triggerParentUpdate('MATH_EQUATION', e.target.value, null, uploadedFile);
                        }}
                    ></textarea>
                    {/* Real-time Math Preview */}
                    {mathContent && (
                        <div className="mt-2 p-2 bg-white rounded border">
                            <small className="text-muted fw-bold d-block mb-1">Rendered Expression Preview:</small>
                            <span className="fs-5 text-primary font-monospace">{mathContent}</span>
                        </div>
                    )}
                </div>
            )}

            {/* TAB 3: DFA / NFA STRUCTURED BUILDER */}
            {activeTab === 'AUTOMATA_GRAPH' && (
                <div>
                    <div className="row g-2 mb-2">
                        <div className="col-md-3">
                            <label className="small fw-bold text-muted">Automaton Type</label>
                            <select 
                                className="form-select form-select-sm"
                                value={automataData.type}
                                onChange={(e) => handleAutomataTypeChange(e.target.value)}
                            >
                                <option value="DFA">DFA (Deterministic)</option>
                                <option value="NFA">NFA (Non-Deterministic)</option>
                            </select>
                        </div>
                        <div className="col-md-3">
                            <label className="small fw-bold text-muted">States Q (comma separated)</label>
                            <input 
                                type="text" 
                                className="form-control form-control-sm" 
                                value={automataData.states.join(', ')}
                                onChange={(e) => {
                                    const states = e.target.value.split(',').map(s => s.trim()).filter(Boolean);
                                    const updated = { ...automataData, states };
                                    setAutomataData(updated);
                                    triggerParentUpdate('AUTOMATA_GRAPH', `[Automata ${updated.type}]`, updated, uploadedFile);
                                }}
                            />
                        </div>
                        <div className="col-md-2">
                            <label className="small fw-bold text-muted">Alphabet Σ</label>
                            <input 
                                type="text" 
                                className="form-control form-control-sm" 
                                value={automataData.alphabet.join(', ')}
                                onChange={(e) => {
                                    const alphabet = e.target.value.split(',').map(s => s.trim()).filter(Boolean);
                                    const updated = { ...automataData, alphabet };
                                    setAutomataData(updated);
                                    triggerParentUpdate('AUTOMATA_GRAPH', `[Automata ${updated.type}]`, updated, uploadedFile);
                                }}
                            />
                        </div>
                        <div className="col-md-2">
                            <label className="small fw-bold text-muted">Start State q0</label>
                            <input 
                                type="text" 
                                className="form-control form-control-sm" 
                                value={automataData.initial_state}
                                onChange={(e) => {
                                    const updated = { ...automataData, initial_state: e.target.value.trim() };
                                    setAutomataData(updated);
                                    triggerParentUpdate('AUTOMATA_GRAPH', `[Automata ${updated.type}]`, updated, uploadedFile);
                                }}
                            />
                        </div>
                        <div className="col-md-2">
                            <label className="small fw-bold text-muted">Final States F</label>
                            <input 
                                type="text" 
                                className="form-control form-control-sm" 
                                value={automataData.final_states.join(', ')}
                                onChange={(e) => {
                                    const final_states = e.target.value.split(',').map(s => s.trim()).filter(Boolean);
                                    const updated = { ...automataData, final_states };
                                    setAutomataData(updated);
                                    triggerParentUpdate('AUTOMATA_GRAPH', `[Automata ${updated.type}]`, updated, uploadedFile);
                                }}
                            />
                        </div>
                    </div>

                    {/* Transition Table */}
                    <div className="card p-2 bg-white border">
                        <div className="d-flex justify-content-between align-items-center mb-2">
                            <small className="fw-bold text-muted">Transition Function δ(q, σ) → q'</small>
                            <button type="button" className="btn btn-xs btn-outline-primary" onClick={addTransition}>
                                + Add Transition
                            </button>
                        </div>
                        <div className="table-responsive">
                            <table className="table table-sm table-bordered align-middle mb-0">
                                <thead className="table-light">
                                    <tr>
                                        <th>From State</th>
                                        <th>Input Symbol</th>
                                        <th>To State</th>
                                        <th style={{ width: '50px' }}></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {automataData.transitions.map((t, idx) => (
                                        <tr key={idx}>
                                            <td>
                                                <input 
                                                    type="text" 
                                                    className="form-control form-control-sm border-0" 
                                                    value={t.from}
                                                    onChange={(e) => updateTransition(idx, 'from', e.target.value)}
                                                />
                                            </td>
                                            <td>
                                                <input 
                                                    type="text" 
                                                    className="form-control form-control-sm border-0" 
                                                    value={t.symbol}
                                                    onChange={(e) => updateTransition(idx, 'symbol', e.target.value)}
                                                />
                                            </td>
                                            <td>
                                                <input 
                                                    type="text" 
                                                    className="form-control form-control-sm border-0" 
                                                    value={t.to}
                                                    onChange={(e) => updateTransition(idx, 'to', e.target.value)}
                                                />
                                            </td>
                                            <td className="text-center">
                                                <button 
                                                    type="button" 
                                                    className="btn btn-xs text-danger"
                                                    onClick={() => removeTransition(idx)}
                                                >
                                                    ✕
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}

            {/* TAB 4: FILE UPLOAD (PDF / IMAGE) */}
            {activeTab === 'FILE_UPLOAD' && (
                <div className="card p-3 bg-white text-center border-dashed">
                    <input 
                        type="file" 
                        id={`file_input_${question.id}`} 
                        className="d-none" 
                        accept=".pdf,.png,.jpg,.jpeg,.webp"
                        onChange={handleFileUpload}
                    />
                    <label htmlFor={`file_input_${question.id}`} style={{ cursor: 'pointer' }}>
                        <UploadCloud size={32} className="text-primary mb-2" />
                        <h6 className="fw-bold m-0">Click to upload answer file (PDF or Scanned Solution)</h6>
                        <small className="text-muted d-block">Supported formats: PDF (up to 10 pages), PNG, JPG (Max 10 MB)</small>
                    </label>

                    {uploadedFile && (
                        <div className="alert alert-success mt-3 py-2 px-3 small d-flex justify-content-between align-items-center">
                            <span className="d-flex align-items-center">
                                <FileText size={16} className="me-2 text-success" />
                                <strong>{uploadedFile.filename}</strong> (Hash: {uploadedFile.hash?.substring(0, 10)}...)
                            </span>
                            <a href={uploadedFile.url} target="_blank" rel="noreferrer" className="btn btn-xs btn-outline-success">
                                View File ↗
                            </a>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default MultiFormatAnswerInput;
