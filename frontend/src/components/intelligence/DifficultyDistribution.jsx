import React from 'react';
import ProgressBar from '../common/ProgressBar';

const DifficultyDistribution = ({ data, targetData = null, totalQuestions }) => {
    const levels = ['Easy', 'Medium', 'Hard'];
    
    return (
        <div className="card shadow-sm h-100">
            <div className="card-header border-bottom-0 pt-3" style={{ background: 'transparent' }}>
                <h6 className="mb-0 fw-bold">Difficulty Distribution</h6>
            </div>
            <div className="card-body pt-2">
                {levels.map(level => {
                    const count = data[level] || 0;
                    const pct = totalQuestions > 0 ? (count / totalQuestions) * 100 : 0;
                    const targetPct = targetData ? targetData[level] : null;
                    
                    let color = 'bg-info';
                    if (targetPct !== null && targetPct !== undefined) {
                        const diff = pct - targetPct;
                        if (Math.abs(diff) <= 10) color = 'bg-success';
                        else if (Math.abs(diff) <= 20) color = 'bg-warning';
                        else color = 'bg-danger';
                    }

                    return (
                        <div key={level} className="mb-3">
                            <div className="d-flex justify-content-between mb-1 small">
                                <span>{level} <span className="text-muted">({count})</span></span>
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
                })}
            </div>
        </div>
    );
};

export default DifficultyDistribution;
