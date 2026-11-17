import React, { useState, useEffect } from 'react';
import { 
  BrainCircuit, 
  UploadCloud, 
  FileText, 
  Sparkles, 
  CheckCircle2, 
  AlertCircle, 
  Sliders, 
  Trash2, 
  ArrowRight, 
  ArrowLeft, 
  BookOpen, 
  Layers, 
  HelpCircle,
  Clock,
  Award,
  Check
} from 'lucide-react';
import { examService } from '../../services/examService';

const cleanTopicTag = (topic) => {
  if (!topic) return 'CORE TOPIC';
  let t = topic.replace(/^[•\*\-\d\.\)]+\s*/, '')
               .replace(/^(?:unit|module|chapter)\s*[\divx\.\-\:\)]+\s*/i, '')
               .replace(/^(?:introduction to|overview of|basics of|fundamentals of|principles of|study of|we will learn about)\s+/i, '');
  t = t.split(/[\.\;\:\(\)\[\]\–\—]/)[0].trim();
  if (t.includes(',')) t = t.split(',')[0].trim();
  const words = t.split(/\s+/).filter(Boolean).slice(0, 4);
  while (words.length > 0 && ['AND', '&', 'OR', 'WITH', 'FOR', 'IN', 'OF', 'TO'].includes(words[words.length - 1].toUpperCase())) {
    words.pop();
  }
  return words.join(' ').toUpperCase() || 'CORE TOPIC';
};

const SyllabusExamAutomation = ({ onQuestionsGenerated, initialQuestionCount = 10, examTitle = '' }) => {
  // Step state: 1: Ingest Syllabus, 2: Review & Curate Topics, 3: Preview Generated Questions
  const [step, setStep] = useState(1);
  // inputMode: null (show 2 clickable cards like HackerEarth) | 'text' | 'file'
  const [inputMode, setInputMode] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Step 1: Input state
  const [syllabusText, setSyllabusText] = useState('');
  const [title, setTitle] = useState(examTitle || 'Course Curriculum & Syllabus');
  const [courseName, setCourseName] = useState('');
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [questionCount, setQuestionCount] = useState(initialQuestionCount || 10);
  const [examType, setExamType] = useState('Mixed'); // 'Mixed' | 'Objective' | 'Subjective'
  const [knowledgeDocs, setKnowledgeDocs] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState('');

  // Step 2: Analyzed Topics state
  const [analysisResult, setAnalysisResult] = useState(null);
  const [curatedTopics, setCuratedTopics] = useState([]);

  // Step 3: Generated Questions state & inline edit
  const [generatedQuestions, setGeneratedQuestions] = useState([]);
  const [editingIdx, setEditingIdx] = useState(null);

  // Fetch saved knowledge base documents on mount
  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const docs = await examService.getKnowledgeDocuments();
        if (Array.isArray(docs)) {
          setKnowledgeDocs(docs);
        }
      } catch (err) {
        console.warn('Knowledge docs fetch notice:', err);
      }
    };
    fetchDocs();
  }, []);

  // When teacher selects an existing document
  const handleSelectExistingDoc = (docId) => {
    setSelectedDocId(docId);
    if (!docId) return;
    const doc = knowledgeDocs.find(d => String(d.id) === String(docId));
    if (doc) {
      setTitle(doc.title || title);
      setCourseName(doc.course_name || courseName);
      setSyllabusText(doc.content_text || '');
    }
  };

  // File upload / drop handler (.txt, .md, .doc, .docx, .odt, .pdf)
  const processFile = (file) => {
    if (!file) return;
    setUploadedFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result;
      if (typeof text === 'string') {
        setSyllabusText(text);
        if (!title || title === 'Course Curriculum & Syllabus') {
          setTitle(file.name.replace(/\.[^/.]+$/, ""));
        }
      }
    };
    reader.readAsText(file);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    processFile(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    processFile(file);
  };

  // STEP 1 -> STEP 2: Analyze Syllabus
  const handleAnalyzeSyllabus = async () => {
    if (!syllabusText || syllabusText.trim().length < 15) {
      setError('Please provide syllabus content with at least 15 characters.');
      return;
    }
    setError('');
    setLoading(true);

    try {
      const payload = {
        syllabus_text: syllabusText.trim(),
        title: title.trim() || 'Course Syllabus',
        course_name: courseName.trim() || 'General Curriculum',
        document_id: selectedDocId ? parseInt(selectedDocId) : null
      };

      const result = await examService.analyzeSyllabus(payload);
      setAnalysisResult(result);

      // Initialize curated topics with active status and sanitized names
      const initialTopics = (result.topics || []).map((t, idx) => ({
        ...t,
        selected: true,
        weight_percentage: parseInt(t.weight_percentage) || Math.floor(100 / result.topics.length)
      }));
      setCuratedTopics(initialTopics);
      setStep(2);
    } catch (err) {
      console.error('Syllabus analysis error:', err);
      setError(err.message || 'Failed to analyze syllabus. Please check your network connection.');
    } finally {
      setLoading(false);
    }
  };

  // Topic weight adjustment
  const handleWeightChange = (idx, newWeight) => {
    const parsed = Math.max(0, Math.min(100, parseInt(newWeight) || 0));
    setCuratedTopics(prev => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], weight_percentage: parsed };
      return copy;
    });
  };

  const handleToggleTopic = (idx) => {
    setCuratedTopics(prev => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], selected: !copy[idx].selected };
      return copy;
    });
  };

  // Calculate total weight of selected topics
  const totalWeight = curatedTopics
    .filter(t => t.selected)
    .reduce((acc, t) => acc + (parseInt(t.weight_percentage) || 0), 0);

  // STEP 2 -> STEP 3: Generate Questions
  const handleGenerateQuestions = async () => {
    const selected = curatedTopics.filter(t => t.selected);
    if (selected.length === 0) {
      setError('Please select at least one topic to generate questions.');
      return;
    }
    if (totalWeight !== 100) {
      setError(`Topic weights must sum to exactly 100%. Current sum: ${totalWeight}%. Please adjust sliders.`);
      return;
    }
    setError('');
    setLoading(true);

    try {
      const payload = {
        topics: selected,
        question_count: parseInt(questionCount) || 10,
        exam_type: examType,
        syllabus_text: syllabusText
      };

      const res = await examService.generateSyllabusQuestions(payload);
      if (res && Array.isArray(res.questions)) {
        setGeneratedQuestions(res.questions);
        setStep(3);
      } else {
        throw new Error('Invalid response structure received from question generator.');
      }
    } catch (err) {
      console.error('Question generation error:', err);
      setError(err.message || 'Failed to generate assessment questions from syllabus.');
    } finally {
      setLoading(false);
    }
  };

  // Question manipulation in preview
  const handleRemoveQuestion = (idx) => {
    setGeneratedQuestions(prev => prev.filter((_, i) => i !== idx));
  };

  const handleEditQuestionText = (idx, newText) => {
    setGeneratedQuestions(prev => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], text: newText };
      return copy;
    });
  };

  // Final Step: confirm and pass back to parent CreateExamForm
  const handleFinalize = () => {
    if (onQuestionsGenerated) {
      onQuestionsGenerated({
        questions: generatedQuestions,
        questionCount: generatedQuestions.length,
        blueprint: {
          topic_distribution: Object.fromEntries(
            curatedTopics.filter(t => t.selected).map(t => [t.name, t.weight_percentage])
          ),
          difficulty_distribution: analysisResult?.difficulty_distribution || { Easy: 30, Medium: 50, Hard: 20 },
          bloom_distribution: analysisResult?.bloom_distribution || { Remember: 25, Understand: 30, Apply: 25, Analyze: 20 }
        },
        syllabusTitle: title,
        courseName: courseName
      });
    }
  };

  return (
    <div className="card shadow-sm border-0 my-3" style={{ background: '#ffffff', borderRadius: '12px' }}>
      {/* Top Header & Breadcrumb */}
      <div className="card-header bg-white border-bottom p-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <div className="d-flex align-items-center gap-2">
            <div className="p-2 rounded bg-primary bg-opacity-10 text-primary">
              <BrainCircuit size={22} />
            </div>
            <div>
              <h5 className="fw-bold m-0 text-dark">AI Syllabus & JD Intelligence</h5>
              <small className="text-muted">Automated curriculum analysis, topic recommendation & assessment generation (HackerEarth-style)</small>
            </div>
          </div>
          <span className="badge bg-primary bg-opacity-10 text-primary fw-semibold px-3 py-2 border border-primary border-opacity-25">
            Stage {step} of 3: {step === 1 ? 'Syllabus Ingestion' : (step === 2 ? 'Curriculum Curation' : 'Question Preview')}
          </span>
        </div>

        {/* Step Indicator Progress Bar */}
        <div className="d-flex align-items-center gap-2">
          <div className={`flex-grow-1 p-1 rounded ${step >= 1 ? 'bg-primary' : 'bg-light'}`} style={{ height: '6px' }} />
          <div className={`flex-grow-1 p-1 rounded ${step >= 2 ? 'bg-primary' : 'bg-light'}`} style={{ height: '6px' }} />
          <div className={`flex-grow-1 p-1 rounded ${step >= 3 ? 'bg-primary' : 'bg-light'}`} style={{ height: '6px' }} />
        </div>
      </div>

      <div className="card-body p-4">
        {error && (
          <div className="alert alert-danger py-2 px-3 small d-flex align-items-center mb-3">
            <AlertCircle size={16} className="me-2 text-danger flex-shrink-0" />
            <div>{error}</div>
          </div>
        )}

        {/* ============================================================== */}
        {/* STEP 1: INGEST SYLLABUS — HACKEREARTH JD STYLE INTERFACE        */}
        {/* ============================================================== */}
        {step === 1 && (
          <div>
            {/* Screen 1A: Two Clickable Options (Given Photo Interface) */}
            {inputMode === null && (
              <div className="py-2">
                <div className="mb-4">
                  <h5 className="fw-bold mb-1 text-dark">
                    Based on your syllabus / job description
                  </h5>
                  <p className="text-muted small mb-0">
                    The details from your course syllabus or job description are used to create a relevant test.
                  </p>
                </div>

                <div className="d-flex flex-column gap-3 mb-4">
                  {/* Card 1: Add Text */}
                  <div 
                    className="p-4 rounded border text-center"
                    style={{
                      background: '#ffffff',
                      border: '1.5px solid #e2e8f0',
                      borderRadius: '10px',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease-in-out'
                    }}
                    onClick={() => setInputMode('text')}
                    onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#3b82f6'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(59,130,246,0.08)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#e2e8f0'; e.currentTarget.style.boxShadow = 'none'; }}
                  >
                    <div className="d-flex justify-content-center mb-3">
                      <div className="p-3 rounded-circle bg-light text-secondary">
                        <FileText size={32} />
                      </div>
                    </div>
                    <h6 className="fw-bold text-dark mb-1">Add your course syllabus / job description</h6>
                    <p className="text-muted small mb-0">(Between 100 and 10000 characters only)</p>
                  </div>

                  {/* OR Divider */}
                  <div className="d-flex align-items-center justify-content-center gap-3 my-1">
                    <div className="flex-grow-1" style={{ height: '1px', background: '#e2e8f0' }} />
                    <span className="text-muted small fw-bold">OR</span>
                    <div className="flex-grow-1" style={{ height: '1px', background: '#e2e8f0' }} />
                  </div>

                  {/* Card 2: Upload File */}
                  <div 
                    className="p-4 rounded border text-center"
                    style={{
                      background: '#f8fafc',
                      border: '1.5px solid #cbd5e1',
                      borderRadius: '10px',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease-in-out'
                    }}
                    onClick={() => setInputMode('file')}
                    onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#3b82f6'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(59,130,246,0.08)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#cbd5e1'; e.currentTarget.style.boxShadow = 'none'; }}
                  >
                    <div className="d-flex justify-content-center mb-3">
                      <div className="p-3 rounded-circle bg-white text-primary shadow-sm">
                        <UploadCloud size={32} />
                      </div>
                    </div>
                    <h6 className="fw-bold text-primary mb-1">Upload your course syllabus / job description</h6>
                    <p className="fw-semibold text-secondary small mb-1">or drag and drop your file here</p>
                    <p className="text-muted" style={{ fontSize: '11px', margin: 0 }}>
                      (Supported files: .doc, .docx, .pdf, .txt, .odt files up to 5MB)
                    </p>
                  </div>
                </div>

                {knowledgeDocs.length > 0 && (
                  <div className="card p-3 bg-light border-0 rounded-3">
                    <label className="fw-semibold small text-muted mb-2 d-flex align-items-center gap-1">
                      <BookOpen size={14} className="text-primary" /> Or select a previously saved institutional document:
                    </label>
                    <select 
                      className="form-select form-select-sm"
                      value={selectedDocId}
                      onChange={(e) => {
                        handleSelectExistingDoc(e.target.value);
                        setInputMode('text');
                      }}
                    >
                      <option value="">-- Choose from saved documents ({knowledgeDocs.length}) --</option>
                      {knowledgeDocs.map(doc => (
                        <option key={doc.id} value={doc.id}>
                          {doc.title} {doc.course_name ? `(${doc.course_name})` : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            )}

            {/* Screen 1B: Text Input Mode */}
            {inputMode === 'text' && (
              <div>
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <button 
                    type="button" 
                    className="btn btn-sm btn-link text-decoration-none p-0 d-flex align-items-center gap-1 text-primary fw-semibold"
                    onClick={() => setInputMode(null)}
                  >
                    <ArrowLeft size={16} /> Back to selection
                  </button>
                  <span className="text-muted small">
                    {syllabusText.length} / 10000 characters
                  </span>
                </div>

                <div className="form-group mb-3">
                  <label className="form-label small fw-bold text-dark">Course / Document Title</label>
                  <input 
                    type="text" 
                    className="form-control" 
                    placeholder="e.g. CS202 - Data Structures & Algorithms"
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                  />
                </div>

                <div className="form-group mb-3">
                  <label className="form-label small fw-bold text-dark">
                    Add your course syllabus / job description <span className="text-muted fw-normal">(100 - 10000 characters)</span>
                  </label>
                  <textarea 
                    className="form-control font-monospace"
                    rows="8"
                    style={{ fontSize: '13px', lineHeight: '1.6' }}
                    placeholder="Paste your course units, syllabus topics, or job description here...
Example:
Unit 1: Stacks and Queues (LIFO, FIFO, complexity analysis)
Unit 2: Binary Search Trees and AVL Balanced Trees
Unit 3: Graph Traversal Algorithms (BFS, DFS, Dijkstra)
Unit 4: Dynamic Programming & Greedy Approximations"
                    value={syllabusText}
                    onChange={e => setSyllabusText(e.target.value)}
                  />
                </div>

                {/* Target Settings */}
                <div className="card p-3 bg-light border-0 mb-4 rounded-3">
                  <h6 className="small fw-bold text-dark mb-2 d-flex align-items-center gap-1">
                    <Sliders size={14} className="text-primary" /> Target Test Settings
                  </h6>
                  <div className="row g-3">
                    <div className="col-md-6">
                      <label className="small text-muted">Total Questions</label>
                      <select 
                        className="form-select form-select-sm"
                        value={questionCount}
                        onChange={e => setQuestionCount(parseInt(e.target.value))}
                      >
                        <option value="5">5 Questions (Quick Assessment)</option>
                        <option value="10">10 Questions (Standard Test)</option>
                        <option value="15">15 Questions (Comprehensive)</option>
                        <option value="20">20 Questions (Benchmark Midterm)</option>
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="small text-muted">Question Format</label>
                      <select 
                        className="form-select form-select-sm"
                        value={examType}
                        onChange={e => setExamType(e.target.value)}
                      >
                        <option value="Mixed">⚡ Mixed: Objective (MCQs) + Subjective</option>
                        <option value="Objective">🎯 Objective Only (MCQs)</option>
                        <option value="Subjective">✍️ Subjective Only (Problems / Theory / DFA)</option>
                      </select>
                    </div>
                  </div>
                </div>

                <button 
                  type="button" 
                  disabled={loading || syllabusText.length < 15}
                  className="btn btn-primary w-100 py-2 fw-bold d-flex align-items-center justify-content-center gap-2"
                  onClick={handleAnalyzeSyllabus}
                >
                  {loading ? (
                    <>
                      <span className="spinner-border spinner-border-sm" role="status" />
                      Analyzing Syllabus & Extracting Topics...
                    </>
                  ) : (
                    <>
                      <Sparkles size={16} />
                      Analyze Syllabus & Extract Blueprint
                      <ArrowRight size={16} />
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Screen 1C: File Upload Mode */}
            {inputMode === 'file' && (
              <div>
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <button 
                    type="button" 
                    className="btn btn-sm btn-link text-decoration-none p-0 d-flex align-items-center gap-1 text-primary fw-semibold"
                    onClick={() => setInputMode(null)}
                  >
                    <ArrowLeft size={16} /> Back to selection
                  </button>
                </div>

                <div 
                  className={`p-5 rounded border text-center mb-3 ${isDragging ? 'border-primary bg-primary bg-opacity-10' : 'bg-light'}`}
                  style={{
                    border: '2px dashed #94a3b8',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => document.getElementById('syllabus_file_drop_input')?.click()}
                >
                  <input 
                    id="syllabus_file_drop_input" 
                    type="file" 
                    className="d-none" 
                    accept=".txt,.md,.doc,.docx,.odt,.pdf,.text"
                    onChange={handleFileUpload}
                  />
                  <div className="d-flex justify-content-center mb-2">
                    <UploadCloud size={40} className="text-primary" />
                  </div>
                  <h6 className="fw-bold text-dark mb-1">
                    {uploadedFileName ? `Selected: ${uploadedFileName}` : 'Upload your syllabus / job description'}
                  </h6>
                  <p className="text-muted small mb-0">Drag and drop file here, or click to browse</p>
                  <small className="text-secondary" style={{ fontSize: '11px' }}>
                    Supported formats: .txt, .pdf, .docx, .doc, .odt up to 5MB
                  </small>
                </div>

                {syllabusText && (
                  <div className="card p-3 bg-white border mb-3">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span className="small fw-bold text-success">✓ File content loaded ({syllabusText.length} characters)</span>
                      <button 
                        type="button" 
                        className="btn btn-sm btn-link text-danger text-decoration-none p-0"
                        onClick={() => { setSyllabusText(''); setUploadedFileName(''); }}
                      >
                        Clear
                      </button>
                    </div>
                    <div className="small text-muted font-monospace bg-light p-2 rounded" style={{ maxHeight: '100px', overflowY: 'auto' }}>
                      {syllabusText.slice(0, 300)}...
                    </div>
                  </div>
                )}

                {/* Target Settings */}
                <div className="card p-3 bg-light border-0 mb-4 rounded-3">
                  <h6 className="small fw-bold text-dark mb-2 d-flex align-items-center gap-1">
                    <Sliders size={14} className="text-primary" /> Target Test Settings
                  </h6>
                  <div className="row g-3">
                    <div className="col-md-6">
                      <label className="small text-muted">Total Questions</label>
                      <select 
                        className="form-select form-select-sm"
                        value={questionCount}
                        onChange={e => setQuestionCount(parseInt(e.target.value))}
                      >
                        <option value="5">5 Questions (Quick Assessment)</option>
                        <option value="10">10 Questions (Standard Test)</option>
                        <option value="15">15 Questions (Comprehensive)</option>
                        <option value="20">20 Questions (Benchmark Midterm)</option>
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="small text-muted">Question Format</label>
                      <select 
                        className="form-select form-select-sm"
                        value={examType}
                        onChange={e => setExamType(e.target.value)}
                      >
                        <option value="Mixed">⚡ Mixed: Objective (MCQs) + Subjective</option>
                        <option value="Objective">🎯 Objective Only (MCQs)</option>
                        <option value="Subjective">✍️ Subjective Only (Problems / Theory / DFA)</option>
                      </select>
                    </div>
                  </div>
                </div>

                <button 
                  type="button" 
                  disabled={loading || syllabusText.length < 15}
                  className="btn btn-primary w-100 py-2 fw-bold d-flex align-items-center justify-content-center gap-2"
                  onClick={handleAnalyzeSyllabus}
                >
                  {loading ? (
                    <>
                      <span className="spinner-border spinner-border-sm" role="status" />
                      Analyzing Syllabus & Extracting Topics...
                    </>
                  ) : (
                    <>
                      <Sparkles size={16} />
                      Analyze Syllabus & Extract Blueprint
                      <ArrowRight size={16} />
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        )}

        {/* ============================================================== */}
        {/* STEP 2: REVIEW & CURATE EXTRACTED TOPICS (100% WEIGHT SUM)     */}
        {/* ============================================================== */}
        {step === 2 && (
          <div>
            <div className="d-flex justify-content-between align-items-center mb-3">
              <div>
                <h5 className="fw-bold m-0 text-dark">Curate Extracted Topics & Weightage</h5>
                <small className="text-muted">
                  Extracted {curatedTopics.length} core academic modules. Adjust weightage sliders to balance your assessment.
                </small>
              </div>

              <div className="d-flex align-items-center gap-2">
                <span className={`badge px-3 py-2 fs-6 ${totalWeight === 100 ? 'bg-success' : 'bg-danger'}`}>
                  Total Weight: {totalWeight}% {totalWeight === 100 ? '✓ Balanced' : '(Must be 100%)'}
                </span>
              </div>
            </div>

            {/* Topic Cards */}
            <div className="d-flex flex-column gap-3 mb-4">
              {curatedTopics.map((topic, idx) => (
                <div 
                  key={topic.id || idx} 
                  className={`card border transition-all ${topic.selected ? 'border-primary shadow-sm' : 'border-light bg-light opacity-50'}`}
                  style={{ borderRadius: '10px' }}
                >
                  <div className="card-body p-3">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <div className="d-flex align-items-center gap-2">
                        <input 
                          type="checkbox" 
                          className="form-check-input"
                          checked={topic.selected}
                          onChange={() => handleToggleTopic(idx)}
                        />
                        <h6 className="fw-bold m-0 text-dark">
                          {topic.name}
                        </h6>
                        <span className="badge bg-secondary opacity-75 small">
                          {cleanTopicTag(topic.name)}
                        </span>
                      </div>

                      <div className="d-flex align-items-center gap-2">
                        <span className="badge bg-light text-secondary border small">
                          {topic.recommended_difficulty || 'Medium'}
                        </span>
                        <span className="badge bg-light text-secondary border small">
                          Bloom: {topic.recommended_bloom || 'Apply'}
                        </span>
                      </div>
                    </div>

                    {topic.selected && (
                      <div className="row align-items-center mt-3 g-2">
                        <div className="col-md-3">
                          <label className="small fw-semibold text-secondary m-0">Topic Weightage:</label>
                        </div>
                        <div className="col-md-6">
                          <input 
                            type="range" 
                            className="form-range" 
                            min="5" 
                            max="80" 
                            step="5"
                            value={topic.weight_percentage}
                            onChange={(e) => handleWeightChange(idx, e.target.value)}
                          />
                        </div>
                        <div className="col-md-3 text-end">
                          <span className="badge bg-primary px-3 py-1 fs-6">
                            {topic.weight_percentage}%
                          </span>
                          <span className="text-muted small ms-2">
                            (~{Math.max(1, Math.round((topic.weight_percentage / 100) * questionCount))} Qs)
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Actions: Back & Generate */}
            <div className="d-flex justify-content-between align-items-center pt-2">
              <button 
                type="button" 
                className="btn btn-outline-secondary px-4 d-flex align-items-center gap-1"
                onClick={() => setStep(1)}
              >
                <ArrowLeft size={16} /> Back to Syllabus
              </button>

              <button 
                type="button" 
                className="btn btn-primary px-5 py-2 fw-bold d-flex align-items-center gap-2"
                disabled={loading || totalWeight !== 100}
                onClick={handleGenerateQuestions}
              >
                {loading ? (
                  <>
                    <span className="spinner-border spinner-border-sm" role="status" />
                    Generating Questions with AI...
                  </>
                ) : (
                  <>
                    <Sparkles size={18} />
                    Generate Question Set ({questionCount} Qs)
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* STEP 3: PREVIEW GENERATED QUESTIONS (IMAGE 2 MATCHING UI)       */}
        {/* ============================================================== */}
        {step === 3 && (
          <div>
            <div className="d-flex justify-content-between align-items-center mb-3">
              <div>
                <h5 className="fw-bold m-0 text-dark">Generated Question Set Preview</h5>
                <small className="text-muted">
                  Grounded strictly in syllabus • {generatedQuestions.length} questions generated
                </small>
              </div>

              <div className="d-flex gap-2">
                <span className="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25 px-3 py-2">
                  ✓ {generatedQuestions.filter(q => !q.is_subjective).length} Objective (MCQ)
                </span>
                <span className="badge bg-info bg-opacity-10 text-info border border-info border-opacity-25 px-3 py-2">
                  ✓ {generatedQuestions.filter(q => q.is_subjective).length} Subjective (Problem/Theory)
                </span>
              </div>
            </div>

            {/* Questions List (Styled precisely like Image 2) */}
            <div className="d-flex flex-column gap-3 mb-4">
              {generatedQuestions.map((q, idx) => (
                <div key={idx} className="p-3 rounded border bg-white shadow-sm position-relative" style={{ borderRadius: '8px' }}>
                  <div className="d-flex justify-content-between align-items-start mb-2">
                    <span className="badge bg-primary">Q{idx + 1}</span>
                    <div className="d-flex gap-1">
                      <button 
                        type="button"
                        onClick={() => setEditingIdx(editingIdx === idx ? null : idx)} 
                        className="btn btn-sm btn-outline-secondary p-1 px-2" 
                        style={{ fontSize: '0.75rem' }}
                      >
                        {editingIdx === idx ? 'Done' : 'Edit'}
                      </button>
                      <button 
                        type="button"
                        onClick={() => handleRemoveQuestion(idx)} 
                        className="btn btn-sm btn-outline-danger p-1 px-2" 
                        style={{ fontSize: '0.75rem' }}
                      >
                        Remove
                      </button>
                    </div>
                  </div>

                  {editingIdx === idx ? (
                    <textarea 
                      className="form-control mb-2" 
                      rows="3" 
                      value={q.text} 
                      onChange={(e) => handleEditQuestionText(idx, e.target.value)} 
                    />
                  ) : (
                    <p className="mb-2 fw-semibold text-dark" style={{ fontSize: '0.92rem', lineHeight: '1.5' }}>
                      {q.text}
                    </p>
                  )}

                  {/* Clean Tags: MCQ, Marks, Concise Topic, Difficulty, Bloom */}
                  <div className="d-flex flex-wrap gap-2 mb-2">
                    <span className="badge bg-info text-dark">
                      {q.is_subjective ? (q.question_type || 'SUBJECTIVE') : 'MCQ'}
                    </span>
                    <span className="badge bg-primary">
                      {q.max_marks || 1} MARK(S)
                    </span>
                    {q.topic && (
                      <span className="badge bg-secondary opacity-75">
                        {cleanTopicTag(q.topic)}
                      </span>
                    )}
                    {q.difficulty && (
                      <span className="badge bg-secondary opacity-75">
                        {q.difficulty.toUpperCase()}
                      </span>
                    )}
                    {q.bloom_level && (
                      <span className="badge bg-secondary opacity-75">
                        {q.bloom_level.toUpperCase()}
                      </span>
                    )}
                  </div>

                  {/* MCQ Options Display */}
                  {!q.is_subjective && (
                    <div className="row g-2 mt-1">
                      {['A', 'B', 'C', 'D'].map(opt => {
                        const isCorrect = q.correct_option === opt;
                        const optText = q[`option_${opt.toLowerCase()}`];
                        if (!optText) return null;
                        return (
                          <div key={opt} className="col-md-6">
                            <div className={`p-2 rounded border small d-flex align-items-center justify-content-between ${isCorrect ? 'bg-success bg-opacity-10 border-success text-success fw-bold' : 'bg-light text-dark'}`}>
                              <span><strong>{opt}:</strong> {optText}</span>
                              {isCorrect && <Check size={14} className="text-success" />}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Subjective Reference and Rubric */}
                  {q.is_subjective && (
                    <div className="bg-light p-2 rounded border small mt-2">
                      <div>
                        <strong className="text-success">Reference Solution:</strong>
                        <div className="bg-white p-2 rounded border mt-1 font-monospace" style={{ whiteSpace: 'pre-wrap' }}>
                          {q.reference_answer || 'Detailed step-by-step solution.'}
                        </div>
                      </div>
                      {q.rubric && (
                        <div className="mt-2 text-muted">
                          <strong>Rubric Criteria:</strong> {q.rubric}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Actions: Back & Confirm */}
            <div className="d-flex justify-content-between align-items-center pt-3 border-top">
              <button 
                type="button" 
                className="btn btn-outline-secondary px-4 d-flex align-items-center gap-1"
                onClick={() => setStep(2)}
              >
                <ArrowLeft size={16} /> Back to Topics
              </button>

              <button 
                type="button" 
                disabled={loading || generatedQuestions.length === 0}
                className="btn btn-success btn-lg px-5 py-2 fw-bold d-flex align-items-center gap-2 shadow"
                onClick={handleFinalize}
              >
                <CheckCircle2 size={20} />
                Approve & Create Assessment ({generatedQuestions.length} Questions)
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SyllabusExamAutomation;
