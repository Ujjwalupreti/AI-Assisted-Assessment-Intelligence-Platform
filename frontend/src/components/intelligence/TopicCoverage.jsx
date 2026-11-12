import React from 'react';
import ProgressBar from '../common/ProgressBar';

const TopicCoverage = ({ data, targetData = null, totalQuestions }) => {
    // Combine keys from both data and targetData to show all relevant topics
    const allTopics = new Set([...Object.keys(data || {}), ...Object.keys(targetData || {})]);
    
    // Convert to array and sort alphabetically
    const topics = Array.from(allTopics).sort();
    
    return (
        <div className="card shadow-sm h-100">
            <div className="card-header border-bottom-0 pt-3" style={{ background: 'transparent' }}>
                <h6 className="mb-0 fw-bold">Topic Coverage</h6>
            </div>
            <div className="card-body pt-2" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                {topics.length === 0 ? (
                    <p className="text-muted small">No topic data available.</p>
                ) : (
                    topics.map(topic => {
                        const count = data[topic] || 0;
                        const pct = totalQuestions > 0 ? (count / totalQuestions) * 100 : 0;
                        const targetPct = targetData ? targetData[topic] : null;
                        
                        let color = 'bg-secondary';
                        if (targetPct !== null && targetPct !== undefined) {
                            const diff = pct - targetPct;
                            if (Math.abs(diff) <= 10) color = 'bg-success';
                            else if (Math.abs(diff) <= 20) color = 'bg-warning';
                            else color = 'bg-danger';
                        }
    
                        return (
                            <div key={topic} className="mb-3">
                                <div className="d-flex justify-content-between mb-1 small">
                                    <span className="text-truncate" style={{ maxWidth: '60%' }} title={topic}>
                                        {topic} <span className="text-muted">({count})</span>
                                    </span>
                                    <span>
                                        <span className="fw-bold">{Math.round(pct)}%</span>
                                        {targetPct !== null && targetPct !== undefined && (
                                            <span className="text-muted ms-1">/ {targetPct}%</span>
                                        )}
                                    </span>
                                </div>
                                <ProgressBar percentage={pct} color={color} showLabel={false} height="8px" />
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
};

export default TopicCoverage;
