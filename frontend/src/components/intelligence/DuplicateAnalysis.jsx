import React, { useState, useEffect } from 'react';
import { intelligenceService } from '../../services/intelligenceService';
import SectionHeader from '../common/SectionHeader';
import LoadingState from '../common/LoadingState';

const DuplicateAnalysis = ({ examId, duplicateSafety = 100 }) => {
    const [duplicates, setDuplicates] = useState([]);
    const [loading, setLoading] = useState(false);
    const [running, setRunning] = useState(false);

    let colorClass = 'text-success';
    if (duplicateSafety < 90) colorClass = 'text-warning';
    if (duplicateSafety < 70) colorClass = 'text-danger';

    useEffect(() => {
        if (examId) fetchDuplicates();
    }, [examId]);

    async function fetchDuplicates() {
        setLoading(true);
        try {
            const data = await intelligenceService.getDuplicates(examId);
            setDuplicates(data || []);
        } catch (error) {
            console.error("Failed to fetch duplicates:", error);
        }
        setLoading(false);
    };

    const handleRunDeduplication = async () => {
        setRunning(true);
        try {
            await intelligenceService.runDeduplication(examId);
            await fetchDuplicates();
            alert(" Deduplication scan complete!");
        } catch (error) {
            console.error("Failed to run deduplication:", error);
            alert(" Deduplication scan failed.");
        }
        setRunning(false);
    };

    const handleReview = async (groupId, decision, keeperId = null) => {
        try {
            const payload = { decision };
            if (keeperId) payload.keeper_question_id = keeperId;
            
            await intelligenceService.reviewDuplicate(groupId, payload);
            await fetchDuplicates();
        } catch (error) {
            console.error("Failed to submit review:", error);
            alert(" Failed to submit decision.");
        }
    };

    return (
        <div className="card shadow-sm border-0 mb-4 h-100">
            <div className="card-body p-4">
                <div className="d-flex justify-content-between align-items-center mb-3">
                    <div>
                        <h6 className="card-title text-muted mb-0">Duplicate Safety</h6>
                        <h2 className={`mb-1 ${colorClass}`}>{duplicateSafety}%</h2>
                        <small className="text-muted">Indicates exam uniqueness</small>
                    </div>
                    <button 
                        className="btn btn-outline-primary btn-sm fw-bold"
                        onClick={handleRunDeduplication}
                        disabled={running}
                    >
                        {running ? 'Scanning...' : ' Scan for Duplicates'}
                    </button>
                </div>

                {loading ? (
                    <LoadingState message="Loading duplicates..." />
                ) : duplicates.length > 0 ? (
                    <div className="mt-4">
                        <h6 className="fw-bold mb-3">Duplicate Groups Found: {duplicates.length}</h6>
                        <div className="accordion" id="duplicatesAccordion">
                            {duplicates.map((group, index) => {
                                const groupId = group.group_id || group.id;
                                const members = group.members || group.questions || [];
                                return (
                                <div className="accordion-item" key={groupId}>
                                    <h2 className="accordion-header">
                                        <button className="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target={`#collapseGroup${groupId}`}>
                                            <span className="badge bg-warning text-dark me-2">Group {index + 1}</span>
                                            {members.length} Similar Questions
                                            {group.status === 'RESOLVED' && <span className="badge bg-success ms-auto">Resolved</span>}
                                        </button>
                                    </h2>
                                    <div id={`collapseGroup${groupId}`} className="accordion-collapse collapse" data-bs-parent="#duplicatesAccordion">
                                        <div className="accordion-body">
                                            {members.map(m => {
                                                const qId = m.question_id || m.id;
                                                const qText = m.question_text || m.text_preview;
                                                return (
                                                <div key={qId} className="p-2 border rounded mb-2" style={{ background: 'var(--surface-secondary)' }}>
                                                    <div className="d-flex justify-content-between align-items-start">
                                                        <div className="text-truncate" style={{maxWidth: '80%'}}>
                                                            <small className="text-muted d-block">ID: {qId}</small>
                                                            {qText}
                                                        </div>
                                                        {group.status === 'PENDING' && (
                                                            <button 
                                                                className="btn btn-sm btn-success"
                                                                onClick={() => handleReview(groupId, 'ARCHIVE', qId)}
                                                                title="Keep this question and archive the rest"
                                                            >
                                                                Keep This
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>
                                            )})}
                                            {group.status === 'PENDING' && (
                                                <div className="text-end mt-3 border-top pt-3">
                                                    <button 
                                                        className="btn btn-sm btn-outline-secondary"
                                                        onClick={() => handleReview(groupId, 'KEEP_ALL')}
                                                    >
                                                        Ignore & Keep All
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                );
                            })}
                        </div>
                    </div>
                ) : (
                    <div className="text-center text-muted mt-4 p-3 bg-light rounded">
                        No duplicates found in this exam.
                    </div>
                )}
            </div>
        </div>
    );
};

export default DuplicateAnalysis;
