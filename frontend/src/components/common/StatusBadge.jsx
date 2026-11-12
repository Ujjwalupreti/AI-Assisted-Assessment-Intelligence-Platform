import React from 'react';

const StatusBadge = ({ status, text }) => {
    let badgeClass = 'bg-secondary';
    
    // Auto-derive color from status/text
    const lText = (status || text || '').toLowerCase();
    if (lText.includes('good') || lText.includes('success') || lText.includes('active') || lText.includes('completed')) {
        badgeClass = 'bg-success';
    } else if (lText.includes('warn') || lText.includes('pending') || lText.includes('review')) {
        badgeClass = 'bg-warning text-dark';
    } else if (lText.includes('err') || lText.includes('fail') || lText.includes('danger') || lText.includes('critical')) {
        badgeClass = 'bg-danger';
    } else if (lText.includes('info')) {
        badgeClass = 'bg-info text-dark';
    }

    return (
        <span className={`badge ${badgeClass} rounded-pill`}>
            {text || status}
        </span>
    );
};

export default StatusBadge;
