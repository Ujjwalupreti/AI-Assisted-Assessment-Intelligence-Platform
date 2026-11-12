import React from 'react';

const LoadingState = ({ message = "Loading..." }) => {
    return (
        <div className="d-flex flex-column align-items-center justify-content-center p-5 text-muted">
            <div className="spinner-border mb-3" role="status" style={{ width: '3rem', height: '3rem' }}>
                <span className="visually-hidden">Loading...</span>
            </div>
            <h5>{message}</h5>
        </div>
    );
};

export default LoadingState;
