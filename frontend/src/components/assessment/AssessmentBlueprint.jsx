import React, { useState, useEffect } from 'react';
import SectionHeader from '../common/SectionHeader';
import { useAuth } from '../../AuthContext';

const AssessmentBlueprint = ({ blueprint, setBlueprint }) => {
    const { API_BASE_URL, getHeaders } = useAuth();
    const [availableTopics, setAvailableTopics] = useState([]);

    useEffect(() => {
        const fetchTopics = async () => {
            try {
                const res = await fetch(`${API_BASE_URL}/exams/bank`, { headers: getHeaders() });
                if (res.ok) {
                    const data = await res.json();
                    const uniqueTopics = [...new Set(data.map(q => q.topic).filter(Boolean))];
                    setAvailableTopics(uniqueTopics);
                }
            } catch (e) {
                console.error(e);
            }
        };
        fetchTopics();
    }, [API_BASE_URL]);
    
    const handleBloomChange = (level, value) => {
        setBlueprint(prev => ({
            ...prev,
            bloom_distribution: {
                ...prev.bloom_distribution,
                [level]: parseInt(value) || 0
            }
        }));
    };

    const handleDifficultyChange = (level, value) => {
        setBlueprint(prev => ({
            ...prev,
            difficulty_distribution: {
                ...prev.difficulty_distribution,
                [level]: parseInt(value) || 0
            }
        }));
    };

    const [manualTopics, setManualTopics] = useState({});
    const [manualDifficulty, setManualDifficulty] = useState({});

    const redistributeRemaining = (distObj, manualFlags) => {
        const keys = Object.keys(distObj);
        if (keys.length === 0) return {};
        
        let manualSum = 0;
        let autoKeys = [];
        keys.forEach(k => {
            if (manualFlags[k]) manualSum += (distObj[k] || 0);
            else autoKeys.push(k);
        });
        
        if (manualSum > 100) {
            return distObj; // Exceeds 100%, leave as is to show error
        }
        
        const remaining = 100 - manualSum;
        if (autoKeys.length === 0) return distObj;
        
        const basePct = Math.floor((remaining / autoKeys.length) * 100) / 100;
        const totalBase = basePct * autoKeys.length;
        let remainder = Math.round((remaining - totalBase) * 100);
        
        const newDist = { ...distObj };
        autoKeys.forEach(k => {
            let pct = basePct;
            if (remainder > 0) {
                pct += 0.01;
                remainder -= 1;
            }
            newDist[k] = Math.round(pct * 100) / 100;
        });
        
        return newDist;
    };

    const addTopic = () => {
        setBlueprint(prev => {
            const newTopics = { ...prev.topic_distribution, '': 0 };
            return { ...prev, topic_distribution: redistributeRemaining(newTopics, manualTopics) };
        });
    };

    const updateTopicName = (oldName, newName) => {
        const trimmed = newName.trim();
        if (!trimmed || oldName === trimmed) return;
        
        // Update manual flag key if it existed
        setManualTopics(prev => {
            if (!prev[oldName]) return prev;
            const next = { ...prev };
            next[trimmed] = next[oldName];
            delete next[oldName];
            return next;
        });
        
        setBlueprint(prev => {
            const newTopics = { ...prev.topic_distribution };
            const value = newTopics[oldName];
            delete newTopics[oldName];
            newTopics[trimmed] = value;
            return { ...prev, topic_distribution: redistributeRemaining(newTopics, manualTopics) };
        });
    };

    const removeTopic = (topic) => {
        setManualTopics(prev => {
            const next = { ...prev };
            delete next[topic];
            return next;
        });
        setBlueprint(prev => {
            const newTopics = { ...prev.topic_distribution };
            delete newTopics[topic];
            // Since we deleted a key, we might have removed a manual topic, so we must re-evaluate manual flags
            const tempManual = { ...manualTopics };
            delete tempManual[topic];
            return { ...prev, topic_distribution: redistributeRemaining(newTopics, tempManual) };
        });
    };

    const handleTopicManualChange = (topic, value) => {
        let val = parseFloat(value);
        if (isNaN(val) || val < 0) val = 0;
        if (val > 100) val = 100;
        
        setManualTopics(prev => ({ ...prev, [topic]: true }));
        setBlueprint(prev => {
            const newTopics = { ...prev.topic_distribution, [topic]: val };
            return { ...prev, topic_distribution: redistributeRemaining(newTopics, { ...manualTopics, [topic]: true }) };
        });
    };

    const resetTopics = () => {
        setManualTopics({});
        setBlueprint(prev => ({ ...prev, topic_distribution: redistributeRemaining(prev.topic_distribution, {}) }));
    };

    const toggleDifficulty = (level, checked) => {
        if (!checked) {
            setManualDifficulty(prev => {
                const next = { ...prev };
                delete next[level];
                return next;
            });
        }
        setBlueprint(prev => {
            const newDiff = { ...prev.difficulty_distribution };
            if (checked) {
                newDiff[level] = 0;
            } else {
                delete newDiff[level];
            }
            const tempManual = { ...manualDifficulty };
            if (!checked) delete tempManual[level];
            return { ...prev, difficulty_distribution: redistributeRemaining(newDiff, tempManual) };
        });
    };

    const handleDifficultyManualChange = (level, value) => {
        let val = parseFloat(value);
        if (isNaN(val) || val < 0) val = 0;
        if (val > 100) val = 100;
        
        setManualDifficulty(prev => ({ ...prev, [level]: true }));
        setBlueprint(prev => {
            const newDiff = { ...prev.difficulty_distribution, [level]: val };
            return { ...prev, difficulty_distribution: redistributeRemaining(newDiff, { ...manualDifficulty, [level]: true }) };
        });
    };

    const resetDifficulty = () => {
        setManualDifficulty({});
        setBlueprint(prev => ({ ...prev, difficulty_distribution: redistributeRemaining(prev.difficulty_distribution, {}) }));
    };

    // Calculate totals
    const bloomTotal = Object.values(blueprint.bloom_distribution || {}).reduce((a, b) => a + b, 0);
    const difficultyTotal = Object.values(blueprint.difficulty_distribution || {}).reduce((a, b) => a + b, 0);
    const topicTotal = Object.values(blueprint.topic_distribution || {}).reduce((a, b) => a + b, 0);

    return (
        <div className="mt-4">
            <SectionHeader title=" Assessment Blueprint (Optional)" subtitle="Configure target percentages for AI generation and analysis." />
            
            <div className="row g-4">
                {/* Difficulty */}
                <div className="col-md-6">
                    <div className="card shadow-sm h-100">
                        <div className="card-header bg-light">
                            <div>
                                <h6 className="mb-0">Difficulty (%)</h6>
                                <small className="text-muted" style={{ fontSize: '0.75rem' }}>Balanced defaults — you can adjust the weights</small>
                            </div>
                        </div>
                        <div className="card-body">
                            {['Easy', 'Medium', 'Hard'].map(level => (
                                <div key={level} className="mb-2 d-flex align-items-center gap-2">
                                    <div className="form-check w-50 mb-0">
                                        <input 
                                            type="checkbox" 
                                            className="form-check-input"
                                            id={`diff-${level}`}
                                            checked={blueprint.difficulty_distribution?.[level] !== undefined}
                                            onChange={(e) => toggleDifficulty(level, e.target.checked)}
                                        />
                                        <label className="form-check-label small" htmlFor={`diff-${level}`}>
                                            {level}
                                        </label>
                                    </div>
                                    <div className="input-group input-group-sm w-25 ms-auto">
                                        <input 
                                            type="number" 
                                            className={`form-control text-center ${manualDifficulty[level] ? 'fw-bold border-primary' : 'bg-light'}`}
                                            value={blueprint.difficulty_distribution?.[level] ?? ''}
                                            onChange={(e) => handleDifficultyManualChange(level, e.target.value)}
                                            min="0" max="100"
                                            disabled={blueprint.difficulty_distribution?.[level] === undefined}
                                        />
                                        <span className="input-group-text">%</span>
                                    </div>
                                </div>
                            ))}
                            {Object.keys(manualDifficulty).length > 0 && (
                                <div className="text-end mt-2">
                                    <button type="button" className="btn btn-sm btn-link text-decoration-none py-0" onClick={resetDifficulty}>Reset Balanced</button>
                                </div>
                            )}
                            <div className={`mt-3 small fw-bold text-end ${Math.round(difficultyTotal) > 100 ? 'text-danger' : Math.round(difficultyTotal) === 100 ? 'text-success' : 'text-muted'}`}>
                                Total: {Math.round(difficultyTotal)}% {Math.round(difficultyTotal) === 100 ? '✓' : ''}
                            </div>
                            {(() => {
                                const manualSum = Object.keys(manualDifficulty).reduce((sum, level) => sum + (blueprint.difficulty_distribution?.[level] || 0), 0);
                                return manualSum > 100 ? <div className="text-danger small text-end mt-1">Fixed weights exceed 100%. Reduce one or more values.</div> : null;
                            })()}
                        </div>
                    </div>
                </div>

                {/* Topic Coverage */}
                <div className="col-md-6">
                    <div className="card shadow-sm h-100">
                        <div className="card-header bg-light d-flex justify-content-between align-items-center">
                            <div>
                                <h6 className="mb-0">Topics (%)</h6>
                                <small className="text-muted" style={{ fontSize: '0.75rem' }}>Balanced defaults — you can adjust the weights</small>
                            </div>
                            <button type="button" className="btn btn-sm btn-outline-primary py-0" onClick={addTopic}>+ Add</button>
                        </div>
                        <div className="card-body">
                            {Object.entries(blueprint.topic_distribution || {}).map(([topic, value], idx) => (
                                <div key={idx} className="mb-2 d-flex align-items-center gap-2">
                                    <input 
                                        type="text" 
                                        list="topic-options"
                                        className="form-control form-control-sm" 
                                        placeholder="Search or enter topic"
                                        defaultValue={topic}
                                        onBlur={(e) => updateTopicName(topic, e.target.value)}
                                    />
                                    <div className="input-group input-group-sm w-25">
                                        <input 
                                            type="number" 
                                            className={`form-control text-center ${manualTopics[topic] ? 'fw-bold border-primary' : 'bg-light'}`}
                                            value={value ?? ''}
                                            onChange={(e) => handleTopicManualChange(topic, e.target.value)}
                                            min="0" max="100"
                                        />
                                        <span className="input-group-text">%</span>
                                    </div>
                                    <button type="button" className="btn btn-sm btn-text text-danger px-1" onClick={() => removeTopic(topic)}>×</button>
                                </div>
                            ))}
                            {Object.keys(manualTopics).length > 0 && (
                                <div className="text-end mt-2">
                                    <button type="button" className="btn btn-sm btn-link text-decoration-none py-0" onClick={resetTopics}>Reset Balanced</button>
                                </div>
                            )}
                            <div className={`mt-3 small fw-bold text-end ${Math.round(topicTotal) > 100 ? 'text-danger' : Math.round(topicTotal) === 100 ? 'text-success' : 'text-muted'}`}>
                                Total: {Math.round(topicTotal)}% {Math.round(topicTotal) === 100 ? '✓' : ''}
                            </div>
                            {(() => {
                                const manualSum = Object.keys(manualTopics).reduce((sum, t) => sum + (blueprint.topic_distribution?.[t] || 0), 0);
                                return manualSum > 100 ? <div className="text-danger small text-end mt-1">Fixed weights exceed 100%. Reduce one or more values.</div> : null;
                            })()}
                            <datalist id="topic-options">
                                {availableTopics.map((t, i) => <option key={i} value={t}>{t}</option>)}
                            </datalist>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AssessmentBlueprint;
