import React, { useState, useEffect, useRef } from 'react';
import { Type, Calculator, GitCommit, UploadCloud, CheckCircle2, AlertTriangle, FileText, Table as TableIcon } from 'lucide-react';
import AutomataDiagramViewer from './AutomataDiagramViewer';

const MultiFormatAnswerInput = ({ 
    question, 
    examId, 
    initialAnswer, 
    onAnswerChange, 
    apiBaseUrl, 
    getHeaders 
}) => {
    // Determine initial format based on question type or previous answer
    const getInitialTab = () => {
        if (typeof initialAnswer === 'object' && initialAnswer?.answer_type) {
            return initialAnswer.answer_type;
        }
        const qType = question?.question_type;
        if (['MATH_PROBLEM', 'DERIVATION', 'NUMERICAL', 'PROOF'].includes(qType)) return 'MATH_EQUATION';
        if (['DFA_NFA', 'STATE_TRANSITION', 'GRAPH'].includes(qType)) return 'AUTOMATA_GRAPH';
        if (qType === 'TABLE') return 'TABLE';
        if (qType === 'FLOWCHART') return 'FILE_UPLOAD';
        return 'TEXT';
    };

    const [activeTab, setActiveTab] = useState(getInitialTab);
    const [dfaSubView, setDfaSubView] = useState('both'); // 'both' | 'editor' | 'graph'

    // Content states
    const [textContent, setTextContent] = useState(() => {
        if (typeof initialAnswer === 'string') return initialAnswer;
        return initialAnswer?.text || '';
    });
    const [mathContent, setMathContent] = useState(() => {
        return initialAnswer?.answer_type === 'MATH_EQUATION' ? (initialAnswer.text || '') : '';
    });
    
    // Structured Table State
    const [tableData, setTableData] = useState(() => {
        if (initialAnswer?.structured_answer) {
            try {
                const parsed = JSON.parse(initialAnswer.structured_answer);
                if (parsed && (parsed.type === 'TABLE' || parsed.table || parsed.rows)) {
                    return {
                        headers: parsed.headers || ['Col 1', 'Col 2', 'Col 3'],
                        rows: parsed.rows || [['', '', ''], ['', '', '']]
                    };
                }
            } catch (e) {}
        }
        return {
            headers: ['Col 1', 'Col 2', 'Col 3'],
            rows: [
                ['', '', ''],
                ['', '', '']
            ]
        };
    });

    // Automata DFA/NFA state - default is blank, never revealing the solution
    const [automataData, setAutomataData] = useState(() => {
        if (initialAnswer?.structured_answer) {
            try {
                const parsed = JSON.parse(initialAnswer.structured_answer);
                if (parsed && (parsed.type === 'DFA' || parsed.type === 'NFA' || parsed.states || parsed.transitions)) {
                    return {
                        type: parsed.type || 'DFA',
                        states: parsed.states || ['q0'],
                        alphabet: parsed.alphabet || ['0', '1'],
                        initial_state: parsed.initial_state || parsed.start_state || 'q0',
                        final_states: parsed.final_states || parsed.accept_states || [],
                        transitions: parsed.transitions || []
                    };
                }
            } catch (e) {}
        }
        return {
            type: 'DFA',
            states: ['q0'],
            alphabet: ['0', '1'],
            initial_state: 'q0',
            final_states: [],
            transitions: []
        };
    });

    // File upload state
    const [uploadedFile, setUploadedFile] = useState(() => {
        if (initialAnswer?.file_reference) {
            return {
                url: `${apiBaseUrl.replace('/api', '')}/static/uploads/answers/${initialAnswer.file_reference.split(/[/\\]/).pop()}`,
                filename: initialAnswer.file_reference.split(/[/\\]/).pop(),
                hash: null
            };
        }
        return null;
    });

    // Autosave & validation states
    const [saveStatus, setSaveStatus] = useState('idle'); // 'idle' | 'saving' | 'saved' | 'error'
    const [lastSavedTime, setLastSavedTime] = useState(null);
    const [pasteWarning, setPasteWarning] = useState(null);
    const autosaveTimerRef = useRef(null);

    // Sync state when question changes (critical for single question navigation)
    useEffect(() => {
        if (!question) return;

        let detectedTab = 'TEXT';
        if (initialAnswer && typeof initialAnswer === 'object' && initialAnswer.answer_type) {
            detectedTab = initialAnswer.answer_type;
        } else {
            const qType = question.question_type;
            if (['MATH_PROBLEM', 'DERIVATION', 'NUMERICAL', 'PROOF'].includes(qType)) detectedTab = 'MATH_EQUATION';
            else if (['DFA_NFA', 'STATE_TRANSITION', 'GRAPH'].includes(qType)) detectedTab = 'AUTOMATA_GRAPH';
            else if (qType === 'TABLE') detectedTab = 'TABLE';
            else if (qType === 'FLOWCHART') detectedTab = 'FILE_UPLOAD';
        }
        setActiveTab(detectedTab);

        if (typeof initialAnswer === 'string') {
            setTextContent(initialAnswer);
        } else if (initialAnswer?.text) {
            setTextContent(initialAnswer.text);
        } else {
            setTextContent('');
        }

        if (initialAnswer?.answer_type === 'MATH_EQUATION' && initialAnswer?.text) {
            setMathContent(initialAnswer.text);
        } else {
            setMathContent('');
        }

        // Automata: load student's saved answer or reset to clean blank state
        if (initialAnswer?.structured_answer) {
            try {
                const parsed = JSON.parse(initialAnswer.structured_answer);
                if (parsed && (parsed.type === 'DFA' || parsed.type === 'NFA' || parsed.states || parsed.transitions)) {
                    setAutomataData({
                        type: parsed.type || 'DFA',
                        states: parsed.states || ['q0'],
                        alphabet: parsed.alphabet || ['0', '1'],
                        initial_state: parsed.initial_state || parsed.start_state || 'q0',
                        final_states: parsed.final_states || parsed.accept_states || [],
                        transitions: parsed.transitions || []
                    });
                }
            } catch (e) {}
        } else {
            setAutomataData({
                type: 'DFA',
                states: ['q0'],
                alphabet: ['0', '1'],
                initial_state: 'q0',
                final_states: [],
                transitions: []
            });
        }

        // Table
        if (initialAnswer?.structured_answer) {
            try {
                const parsed = JSON.parse(initialAnswer.structured_answer);
                if (parsed && (parsed.type === 'TABLE' || parsed.table || parsed.rows)) {
                    setTableData({
                        headers: parsed.headers || ['Col 1', 'Col 2', 'Col 3'],
                        rows: parsed.rows || [['', '', ''], ['', '', '']]
                    });
                }
            } catch (e) {}
        } else {
            setTableData({
                headers: ['Col 1', 'Col 2', 'Col 3'],
                rows: [['', '', ''], ['', '', '']]
            });
        }

        // Upload
        if (initialAnswer?.file_reference) {
            setUploadedFile({
                url: `${apiBaseUrl.replace('/api', '')}/static/uploads/answers/${initialAnswer.file_reference.split(/[/\\]/).pop()}`,
                filename: initialAnswer.file_reference.split(/[/\\]/).pop(),
                hash: null
            });
        } else {
            setUploadedFile(null);
        }
    }, [question?.id]);

    // Keep parent updated
    const triggerParentUpdate = (type, textVal, structVal, fileVal) => {
        setSaveStatus('saving');
        
        let structuredPayload = null;
        if (structVal) {
            structuredPayload = typeof structVal === 'string' ? structVal : JSON.stringify(structVal);
        }

        const payload = {
            answer_type: type,
            text: textVal,
            structured_answer: structuredPayload,
            file_reference: fileVal ? fileVal.filename : null,
            uploaded_file: fileVal
        };

        if (onAnswerChange) {
            onAnswerChange(payload);
        }

        // Debounced visual save indicator
        if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
        autosaveTimerRef.current = setTimeout(() => {
            setSaveStatus('saved');
            setLastSavedTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
        }, 800);
    };

    // Paste detection event logger
    const handlePaste = (e) => {
        const pastedText = e.clipboardData?.getData('text') || '';
        const charCount = pastedText.length;
        if (charCount > 20) {
            setPasteWarning(`Warning: Large clipboard paste detected (${charCount} characters). This event is logged by AI Proctor.`);
            setTimeout(() => setPasteWarning(null), 5000);
            
            try {
                fetch(`${apiBaseUrl}/exams/proctoring_event`, {
                    method: 'POST',
                    headers: { ...getHeaders(), 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        attempt_id: examId,
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

    // Structured Table Handlers
    const updateTableCell = (rIdx, cIdx, val) => {
        setTableData(prev => {
            const newRows = prev.rows.map((row, r) => 
                r === rIdx ? row.map((cell, c) => c === cIdx ? val : cell) : row
            );
            const updated = { ...prev, rows: newRows };
            triggerParentUpdate('TABLE', '[Structured Table]', updated, uploadedFile);
            return updated;
        });
    };

    const updateTableHeader = (cIdx, val) => {
        setTableData(prev => {
            const newHeaders = prev.headers.map((h, c) => c === cIdx ? val : h);
            const updated = { ...prev, headers: newHeaders };
            triggerParentUpdate('TABLE', '[Structured Table]', updated, uploadedFile);
            return updated;
        });
    };

    const addTableRow = () => {
        setTableData(prev => {
            const emptyRow = new Array(prev.headers.length).fill('');
            const updated = { ...prev, rows: [...prev.rows, emptyRow] };
            triggerParentUpdate('TABLE', '[Structured Table]', updated, uploadedFile);
            return updated;
        });
    };

    const removeTableRow = (rIdx) => {
        setTableData(prev => {
            if (prev.rows.length <= 1) return prev;
            const updated = { ...prev, rows: prev.rows.filter((_, idx) => idx !== rIdx) };
            triggerParentUpdate('TABLE', '[Structured Table]', updated, uploadedFile);
            return updated;
        });
    };

    const addTableColumn = () => {
        setTableData(prev => {
            const newHeaders = [...prev.headers, `Col ${prev.headers.length + 1}`];
            const newRows = prev.rows.map(row => [...row, '']);
            const updated = { ...prev, headers: newHeaders, rows: newRows };
            triggerParentUpdate('TABLE', '[Structured Table]', updated, uploadedFile);
            return updated;
        });
    };

    const removeTableColumn = (cIdx) => {
        setTableData(prev => {
            if (prev.headers.length <= 1) return prev;
            const newHeaders = prev.headers.filter((_, idx) => idx !== cIdx);
            const newRows = prev.rows.map(row => row.filter((_, idx) => idx !== cIdx));
            const updated = { ...prev, headers: newHeaders, rows: newRows };
            triggerParentUpdate('TABLE', '[Structured Table]', updated, uploadedFile);
            return updated;
        });
    };

    // File Upload Handler
    const handleFileUpload = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const maxMb = 10;
        if (file.size > maxMb * 1024 * 1024) {
            alert(`File size exceeds ${maxMb}MB limit.`);
            return;
        }

        const allowedExts = ['pdf', 'png', 'jpg', 'jpeg', 'webp'];
        const ext = file.name.split('.').pop().toLowerCase();
        if (!allowedExts.includes(ext)) {
            alert(`Unsupported file format. Please upload PDF, PNG, or JPG.`);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('question_id', question.id);
        formData.append('exam_id', examId);

        setSaveStatus('saving');
        try {
            const res = await fetch(`${apiBaseUrl}/exams/upload_answer_document`, {
                method: 'POST',
                headers: getHeaders(),
                body: formData
            });

            if (res.ok) {
                const data = await res.json();
                const fileObj = {
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

    // Tab definitions with stable labels & icons
    const formatTabs = [
        {
            id: 'TEXT',
            label: 'Text Answer',
            icon: <Type size={16} />,
            title: 'Descriptive text & explanations',
            getText: () => textContent,
            getStructured: () => null
        },
        {
            id: 'MATH_EQUATION',
            label: 'Math / LaTeX',
            icon: <Calculator size={16} />,
            title: 'Mathematical equations, symbols & LaTeX derivations',
            getText: () => mathContent,
            getStructured: () => null
        },
        {
            id: 'AUTOMATA_GRAPH',
            label: 'DFA / NFA Diagram',
            icon: <GitCommit size={16} />,
            title: 'Automata state diagrams, transitions & formal specification',
            getText: () => `[Automata ${automataData.type}]`,
            getStructured: () => automataData
        },
        {
            id: 'TABLE',
            label: 'Table Editor',
            icon: <TableIcon size={16} />,
            title: 'Structured matrix & transition table builder',
            getText: () => '[Structured Table]',
            getStructured: () => tableData
        },
        {
            id: 'FILE_UPLOAD',
            label: 'Upload Solution',
            icon: <UploadCloud size={16} />,
            title: 'Upload scanned handwritten solution or PDF file',
            getText: () => uploadedFile?.filename || '[File Attached]',
            getStructured: () => null
        }
    ];

    const handleTabSwitch = (tabId) => {
        setActiveTab(tabId);
        const tab = formatTabs.find(t => t.id === tabId);
        if (tab) {
            triggerParentUpdate(tab.id, tab.getText(), tab.getStructured(), uploadedFile);
        }
    };

    return (
        <div className="multi-format-answer-container border rounded-3 p-3 bg-light shadow-sm position-relative d-flex flex-column" style={{ minHeight: '380px' }}>
            {/* Scoped CSS for Stable Sticky Segmented Dock (NO LAYOUT SHIFT, ALWAYS ACCESSIBLE) */}
            <style>{`
                .multi-format-answer-container {
                    transition: all 0.2s ease;
                }
                .format-dock-wrapper {
                    position: sticky;
                    bottom: 0;
                    z-index: 30;
                    background: rgba(255, 255, 255, 0.96);
                    backdrop-filter: blur(8px);
                    padding: 10px 0 6px 0;
                    margin-top: auto;
                    border-top: 1px solid #e2e8f0;
                    box-shadow: 0 -4px 14px rgba(0, 0, 0, 0.05);
                    border-bottom-left-radius: 8px;
                    border-bottom-right-radius: 8px;
                }
                .format-stable-dock {
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    padding: 6px 10px;
                    background: #ffffff;
                    border: 1px solid #cbd5e1;
                    border-radius: 9999px;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
                    transition: box-shadow 0.2s ease, border-color 0.2s ease;
                }
                .format-stable-dock:hover {
                    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.15);
                    border-color: #93c5fd;
                }
                .dock-item-btn {
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    padding: 6px 14px;
                    border-radius: 9999px;
                    border: 1px solid transparent;
                    font-size: 13px;
                    font-weight: 600;
                    white-space: nowrap;
                    cursor: pointer;
                    user-select: none;
                    transition: background-color 0.15s ease, color 0.15s ease, transform 0.1s ease;
                    outline: none;
                }
                .dock-item-btn.active {
                    background-color: #2563eb !important;
                    color: #ffffff !important;
                    box-shadow: 0 2px 6px rgba(37, 99, 235, 0.35);
                }
                .dock-item-btn:not(.active) {
                    background-color: transparent;
                    color: #4b5563;
                }
                .dock-item-btn:not(.active):hover {
                    background-color: #f1f5f9;
                    color: #0f172a;
                }
                .dock-item-btn:active {
                    transform: scale(0.97);
                }
                .automata-scroll-area {
                    max-height: 480px;
                    overflow-y: auto;
                    padding-right: 4px;
                }
                .automata-scroll-area::-webkit-scrollbar {
                    width: 6px;
                }
                .automata-scroll-area::-webkit-scrollbar-thumb {
                    background: #cbd5e1;
                    border-radius: 4px;
                }
            `}</style>

            {/* TOP BAR: Distraction-free, minimal title + autosave indicator */}
            <div className="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom">
                <div className="d-flex align-items-center gap-2">
                    <span className="badge bg-white text-primary border fw-semibold px-2 py-1">
                        {activeTab === 'TEXT' && '✍️ Text Mode'}
                        {activeTab === 'MATH_EQUATION' && '∑ Math / LaTeX Mode'}
                        {activeTab === 'AUTOMATA_GRAPH' && '🔄 DFA / NFA Diagram Mode'}
                        {activeTab === 'TABLE' && '📊 Table Mode'}
                        {activeTab === 'FILE_UPLOAD' && '📎 Document Mode'}
                    </span>
                    <span className="text-muted small">
                        {activeTab === 'TEXT' && 'Clear descriptive writing canvas'}
                        {activeTab === 'MATH_EQUATION' && 'Mathematical expression formatting'}
                        {activeTab === 'AUTOMATA_GRAPH' && 'Live visual state diagram & transition table'}
                        {activeTab === 'TABLE' && 'Tabular grid response'}
                        {activeTab === 'FILE_UPLOAD' && 'PDF or scanned image attachment'}
                    </span>
                </div>

                <div className="d-flex align-items-center gap-2 small">
                    {saveStatus === 'saving' && (
                        <span className="text-muted"><span className="spinner-border spinner-border-sm me-1"></span>Saving...</span>
                    )}
                    {saveStatus === 'saved' && (
                        <span className="text-success fw-medium"><CheckCircle2 size={14} className="me-1 inline" />Saved {lastSavedTime ? `at ${lastSavedTime}` : ''}</span>
                    )}
                    {saveStatus === 'error' && (
                        <span className="text-danger fw-medium"><AlertTriangle size={14} className="me-1 inline" />Autosave Failed</span>
                    )}
                </div>
            </div>

            {pasteWarning && (
                <div className="alert alert-warning py-1 px-2 small mb-2 d-flex align-items-center">
                    <AlertTriangle size={14} className="me-1 text-warning" /> {pasteWarning}
                </div>
            )}

            {/* MAIN ANSWER AREA */}
            <div className="answer-workspace mb-3">
                {/* TAB 1: PLAIN / RICH TEXT */}
                {activeTab === 'TEXT' && (
                    <div>
                        <textarea
                            className="form-control"
                            rows="7"
                            style={{ fontSize: '15px', lineHeight: '1.6' }}
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
                            rows="5"
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

                {/* TAB 3: DFA / NFA STRUCTURED BUILDER WITH LIVE VISUAL DIAGRAM */}
                {activeTab === 'AUTOMATA_GRAPH' && (
                    <div className="d-flex flex-column">
                        {/* Sub-toolbar to switch between builder & diagram easily */}
                        <div className="d-flex flex-wrap justify-content-between align-items-center mb-2 pb-2 border-bottom gap-2">
                            <div className="btn-group btn-group-sm">
                                <button 
                                    type="button" 
                                    className={`btn btn-sm ${dfaSubView === 'editor' ? 'btn-primary' : 'btn-outline-secondary bg-white'}`}
                                    onClick={() => setDfaSubView('editor')}
                                    title="Edit formal 5-tuple and transition function table"
                                >
                                    ✏️ Edit States & Transitions ({automataData.transitions.length})
                                </button>
                                <button 
                                    type="button" 
                                    className={`btn btn-sm ${dfaSubView === 'graph' ? 'btn-primary' : 'btn-outline-secondary bg-white'}`}
                                    onClick={() => setDfaSubView('graph')}
                                    title="View live SVG state transition diagram"
                                >
                                    👁️ State Diagram Graph
                                </button>
                                <button 
                                    type="button" 
                                    className={`btn btn-sm ${dfaSubView === 'both' ? 'btn-primary' : 'btn-outline-secondary bg-white'}`}
                                    onClick={() => setDfaSubView('both')}
                                    title="Show both diagram and editor together"
                                >
                                    📑 Full Combined View
                                </button>
                            </div>

                            <span className="badge bg-white text-dark border small">
                                {automataData.type}: {automataData.states.length} States • {automataData.transitions.length} Transitions
                            </span>
                        </div>

                        <div className="automata-scroll-area">
                            {/* LIVE VISUAL DIAGRAM CANVAS (when 'graph' or 'both') */}
                            {(dfaSubView === 'graph' || dfaSubView === 'both') && (
                                <div className="mb-3">
                                    <div className="d-flex justify-content-between align-items-center mb-1">
                                        <small className="fw-bold text-primary d-flex align-items-center gap-1">
                                            <GitCommit size={14} /> Live State Diagram (DFA/NFA Graph)
                                        </small>
                                        <span className="badge bg-light text-secondary border">Real-time Visual Preview</span>
                                    </div>
                                    <AutomataDiagramViewer automataData={automataData} height={dfaSubView === 'graph' ? 240 : 160} readOnly={false} />
                                </div>
                            )}

                            {/* Automata Inputs (when 'editor' or 'both') */}
                            {(dfaSubView === 'editor' || dfaSubView === 'both') && (
                                <>
                                    <div className="card p-3 bg-white border mb-3">
                                        <h6 className="small fw-bold text-muted mb-2">Formal Specification: 5-Tuple (Q, Σ, δ, q₀, F)</h6>
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
                                                    placeholder="e.g. q0, q1, q2"
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
                                                    placeholder="e.g. 0, 1"
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
                                                    placeholder="q0"
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
                                                    placeholder="e.g. q1"
                                                    onChange={(e) => {
                                                        const final_states = e.target.value.split(',').map(s => s.trim()).filter(Boolean);
                                                        const updated = { ...automataData, final_states };
                                                        setAutomataData(updated);
                                                        triggerParentUpdate('AUTOMATA_GRAPH', `[Automata ${updated.type}]`, updated, uploadedFile);
                                                    }}
                                                />
                                            </div>
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
                                                    {automataData.transitions.length === 0 ? (
                                                        <tr>
                                                            <td colSpan="4" className="text-center text-muted small py-3">
                                                                No transitions defined yet. Click <strong>+ Add Transition</strong> above to start building your state diagram.
                                                            </td>
                                                        </tr>
                                                    ) : (
                                                        automataData.transitions.map((t, idx) => (
                                                            <tr key={idx}>
                                                                <td>
                                                                    <input 
                                                                        type="text" 
                                                                        className="form-control form-control-sm border-0" 
                                                                        value={t.from}
                                                                        placeholder="q0"
                                                                        onChange={(e) => updateTransition(idx, 'from', e.target.value)}
                                                                    />
                                                                </td>
                                                                <td>
                                                                    <input 
                                                                        type="text" 
                                                                        className="form-control form-control-sm border-0" 
                                                                        value={t.symbol}
                                                                        placeholder="0"
                                                                        onChange={(e) => updateTransition(idx, 'symbol', e.target.value)}
                                                                    />
                                                                </td>
                                                                <td>
                                                                    <input 
                                                                        type="text" 
                                                                        className="form-control form-control-sm border-0" 
                                                                        value={t.to}
                                                                        placeholder="q0"
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
                                                        ))
                                                    )}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </>
                            )}
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

                {/* TAB 5: STRUCTURED TABLE / MATRIX EDITOR */}
                {activeTab === 'TABLE' && (
                    <div className="card p-3 bg-white">
                        <div className="d-flex justify-content-between align-items-center mb-2">
                            <h6 className="small fw-bold text-muted m-0">Structured Matrix / Transition Table Editor</h6>
                            <div className="d-flex gap-1">
                                <button type="button" className="btn btn-sm btn-outline-primary py-0 px-2" onClick={addTableRow}>+ Add Row</button>
                                <button type="button" className="btn btn-sm btn-outline-primary py-0 px-2" onClick={addTableColumn}>+ Add Column</button>
                            </div>
                        </div>
                        <div className="table-responsive">
                            <table className="table table-bordered table-sm m-0">
                                <thead className="table-light">
                                    <tr>
                                        <th style={{ width: '40px' }} className="text-center">#</th>
                                        {tableData.headers.map((h, cIdx) => (
                                            <th key={cIdx}>
                                                <div className="d-flex align-items-center gap-1">
                                                    <input 
                                                        type="text" 
                                                        className="form-control form-control-sm fw-bold border-0 bg-transparent p-0" 
                                                        value={h} 
                                                        onChange={(e) => updateTableHeader(cIdx, e.target.value)}
                                                        placeholder={`Header ${cIdx + 1}`}
                                                    />
                                                    {tableData.headers.length > 1 && (
                                                        <button 
                                                            type="button" 
                                                            className="btn btn-link text-danger p-0" 
                                                            style={{ textDecoration: 'none', fontSize: '0.75rem' }}
                                                            onClick={() => removeTableColumn(cIdx)}
                                                            title="Remove column"
                                                        >×</button>
                                                    )}
                                                </div>
                                            </th>
                                        ))}
                                        <th style={{ width: '35px' }}></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {tableData.rows.map((row, rIdx) => (
                                        <tr key={rIdx}>
                                            <td className="text-muted small text-center align-middle">{rIdx + 1}</td>
                                            {row.map((cell, cIdx) => (
                                                <td key={cIdx} className="p-1">
                                                    <input 
                                                        type="text" 
                                                        className="form-control form-control-sm"
                                                        value={cell} 
                                                        onChange={(e) => updateTableCell(rIdx, cIdx, e.target.value)}
                                                        placeholder="Value"
                                                    />
                                                </td>
                                            ))}
                                            <td className="text-center align-middle p-0">
                                                {tableData.rows.length > 1 && (
                                                    <button 
                                                        type="button" 
                                                        className="btn btn-link text-danger p-0" 
                                                        style={{ textDecoration: 'none', fontSize: '0.85rem' }}
                                                        onClick={() => removeTableRow(rIdx)}
                                                        title="Remove row"
                                                    >×</button>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <small className="text-muted mt-2 d-block">
                            Tip: Edit column headers and cell values directly. Answers will be evaluated cell-by-cell against the reference table.
                        </small>
                    </div>
                )}
            </div>

            {/* --- STABLE BOTTOM FORMAT TOOLBAR (ZERO JUMPING, EFFORTLESS CLICKING) --- */}
            <div className="format-dock-wrapper pt-2 border-top d-flex flex-column align-items-center">
                <div className="format-stable-dock">
                    {formatTabs.map(tab => {
                        const isActive = activeTab === tab.id;
                        return (
                            <button
                                key={tab.id}
                                type="button"
                                onClick={() => handleTabSwitch(tab.id)}
                                className={`dock-item-btn ${isActive ? 'active' : ''}`}
                                title={tab.title}
                            >
                                <span className="d-inline-flex align-items-center">
                                    {tab.icon}
                                </span>
                                <span>
                                    {tab.label}
                                </span>
                            </button>
                        );
                    })}
                </div>
                <div className="text-muted text-center mt-1" style={{ fontSize: '11px', opacity: 0.75 }}>
                    Select response format above • Clear, distraction-free workspace
                </div>
            </div>
        </div>
    );
};

export default MultiFormatAnswerInput;
