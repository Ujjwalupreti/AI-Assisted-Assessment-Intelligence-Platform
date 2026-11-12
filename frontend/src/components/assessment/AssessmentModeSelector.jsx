import React from 'react';

const AssessmentModeSelector = ({ mode, setMode }) => {
    return (
        <div className="mb-4">
            <h5 className="mb-3">How do you want to create this assessment?</h5>
            <div className="d-flex gap-3">
                <div 
                    className={`card flex-fill cursor-pointer ${mode === 'manual' ? 'border-primary shadow' : 'border-secondary'}`}
                    onClick={() => setMode('manual')}
                    style={{ cursor: 'pointer' }}
                >
                    <div className="card-body text-center">
                        <h5 className={`card-title ${mode === 'manual' ? 'text-primary' : ''}`}>️ Manual</h5>
                        <p className="card-text text-muted small">You hand-pick questions, upload CSVs, and use the Question Bank. AI assists with intelligence, but you build it.</p>
                    </div>
                </div>
                
                <div 
                    className={`card flex-fill cursor-pointer ${mode === 'automated' ? 'border-primary shadow' : 'border-secondary'}`}
                    onClick={() => setMode('automated')}
                    style={{ cursor: 'pointer' }}
                >
                    <div className="card-body text-center">
                        <h5 className={`card-title ${mode === 'automated' ? 'text-primary' : ''}`}> Automated</h5>
                        <p className="card-text text-muted small">Configure your blueprint (topics, difficulty, count). The system automatically selects the best questions from the Question Bank.</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AssessmentModeSelector;
