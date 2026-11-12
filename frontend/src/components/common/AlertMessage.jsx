import React from 'react';
import { FaInfoCircle, FaExclamationTriangle, FaCheckCircle, FaTimesCircle } from 'react-icons/fa';

const AlertMessage = ({ type = 'info', message, dismissible = false, onClose = null }) => {
    if (!message) return null;

    const config = {
        info: { color: 'alert-info', icon: <FaInfoCircle className="me-2" /> },
        warning: { color: 'alert-warning', icon: <FaExclamationTriangle className="me-2" /> },
        success: { color: 'alert-success', icon: <FaCheckCircle className="me-2" /> },
        danger: { color: 'alert-danger', icon: <FaTimesCircle className="me-2" /> }
    };

    const { color, icon } = config[type] || config['info'];

    return (
        <div className={`alert ${color} ${dismissible ? 'alert-dismissible fade show' : ''} d-flex align-items-center`} role="alert">
            {icon}
            <div>{message}</div>
            {dismissible && (
                <button type="button" className="btn-close" onClick={onClose} aria-label="Close"></button>
            )}
        </div>
    );
};

export default AlertMessage;
