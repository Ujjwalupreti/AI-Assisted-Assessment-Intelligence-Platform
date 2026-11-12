import React from 'react';

const ProgressBar = ({ label, percentage, color = 'bg-primary', height = '12px', showLabel = true }) => {
    // Ensure percentage is between 0 and 100
    const safePercentage = Math.max(0, Math.min(100, percentage || 0));
    
    return (
        <div className="mb-3">
            {showLabel && label && (
                <div className="d-flex justify-content-between mb-1">
                    <span className="small">{label}</span>
                    <span className="small fw-bold">{Math.round(safePercentage)}%</span>
                </div>
            )}
            <div className="progress" style={{ height }}>
                <div 
                    className={`progress-bar ${color}`} 
                    role="progressbar" 
                    style={{ width: `${safePercentage}%` }} 
                    aria-valuenow={safePercentage} 
                    aria-valuemin="0" 
                    aria-valuemax="100"
                ></div>
            </div>
        </div>
    );
};

export default ProgressBar;
