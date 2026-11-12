import React, { useState, useEffect } from 'react';
import { intelligenceService } from '../../services/intelligenceService';
import LoadingState from '../common/LoadingState';
import EmptyState from '../common/EmptyState';
import SectionHeader from '../common/SectionHeader';
import { useAuth } from '../../AuthContext';

const RecommendationPanel = ({ examId, onQuestionAdded }) => {
    const { API_BASE_URL, getHeaders } = useAuth();
    const [loading, setLoading] = useState(true);
    const [recommendations, setRecommendations] = useState([]);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchRecommendations();
    }, [examId]);

    async function fetchRecommendations() {
        setLoading(true);
        try {
            const data = await intelligenceService.getRecommendations(examId);
            const recList = data?.recommendations ? data.recommendations : (Array.isArray(data) ? data : []);
            setRecommendations(recList);
            setError(null);
        } catch (err) {
            console.error("Failed to fetch recommendations:", err);
            setError("Failed to load recommendations.");
        }
        setLoading(false);
    };

    const handleAddCandidate = async (candidateId) => {
        try {
            const res = await fetch(`${API_BASE_URL}/exams/${examId}/clone_from_bank`, {
                method: 'POST',
                headers: { ...getHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ question_id: candidateId })
            });
            if (res.ok) {
                alert(" Cloned into exam.");
                if (onQuestionAdded) onQuestionAdded();
            } else {
                alert(" Failed to add from bank.");
            }
        } catch (e) {
            console.error(e);
        }
    };

    const getSeverityBadge = (severity) => {
        const badges = {
            CRITICAL: 'bg-danger text-white',
            HIGH: 'bg-warning text-dark',
            MEDIUM: 'bg-info text-dark',
            LOW: 'bg-secondary text-white'
        };
        return <span className={`badge ${badges[severity] || 'bg-light text-dark'}`}>{severity}</span>;
    };

    if (loading) return <LoadingState message="Generating AI Recommendations..." />;
    
    if (error) return (
        <div className="alert alert-danger mb-4">
            <strong>Error:</strong> {error}
        </div>
    );

    if (recommendations.length === 0) return (
        <div className="mb-4">
            <SectionHeader title="AI Recommendations" subtitle="Actionable insights to improve exam quality." />
            <EmptyState message="Your exam perfectly aligns with the blueprint! No recommendations at this time." />
        </div>
    );

    return (
        <div className="mb-4">
            <SectionHeader 
                title="AI Recommendations" 
                subtitle="Actionable insights based on blueprint gap analysis and quality issues." 
            />
            
            <div className="row g-3">
                {recommendations.map((rec, index) => (
                    <div key={index} className="col-12">
                        <div className={`card border-start border-4 shadow-sm ${rec.action === 'ADD' ? 'border-success' : rec.action === 'REMOVE' ? 'border-danger' : 'border-warning'}`}>
                            <div className="card-body">
                                <div className="d-flex justify-content-between align-items-center mb-2">
                                    <h6 className="mb-0 fw-bold">
                                        {rec.action === 'ADD' ? '➕ Gap Identified' : 
                                         rec.action === 'REMOVE' ? '➖ Excess Identified' : ' Quality Issue'}
                                    </h6>
                                    {getSeverityBadge(rec.severity || 'MEDIUM')}
                                </div>
                                <p className="mb-2 text-muted">{rec.reason}</p>
                                
                                {rec.candidates && rec.candidates.length > 0 && (
                                    <div className="mt-3">
                                        <p className="fw-bold mb-2 small text-primary">Suggested Candidates from Question Bank:</p>
                                        <ul className="list-group">
                                            {rec.candidates.map(candidate => (
                                                <li key={candidate.id} className="list-group-item d-flex justify-content-between align-items-center bg-light">
                                                    <span className="text-truncate" style={{maxWidth: '75%'}}>
                                                        {candidate.text}
                                                    </span>
                                                    <button 
                                                        className="btn btn-sm btn-outline-success"
                                                        onClick={() => handleAddCandidate(candidate.id)}
                                                    >
                                                        Add to Exam
                                                    </button>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default RecommendationPanel;
