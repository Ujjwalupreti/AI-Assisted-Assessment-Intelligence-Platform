// frontend/src/services/proctoringService.js
import { apiFetch } from './api';

export const proctoringService = {
    getProctorLogs: (examId, studentId) => apiFetch(`/exams/${examId}/review/${studentId}`),
    getSelfReview: (examId) => apiFetch(`/exams/${examId}/review`),
    processFrame: (data) => apiFetch('/proctoring/process-frame', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    }),
    logViolation: (data) => apiFetch('/proctoring/log-violation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    }),
};
