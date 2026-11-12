import React from 'react';
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react';


const AutomatedAssemblyPreview = ({ previewData, onBack, onConfirm }) => {
    if (!previewData) return null;

    const { selected_questions, actual_distribution, gaps, warnings } = previewData;

    return (
        <div className="card shadow-lg border-primary mb-4">
            <div className="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                <h5 className="mb-0"> Assessment Assembly Preview</h5>
                <span className="badge bg-light text-primary">{selected_questions.length} Questions</span>
            </div>
            
            <div className="card-body">
                {warnings && warnings.length > 0 && (
                    <div className="alert alert-warning">
                        <strong><AlertTriangle size={18} className="me-2" /> Warnings:</strong>
                        <ul className="mb-0 mt-2">
                            {warnings.map((w, i) => <li key={i}>{w}</li>)}
                        </ul>
                    </div>
                )}
                
                {gaps && gaps.length > 0 && (
                    <div className="alert alert-danger">
                        <strong><XCircle size={18} className="me-2" /> Blueprint Gaps:</strong>
                        <ul className="mb-0 mt-2">
                            {gaps.map((g, i) => <li key={i}>{g}</li>)}
                        </ul>
                    </div>
                )}

                <div className="row mb-4">
                    <div className="col-md-4">
                        <h6>Topic Distribution</h6>
                        <ul className="list-group list-group-sm">
                            {Object.entries(actual_distribution.topic || {}).map(([k, v]) => (
                                <li key={k} className="list-group-item d-flex justify-content-between align-items-center p-2">
                                    {k} <span className="badge bg-secondary rounded-pill">{v}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div className="col-md-4">
                        <h6>Difficulty</h6>
                        <ul className="list-group list-group-sm">
                            {Object.entries(actual_distribution.difficulty || {}).map(([k, v]) => (
                                <li key={k} className="list-group-item d-flex justify-content-between align-items-center p-2">
                                    {k} <span className="badge bg-secondary rounded-pill">{v}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div className="col-md-4">
                        <h6>Bloom Taxonomy</h6>
                        <ul className="list-group list-group-sm">
                            {Object.entries(actual_distribution.bloom || {}).map(([k, v]) => (
                                <li key={k} className="list-group-item d-flex justify-content-between align-items-center p-2">
                                    {k} <span className="badge bg-secondary rounded-pill">{v}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>

                <div className="d-flex justify-content-between mt-4">
                    <button type="button" className="btn btn-outline-secondary" onClick={onBack}>
                        ⬅️ Edit Settings
                    </button>
                    <div>
                        <button type="button" className="btn btn-primary" onClick={onConfirm}>
                            <CheckCircle size={18} className="me-2" /> Approve & Create Assessment
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AutomatedAssemblyPreview;
