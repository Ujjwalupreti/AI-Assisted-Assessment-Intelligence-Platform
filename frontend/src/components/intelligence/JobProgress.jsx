import React, { useState, useEffect } from 'react';
import { intelligenceService } from '../../services/intelligenceService';
import { AlertTriangle } from 'lucide-react';


const JobProgress = ({ jobId, onComplete, onFail }) => {
    const [status, setStatus] = useState('QUEUED');
    const [progress, setProgress] = useState(0);
    const [details, setDetails] = useState(null);

    useEffect(() => {
        if (!jobId) return;

        const pollInterval = setInterval(async () => {
            try {
                const data = await intelligenceService.getJobStatus(jobId);
                setStatus(data.status);
                setDetails(data);

                if (data.total > 0) {
                    setProgress(Math.round((data.processed / data.total) * 100));
                }

                if (data.status === 'COMPLETED' || data.status === 'FAILED') {
                    clearInterval(pollInterval);
                    if (data.status === 'COMPLETED') {
                        onComplete && onComplete();
                    } else {
                        onFail && onFail(data.failed_question_ids);
                    }
                }
            } catch (error) {
                console.error("Error polling job status:", error);
            }
        }, 3000);

        return () => clearInterval(pollInterval);
    }, [jobId]);

    const getStatusText = () => {
        if (status === 'QUEUED') return 'Job is queued...';
        if (status === 'PROCESSING') return `Analyzing questions... (${details?.processed}/${details?.total})`;
        if (status === 'COMPLETED') return 'Analysis complete!';
        if (status === 'FAILED') return 'Analysis failed.';
        return 'Status unknown';
    };

    return (
        <div className="card shadow-sm border-0 mb-4">
            <div className="card-body p-4 text-center">
                <h5 className="fw-bold mb-3">AI Analysis in Progress</h5>
                <p className="text-muted mb-3">{getStatusText()}</p>
                <div className="progress mb-2" style={{ height: '20px', borderRadius: '10px' }}>
                    <div 
                        className={`progress-bar progress-bar-striped progress-bar-animated ${status === 'FAILED' ? 'bg-danger' : status === 'COMPLETED' ? 'bg-success' : 'bg-primary'}`} 
                        role="progressbar" 
                        style={{ width: `${progress}%` }} 
                        aria-valuenow={progress} 
                        aria-valuemin="0" 
                        aria-valuemax="100"
                    >
                        {progress}%
                    </div>
                </div>
                {details && details.failed > 0 && (
                    <small className="text-danger fw-bold">
                        <AlertTriangle size={18} className="me-2" /> {details.failed} question(s) failed during analysis.
                    </small>
                )}
            </div>
        </div>
    );
};

export default JobProgress;
