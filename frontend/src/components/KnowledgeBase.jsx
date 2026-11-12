import React, { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import { BrainCircuit } from 'lucide-react';

const KnowledgeBase = () => {
  const { API_BASE_URL, getHeaders } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [formData, setFormData] = useState({ title: '', course_name: '', content_text: '' });
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');

  const fetchDocuments = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/rag/documents`, { headers: getHeaders() });
      if (res.ok) {
        setDocuments(await res.json());
      }
    } catch (e) { console.error(e); }
  };

  useEffect(() => { fetchDocuments(); }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMsg('Processing document... This might take a moment to generate embeddings.');
    try {
      const res = await fetch(`${API_BASE_URL}/rag/documents`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        setMsg(' Document processed and added to Knowledge Base.');
        setFormData({ title: '', course_name: '', content_text: '' });
        fetchDocuments();
      } else {
        const err = await res.json();
        setMsg(` Error: ${err.message}`);
      }
    } catch (e) {
      console.error(e);
      setMsg(' Failed to upload document.');
    }
    setLoading(false);
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this document and its embeddings?")) return;
    try {
      const res = await fetch(`${API_BASE_URL}/rag/documents/${id}`, {
        method: 'DELETE',
        headers: getHeaders()
      });
      if (res.ok) {
        fetchDocuments();
      }
    } catch (e) { console.error(e); }
  };

  return (
    <div className="card shadow-sm border-0 my-4">
      <div className="card-header d-flex justify-content-between align-items-center">
        <h5 className="m-0 d-flex align-items-center gap-2"><BrainCircuit size={20} className="text-primary" /> Institutional Knowledge Base (RAG)</h5>
      </div>
      <div className="card-body">
        <div className="alert alert-info py-2 small">
          <strong>Contextual Grounding:</strong> Upload course syllabus, lecture notes, or institutional documents here. 
          The AI will use these documents as context when generating candidate questions to ensure they are perfectly aligned with your curriculum.
        </div>
        
        <div className="row">
          <div className="col-md-7 border-end">
            <h6 className="fw-bold mb-3">Upload New Document</h6>
            {msg && <div className={`alert py-2 small ${msg.includes('Error') ? 'alert-danger' : (msg.includes('Processing') ? 'alert-warning' : 'alert-success')}`}>{msg}</div>}
            
            <form onSubmit={handleSubmit}>
              <div className="row g-2 mb-2">
                <div className="col-6">
                  <input type="text" className="form-control form-control-sm" placeholder="Document Title (e.g. CS101 Syllabus)" required 
                    value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} />
                </div>
                <div className="col-6">
                  <input type="text" className="form-control form-control-sm" placeholder="Course Name (Optional)" 
                    value={formData.course_name} onChange={e => setFormData({...formData, course_name: e.target.value})} />
                </div>
              </div>
              <div className="mb-2">
                <textarea className="form-control" rows="8" placeholder="Paste document content, lecture notes, or syllabus text here..." required
                  value={formData.content_text} onChange={e => setFormData({...formData, content_text: e.target.value})}></textarea>
              </div>
              <button type="submit" className="btn btn-primary btn-sm fw-bold px-4" disabled={loading}>
                {loading ? 'Processing Embeddings...' : 'Add to Knowledge Base'}
              </button>
            </form>
          </div>
          
          <div className="col-md-5">
            <h6 className="fw-bold mb-3">Available Documents ({documents.length})</h6>
            {documents.length === 0 ? (
              <p className="text-muted small">No documents in the knowledge base yet.</p>
            ) : (
              <div className="list-group">
                {documents.map(doc => (
                  <div key={doc.id} className="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <div>
                      <div className="fw-bold small">{doc.title}</div>
                      <div className="text-muted" style={{fontSize: '0.75rem'}}>{doc.course_name || 'General'} • {new Date(doc.created_at).toLocaleDateString()}</div>
                    </div>
                    <button className="btn btn-sm btn-outline-danger py-0 px-2" onClick={() => handleDelete(doc.id)}>×</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default KnowledgeBase;
