import React from 'react';

const AIRecommendations = ({ examId, gapTopic, gapBloom, gapDifficulty, setGapTopic, setGapBloom, setGapDifficulty, useRag, setUseRag, onGenerateGap, generating, generatedQuestion }) => {
    return (
        <div className="card shadow-sm mt-4">
            <div className="card-header pt-3 border-bottom-0" style={{ background: 'transparent' }}>
                <h5 className="fw-bold m-0 text-primary"> AI Recommendations & Gap Filling</h5>
                <p className="text-muted small mb-0">Generate new questions to address blueprint gaps.</p>
            </div>
            <div className="card-body">
                <div className="row g-3">
                    <div className="col-md-4">
                        <label className="form-label small fw-bold">Topic Need</label>
                        <input type="text" className="form-control" placeholder="e.g. Trees" value={gapTopic} onChange={e => setGapTopic(e.target.value)} />
                    </div>
                    <div className="col-md-4">
                        <label className="form-label small fw-bold">Bloom's Level</label>
                        <select className="form-select" value={gapBloom} onChange={e => setGapBloom(e.target.value)}>
                            <option>Remember</option>
                            <option>Understand</option>
                            <option>Apply</option>
                            <option>Analyze</option>
                            <option>Evaluate</option>
                            <option>Create</option>
                        </select>
                    </div>
                    <div className="col-md-4">
                        <label className="form-label small fw-bold">Difficulty</label>
                        <select className="form-select" value={gapDifficulty} onChange={e => setGapDifficulty(e.target.value)}>
                            <option>Easy</option>
                            <option>Medium</option>
                            <option>Hard</option>
                        </select>
                    </div>
                </div>
                <div className="mt-3">
                    <button 
                        className="btn btn-outline-primary" 
                        onClick={onGenerateGap}
                        disabled={generating || !gapTopic}
                    >
                        {generating ? 'Generating...' : 'Generate Gap Question'}
                    </button>
                    <div className="form-check mt-2">
                        <input 
                            className="form-check-input" 
                            type="checkbox" 
                            id="useRagCheck" 
                            checked={useRag} 
                            onChange={e => setUseRag(e.target.checked)} 
                        />
                        <label className="form-check-label small" htmlFor="useRagCheck">
                            Use RAG (Reference Material)
                        </label>
                    </div>
                </div>

                {generatedQuestion && (
                    <div className="mt-4 p-3 border rounded" style={{ background: 'var(--surface-secondary)' }}>
                        <h6 className="fw-bold text-primary">Generated Candidate:</h6>
                        <p>{generatedQuestion.text}</p>
                        <ul className="list-unstyled mb-0 small">
                            <li><strong>A:</strong> {generatedQuestion.option_a}</li>
                            <li><strong>B:</strong> {generatedQuestion.option_b}</li>
                            <li><strong>C:</strong> {generatedQuestion.option_c}</li>
                            <li><strong>D:</strong> {generatedQuestion.option_d}</li>
                        </ul>
                        <div className="mt-2 text-success small fw-bold">
                            Correct: Option {generatedQuestion.correct_option}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default AIRecommendations;
