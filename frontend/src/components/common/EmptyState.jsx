import React from 'react';
import { FaInbox } from 'react-icons/fa';

const EmptyState = ({ message = "No data available.", icon = <FaInbox size={48} /> }) => {
    return (
        <div className="d-flex flex-column align-items-center justify-content-center p-5 text-muted">
            <div className="mb-3 opacity-50">{icon}</div>
            <h5>{message}</h5>
        </div>
    );
};

export default EmptyState;
