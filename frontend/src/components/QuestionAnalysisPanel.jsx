import React from 'react';
import { AlertTriangle } from 'lucide-react';


const SEVERITY_COLOR = { HIGH: 'danger', CRITICAL: 'danger', MEDIUM: 'warning', LOW: 'secondary' };

const QuestionAnalysisPanel = ({ aiData, onAccept, onEdit, onIgnore }) => {
  if (!aiData) return null;

  // BUG-02 FIX: pipeline returns review.required (nested), not flat review_required
  const { classification, quality, validation, alignment, recommendations, explanations, review, duplicate } = aiData;
  const review_required = review?.required;
  const { topic, bloom, difficulty, question_type } = classification || {};

  const getStatusColor = (status) => {
    if (status === 'MATCH' || status === 'GOOD') return 'text-success';
    if (status === 'WARNING' || status === 'MISMATCH') return 'text-warning';
    return 'text-danger';
  };

  // BUG-03 FIX: quality.dimensions is null when LLM unavailable — guard it
  const getDimVal = (key) => {
    const v = quality?.dimensions?.[key];
    return v != null ? (v * 100).toFixed(0) + '%' : 'N/A';
  };

  // BUG-07: Duplicate display helpers
  const dupRisk = duplicate?.risk_label || 'LOW';
  const dupColor = dupRisk === 'HIGH_DUPLICATE_RISK' ? 'danger' : dupRisk === 'SIMILAR' ? 'warning' : 'success';
  const dupSimilar = duplicate?.similar_questions || [];

  return (
    <div className="card border-primary shadow-sm mb-4">
      <div className="card-header bg-primary text-white d-flex justify-content-between align-items-center">
        <h5 className="m-0">AI QUESTION INTELLIGENCE</h5>
        <div className="d-flex gap-2">
          {/* Status Indicators */}
          {aiData.teacher_review_status === 'ACCEPTED' || aiData.teacher_review_status === 'EDITED' ? (
              <span className="badge bg-success">Teacher Confirmed</span>
          ) : (
              <span className="badge bg-info text-dark">AI Prediction</span>
          )}
          
          {aiData.analysis_status === 'FAILED' ? (
              <span className="badge bg-danger">Analysis Failed</span>
          ) : aiData.analysis_status === 'DEGRADED' || aiData.status === 'PARTIAL' ? (
              <span className="badge bg-warning text-dark">Partial Analysis (Heuristic)</span>
          ) : null}

          {review_required && <span className="badge bg-danger">Review Required</span>}
        </div>
      </div>
      
      <div className="card-body">
        <div className="row">
          {/* Left Column */}
          <div className="col-md-6 border-end">
            <h6 className="fw-bold border-bottom pb-2">METADATA</h6>
            <div className="d-flex justify-content-between mb-1">
              <span>Topic:</span>
              <span className="fw-bold">{topic?.label} <small className="text-muted">({topic?.confidence != null ? (topic.confidence * 100).toFixed(0) : '?'}%)</small></span>
            </div>
            <div className="d-flex justify-content-between mb-1">
              <span>Bloom:</span>
              <span className="fw-bold">{bloom?.label} <small className="text-muted">({bloom?.confidence != null ? (bloom.confidence * 100).toFixed(0) : '?'}%)</small></span>
            </div>
            <div className="d-flex justify-content-between mb-1">
              <span>Difficulty:</span>
              <span className="fw-bold">{difficulty?.label} <small className="text-muted">({difficulty?.confidence != null ? (difficulty.confidence * 100).toFixed(0) : '?'}%)</small></span>
            </div>
            <div className="d-flex justify-content-between mb-3">
              <span>Type:</span>
              <span className="fw-bold">{question_type?.label} <small className="text-muted">({question_type?.confidence != null ? (question_type.confidence * 100).toFixed(0) : '?'}%)</small></span>
            </div>

            <h6 className="fw-bold border-bottom pb-2">ALIGNMENT</h6>
            <div className="d-flex justify-content-between mb-1">
              <span>Topic Match:</span>
              <span className={`fw-bold ${getStatusColor(alignment?.topic)}`}>{alignment?.topic || 'NOT_CHECKED'}</span>
            </div>
            <div className="d-flex justify-content-between mb-1">
              <span>Bloom Match:</span>
              <span className={`fw-bold ${getStatusColor(alignment?.bloom)}`}>{alignment?.bloom || 'NOT_CHECKED'}</span>
            </div>
            <div className="d-flex justify-content-between mb-3">
              <span>Difficulty Match:</span>
              <span className={`fw-bold ${getStatusColor(alignment?.difficulty)}`}>{alignment?.difficulty || 'NOT_CHECKED'}</span>
            </div>

            {/* BUG-07 FIX: Show duplicate detection results */}
            <h6 className="fw-bold border-bottom pb-2">DUPLICATE DETECTION</h6>
            <div className="d-flex justify-content-between mb-1">
              <span>Similarity Risk:</span>
              <span className={`fw-bold text-${dupColor}`}>{dupRisk.replace('_', ' ')} ({duplicate?.risk != null ? (duplicate.risk * 100).toFixed(0) : 0}%)</span>
            </div>
            {dupSimilar.length > 0 && (
              <div className="small text-muted mt-1">
                <div className="fw-bold mb-1">Similar questions found:</div>
                {dupSimilar.map((sq, i) => (
                  <div key={i} className="mb-1 ps-2 border-start border-warning">
                    <span className="badge bg-warning text-dark me-1">{(sq.similarity * 100).toFixed(0)}%</span>
                    {sq.text_preview?.substring(0, 60)}...
                  </div>
                ))}
              </div>
            )}
            {duplicate?.is_duplicate && (
              <div className="alert alert-danger py-1 px-2 small mt-2 mb-0">
                <AlertTriangle size={18} className="me-2" /> Possible duplicate of question #{duplicate.similar_question_id}
              </div>
            )}
          </div>

          {/* Right Column */}
          <div className="col-md-6">
            <h6 className="fw-bold border-bottom pb-2">QUALITY CHECK</h6>
            <div className="d-flex justify-content-between align-items-center mb-2">
              <span>Overall Score:</span>
              {/* BUG-03+14 FIX: null score shows N/A not 0/100 */}
              {quality?.overall_score != null ? (
                <h5 className={`m-0 fw-bold ${quality.overall_score > 0.7 ? 'text-success' : 'text-warning'}`}>
                  {(quality.overall_score * 100).toFixed(0)} / 100
                </h5>
              ) : (
                <span className="text-muted small fst-italic">N/A (LLM unavailable)</span>
              )}
            </div>
            {quality?.dimensions ? (
              <div className="small mb-3">
                <div className="d-flex justify-content-between"><span>Clarity:</span> <span>{getDimVal('clarity')}</span></div>
                <div className="d-flex justify-content-between"><span>Completeness:</span> <span>{getDimVal('completeness')}</span></div>
                <div className="d-flex justify-content-between"><span>Specificity:</span> <span>{getDimVal('specificity')}</span></div>
                <div className="d-flex justify-content-between"><span>Ambiguity Risk:</span> <span>{getDimVal('ambiguity')}</span></div>
              </div>
            ) : (
              <p className="small text-muted fst-italic mb-3">Quality dimensions unavailable (requires LLM).</p>
            )}

            {question_type?.label === 'MCQ' && (
              <>
                <h6 className="fw-bold border-bottom pb-2">MCQ VALIDATION</h6>
                {validation?.valid ? (
                  <p className="text-success small fw-bold m-0 mb-3">✓ All options are valid.</p>
                ) : (
                  <ul className="text-danger small mb-3 p-0 ps-3">
                    {validation?.issues?.map((iss, i) => (
                      <li key={i}>{iss.message}</li>
                    ))}
                  </ul>
                )}
              </>
            )}

            {review?.reasons?.length > 0 && (
              <>
                <h6 className="fw-bold border-bottom pb-2">REVIEW REASONS</h6>
                <ul className="small text-warning mb-0 ps-3">
                  {review.reasons.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </>
            )}
          </div>
        </div>

        {/* Bottom Section */}
        <div className="mt-3 bg-light p-3 rounded">
          <h6 className="fw-bold text-primary">AI RECOMMENDATIONS</h6>
          {/* BUG-01 FIX: recommendations are objects, not strings */}
          {recommendations?.length > 0 ? (
            <ul className="small mb-3 list-unstyled">
              {recommendations.map((rec, i) => (
                <li key={i} className="mb-2 p-2 border-start border-3 border-warning">
                  <span className={`badge bg-${SEVERITY_COLOR[rec.severity] || 'secondary'} me-2`}>{rec.severity}</span>
                  <strong>{rec.issue}:</strong> {rec.recommendation}
                  {rec.suggested_improvement && (
                    <div className="text-muted mt-1 fst-italic"> Suggested: {rec.suggested_improvement}</div>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="small text-muted mb-3">No specific recommendations.</p>
          )}

          <h6 className="fw-bold text-primary">WHY DID AI DECIDE THIS?</h6>
          <p className="small mb-1"><strong>Bloom ({bloom?.label}):</strong> {explanations?.bloom}</p>
          <p className="small mb-1"><strong>Difficulty ({difficulty?.label}):</strong> {explanations?.difficulty}</p>
          <p className="small mb-3"><strong>Quality:</strong> {explanations?.quality}</p>
        </div>
      </div>

      <div className="card-footer d-flex gap-2 justify-content-end bg-white">
        <button className="btn btn-outline-secondary" onClick={onIgnore}>Ignore AI</button>
        <button className="btn btn-warning" onClick={onEdit}>Edit Manually</button>
        <button className="btn btn-success fw-bold" onClick={onAccept}>✓ Accept Analysis</button>
      </div>
    </div>
  );
};

export default QuestionAnalysisPanel;
