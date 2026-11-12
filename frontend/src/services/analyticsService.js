// frontend/src/services/analyticsService.js
// Stub for Phase 5
import { apiFetch } from './api';

export const analyticsService = {
    // Expected endpoints in future phases
    getExamAnalytics: (examId) => apiFetch(`/analytics/exam/${examId}`),
    getStudentAnalytics: (studentId) => apiFetch(`/analytics/student/${studentId}`)
};
