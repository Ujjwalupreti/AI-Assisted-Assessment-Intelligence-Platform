import React from 'react';

const MetricCard = ({ title, value, subtitle, icon, className = '' }) => {
    return (
        <div className={`card shadow-sm h-100 ${className}`}>
            <div className="card-body">
                <div className="d-flex justify-content-between align-items-center mb-2">
                    <h6 className="card-title text-muted mb-0">{title}</h6>
                    {icon && <div className="text-primary">{icon}</div>}
                </div>
                <h2 className="mb-1">{value}</h2>
                {subtitle && <small className="text-muted">{subtitle}</small>}
            </div>
        </div>
    );
};

export default MetricCard;
