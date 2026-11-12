import React from 'react';
import { FaExclamationCircle } from 'react-icons/fa';

const ErrorState = ({ message = "Something went wrong.", onRetry = null }) => {
    return (
        <div className="d-flex flex-column align-items-center justify-content-center p-5 text-danger">
            <FaExclamationCircle size={48} className="mb-3" />
            <h5>{message}</h5>
            {onRetry && (
                <button className="btn btn-outline-danger mt-3" onClick={onRetry}>
                    Retry
                </button>
            )}
        </div>
    );
};

export default ErrorState;
