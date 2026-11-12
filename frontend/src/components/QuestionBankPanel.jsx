import React, { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import { CheckCircle } from 'lucide-react';


const QuestionBankPanel = ({ examId, activeExamQuestions = [], onQuestionAdded }) => {
    const { API_BASE_URL, getHeaders } = useAuth();
    const [bankQuestions, setBankQuestions] = useState([]);
    const [filterTopic, setFilterTopic] = useState('');
    const [filterDifficulty, setFilterDifficulty] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const fetchBank = async () => {
            setLoading(true);
            try {
                const res = await fetch(`${API_BASE_URL}/exams/bank`, { headers: getHeaders() });
                if (res.ok) {
                    setBankQuestions(await res.json());
                }
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        };
        fetchBank();
    }, [API_BASE_URL]);

    const handleAdd = async (qId) => {
        try {
            const res = await fetch(`${API_BASE_URL}/exams/${examId}/clone_from_bank`, {
                method: 'POST',
                headers: { ...getHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ question_id: qId })
            });
            if (res.ok) {
                onQuestionAdded();
                alert(" Cloned into exam.");
            } else {
                alert(" Failed to add from bank.");
            }
        } catch (e) {
            console.error(e);
        }
    };

    const filtered = bankQuestions.filter(q => 
        (filterTopic === '' || q.topic === filterTopic) &&
        (filterDifficulty === '' || q.difficulty === filterDifficulty)
    );

    const uniqueTopics = [...new Set(bankQuestions.map(q => q.topic).filter(Boolean))];

    return (
        <div className="card shadow-sm h-100 border-0">
            <div className="card-header bg-white border-bottom-0 pt-4 pb-2">
                <h5 className="mb-0 text-primary"> Question Bank</h5>
                <p className="text-muted small mb-0">Browse and reuse existing questions.</p>
            </div>
            <div className="card-body pt-2 d-flex flex-column" style={{ maxHeight: '600px' }}>
                <div className="d-flex gap-2 mb-3">
                    <select className="form-select form-select-sm" value={filterTopic} onChange={e => setFilterTopic(e.target.value)}>
                        <option value="">All Topics</option>
                        {uniqueTopics.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                    <select className="form-select form-select-sm" value={filterDifficulty} onChange={e => setFilterDifficulty(e.target.value)}>
                        <option value="">All Difficulties</option>
                        <option value="Easy">Easy</option>
                        <option value="Medium">Medium</option>
                        <option value="Hard">Hard</option>
                    </select>
                </div>
                
                <div className="overflow-auto flex-grow-1" style={{ border: '1px solid #dee2e6', borderRadius: '8px', padding: '10px' }}>
                    {loading ? (
                        <div className="text-center p-4">Loading bank...</div>
                    ) : filtered.length === 0 ? (
                        <div className="text-center text-muted p-4 small">No questions found matching criteria.</div>
                    ) : (
                        <div className="d-flex flex-column gap-2">
                            {filtered.map(q => {
                                const isAlreadyAdded = activeExamQuestions.some(examQ => examQ.original_text === q.text);
                                return (
                                <div key={q.id} className={`p-2 border rounded ${isAlreadyAdded ? 'bg-light text-muted' : ''}`} style={{ fontSize: '0.9rem' }}>
                                    <div className="d-flex justify-content-between align-items-start mb-1">
                                        <div className="fw-bold text-truncate me-2" style={{ maxWidth: '80%' }}>
                                            {q.text.startsWith('U2F') ? ' Encrypted Question' : q.text}
                                        </div>
                                        {isAlreadyAdded ? (
                                            <span className="badge bg-secondary text-white py-1 px-2 d-flex align-items-center">
                                                Added <CheckCircle size={18} className="me-2" />
                                            </span>
                                        ) : (
                                            <button className="btn btn-sm btn-outline-primary py-0 px-2" onClick={() => handleAdd(q.id)}>
                                                + Add
                                            </button>
                                        )}
                                    </div>
                                    <div className="d-flex gap-1" style={{ opacity: isAlreadyAdded ? 0.6 : 1 }}>
                                        <span className={`badge ${q.is_subjective || q.question_type === 'SUBJECTIVE' ? 'bg-info text-dark' : 'bg-secondary text-white'}`}>
                                            {q.is_subjective || q.question_type === 'SUBJECTIVE' ? 'Subjective' : 'MCQ'}
                                        </span>
                                        <span className="badge bg-light text-dark border">
                                            Marks: {q.max_marks || 1}
                                        </span>
                                        <span className="badge bg-light text-dark border">{q.topic || 'General'}</span>
                                        <span className={`badge ${q.difficulty==='Easy' ? 'bg-success' : q.difficulty==='Medium' ? 'bg-warning' : 'bg-danger'}`}>{q.difficulty}</span>
                                        <span className="badge bg-info">{q.bloom_level}</span>
                                    </div>
                                </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default QuestionBankPanel;
