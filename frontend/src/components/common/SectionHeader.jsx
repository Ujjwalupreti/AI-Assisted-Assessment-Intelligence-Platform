import React from 'react';

const SectionHeader = ({ title, subtitle, action }) => {
    return (
        <div className="d-flex justify-content-between align-items-center border-bottom pb-3 mb-4">
            <div>
                <h4 className="mb-1">{title}</h4>
                {subtitle && <p className="text-muted mb-0 small">{subtitle}</p>}
            </div>
            {action && <div>{action}</div>}
        </div>
    );
};

export default SectionHeader;
