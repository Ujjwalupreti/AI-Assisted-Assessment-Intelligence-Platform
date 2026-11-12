import React, { useState, useEffect } from 'react';
import { intelligenceService } from '../../services/intelligenceService';
import SectionHeader from '../common/SectionHeader';
import LoadingState from '../common/LoadingState';

const SlotGenerator = ({ examId }) => {
    const [slots, setSlots] = useState([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    
    const [numSlots, setNumSlots] = useState(2);
    const [questionsPerSlot, setQuestionsPerSlot] = useState('');

    useEffect(() => {
        fetchSlots();
    }, [examId]);

    async function fetchSlots() {
        setLoading(true);
        try {
            const data = await intelligenceService.getSlots(examId);
            setSlots(data || []);
        } catch (error) {
            console.error("Failed to fetch slots:", error);
        }
        setLoading(false);
    };

    const handleGenerate = async () => {
        setGenerating(true);
        try {
            const config = {
                num_slots: parseInt(numSlots, 10),
                save: true
            };
            if (questionsPerSlot) {
                config.questions_per_slot = parseInt(questionsPerSlot, 10);
            }
            
            await intelligenceService.generateSlots(examId, config);
            await fetchSlots();
            alert(" Exam slots generated successfully!");
        } catch (error) {
            console.error("Failed to generate slots:", error);
            alert(" Failed to generate exam slots.");
        }
        setGenerating(false);
    };

    if (loading) return <LoadingState message="Loading exam slots..." />;

    return (
        <div className="mb-5">
            <SectionHeader 
                title="Exam Slots (Multi-Set Generation)" 
                subtitle="Automatically generate balanced, non-overlapping question sets from your bank."
            />

            <div className="row align-items-end p-4 rounded mb-4 shadow-sm border" style={{ background: 'var(--surface-secondary)' }}>
                <div className="col-md-4 mb-2 mb-md-0">
                    <label className="form-label fw-bold small text-muted">Number of Slots (Sets)</label>
                    <input 
                        type="number" 
                        className="form-control" 
                        min="2" 
                        max="10" 
                        value={numSlots} 
                        onChange={(e) => setNumSlots(e.target.value)} 
                    />
                </div>
                <div className="col-md-4 mb-2 mb-md-0">
                    <label className="form-label fw-bold small text-muted">Questions per Slot (Optional)</label>
                    <input 
                        type="number" 
                        className="form-control" 
                        min="1" 
                        placeholder="Auto-calculate" 
                        value={questionsPerSlot} 
                        onChange={(e) => setQuestionsPerSlot(e.target.value)} 
                    />
                </div>
                <div className="col-md-4">
                    <button 
                        className="btn btn-primary w-100 fw-bold py-2" 
                        onClick={handleGenerate}
                        disabled={generating}
                    >
                        {generating ? 'Generating...' : '⚡ Generate Slots'}
                    </button>
                </div>
            </div>

            {slots.length > 0 ? (
                <div className="row g-3">
                    {slots.map((slot, index) => (
                        <div key={slot.id} className="col-md-6">
                            <div className="card h-100 shadow-sm border-0" style={{ background: 'var(--surface)' }}>
                                <div className="card-header bg-primary text-white fw-bold border-0" style={{ borderRadius: '12px 12px 0 0' }}>
                                    Slot {slot.slot_number}
                                </div>
                                <div className="card-body">
                                    <div className="d-flex justify-content-between mb-3">
                                        <div>
                                            <small className="text-muted d-block">Questions</small>
                                            <span className="fw-bold fs-5">{slot.question_count}</span>
                                        </div>
                                        <div>
                                            <small className="text-muted d-block">Total Marks</small>
                                            <span className="fw-bold fs-5">{slot.total_marks}</span>
                                        </div>
                                        <div className="text-end">
                                            <small className="text-muted d-block">Quality Match</small>
                                            <span className="badge badge-success">
                                                {Math.round(slot.blueprint_match_score * 100)}%
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <div className="card-footer text-center" style={{ background: 'var(--surface-secondary)', borderTop: '1px solid var(--border)' }}>
                                    <small className="text-muted">ID: {slot.id}</small>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <p className="text-muted text-center my-4">No slots generated yet.</p>
            )}
        </div>
    );
};

export default SlotGenerator;
