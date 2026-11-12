import React, { useState } from 'react';
import { useAuth } from '../AuthContext';
import { examService } from '../services/examService';
import AssessmentBlueprint from './assessment/AssessmentBlueprint';
import AssessmentModeSelector from './assessment/AssessmentModeSelector';
import AutomatedAssemblyPreview from './assessment/AutomatedAssemblyPreview';
import { PenTool } from 'lucide-react';


const CreateExamForm = ({ onSuccess }) => {
  const { API_BASE_URL, getHeaders } = useAuth();
  
  const [formData, setFormData] = useState({ 
      title: '', 
      duration: '', 
      start_date: '', 
      end_date: '', 
      password: '', //  Exam Password State
      creation_mode: 'manual',
      question_count: 10
  });
  
  const [mode, setMode] = useState('manual');
  const [previewData, setPreviewData] = useState(null);
  
  const [blueprint, setBlueprint] = useState({
      bloom_distribution: {},
      difficulty_distribution: {},
      topic_distribution: {}
  });
  
  // Prevent double-clicking while submitting
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    // Validate Blueprint
    const bloomTotal = Object.values(blueprint.bloom_distribution || {}).reduce((a, b) => a + b, 0);
    const difficultyTotal = Object.values(blueprint.difficulty_distribution || {}).reduce((a, b) => a + b, 0);
    const topicTotal = Object.values(blueprint.topic_distribution || {}).reduce((a, b) => a + b, 0);
    
    if (bloomTotal > 100 || difficultyTotal > 100 || topicTotal > 100) {
        alert(" Error: Distribution percentages cannot exceed 100%.");
        setLoading(false);
        return;
    }

    // Filter out 0s or empty topics
    const cleanBlueprint = mode === 'automated' ? {
        bloom_distribution: Object.fromEntries(Object.entries(blueprint.bloom_distribution).filter(([_, v]) => v > 0)),
        difficulty_distribution: Object.fromEntries(Object.entries(blueprint.difficulty_distribution).filter(([_, v]) => v > 0)),
        topic_distribution: Object.fromEntries(Object.entries(blueprint.topic_distribution).filter(([k, v]) => k.trim() !== '' && v > 0))
    } : null;

    if (mode === 'automated' && !previewData) {
        try {
            const payload = {
                topics: cleanBlueprint.topic_distribution,
                difficulty_distribution: cleanBlueprint.difficulty_distribution,
                question_count: parseInt(formData.question_count),
                exam_type: "Objective", // Assuming Objective for MVP
                bloom_distribution: cleanBlueprint.bloom_distribution
            };
            const res = await examService.previewAssembly(payload);
            setPreviewData(res);
        } catch (e) {
            console.error(e);
            alert(" Error: " + (e.message || "Failed to generate preview."));
        } finally {
            setLoading(false);
        }
        return; // Stop here, wait for user to confirm preview
    }

    try {
      const payload = { 
          ...formData, 
          creation_mode: mode,
          blueprint_json: cleanBlueprint ? JSON.stringify(cleanBlueprint) : null,
          selected_questions: previewData ? previewData.selected_questions.map(q => q.id) : []
      };
      
      const res = await examService.createExam(payload);
      
      if (res.message || res.id) {
        alert(" Exam Created Successfully!");
        setFormData({ title: '', duration: '', start_date: '', end_date: '', password: '', creation_mode: 'manual', question_count: 10 });
        setBlueprint({ bloom_distribution: {}, difficulty_distribution: {}, topic_distribution: {} });
        setPreviewData(null);
        onSuccess();
      } else {
        alert(" Error creating exam.");
      }
    } catch (e) { 
        console.error(e); 
        alert(" Error: " + (e.message || "Failed to connect to server."));
    } finally {
        setLoading(false);
    }
  };

  return (
    <div className="card shadow-sm border-0">
        <div className="card-header">
            <h4 className="card-title"><PenTool size={18} className="me-2" />️ Create New Exam</h4>
        </div>
        
        <div className="card-body">
            {previewData ? (
                <AutomatedAssemblyPreview 
                    previewData={previewData} 
                    onBack={() => setPreviewData(null)} 
                    onConfirm={handleSubmit} 
                />
            ) : (
            <form onSubmit={handleSubmit}>
                <div className="form-group mb-4">
                    <label>Exam Title</label>
                    <input type="text" required 
                        placeholder="e.g. Midterm Mathematics"
                        value={formData.title}
                        onChange={e => setFormData({...formData, title: e.target.value})} />
                </div>

                <div className="dashboard-grid mb-4">
                    <div className="form-group">
                        <label>Duration (mins)</label>
                        <input type="number" required min="1"
                            placeholder="60"
                            value={formData.duration}
                            onChange={e => setFormData({...formData, duration: e.target.value})} />
                    </div>
                    
                    {/*  PASSWORD FIELD */}
                    <div className="form-group">
                        <label> Exam Password (Optional)</label>
                        <input type="text" 
                            placeholder="Leave blank for open access"
                            value={formData.password}
                            onChange={e => setFormData({...formData, password: e.target.value})} />
                    </div>
                    
                    {mode === 'automated' && (
                        <div className="form-group">
                            <label> Total Questions</label>
                            <input type="number" required min="1"
                                value={formData.question_count}
                                onChange={e => setFormData({...formData, question_count: e.target.value})} />
                        </div>
                    )}
                </div>
                
                <div className="dashboard-grid mb-5">
                    <div className="form-group">
                        <label className="text-success"> Opens At</label>
                        <input type="datetime-local" required
                            value={formData.start_date}
                            onChange={e => setFormData({...formData, start_date: e.target.value})} />
                    </div>
                    <div className="form-group">
                        <label className="text-danger"> Closes At (Deadline)</label>
                        <input type="datetime-local" required
                            value={formData.end_date}
                            onChange={e => setFormData({...formData, end_date: e.target.value})} />
                    </div>
                </div>
                
                <hr className="my-4" />
                <AssessmentModeSelector mode={mode} setMode={setMode} />
                
                {mode === 'automated' && (
                    <AssessmentBlueprint blueprint={blueprint} setBlueprint={setBlueprint} />
                )}

                <div className="mt-5">
                    {(() => {
                        const tSum = Object.values(blueprint.topic_distribution || {}).reduce((a, b) => a + (b||0), 0);
                        const dSum = Object.values(blueprint.difficulty_distribution || {}).reduce((a, b) => a + (b||0), 0);
                        const isInvalid = mode === 'automated' && (tSum > 101 || dSum > 101);
                        return (
                            <button type="submit" disabled={loading || isInvalid} className="btn btn-primary" style={{ width: '100%', padding: '0.75rem' }}>
                                {loading ? 'Processing...' : (mode === 'automated' ? ' Preview Assessment' : ' Create Draft')}
                            </button>
                        );
                    })()}
                </div>
            </form>
            )}
        </div>
    </div>
  );
};

export default CreateExamForm;