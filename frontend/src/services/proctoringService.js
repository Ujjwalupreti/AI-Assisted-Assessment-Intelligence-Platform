// frontend/src/services/proctoringService.js
// Stub for Phase 5
import { apiFetch } from './api';

export const proctoringService = {
    // Expected endpoints
    getProctorLogs: (examId, studentId) => apiFetch(`/proctoring/exam/${examId}/student/${studentId}`),
};
