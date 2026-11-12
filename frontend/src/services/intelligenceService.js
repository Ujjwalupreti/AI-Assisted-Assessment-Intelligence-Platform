// frontend/src/services/intelligenceService.js
import { apiFetch } from './api';

export const intelligenceService = {
    getReport: (examId) => apiFetch(`/intelligence/${examId}/intelligence-report`),
    
    analyzeAll: (examId) => apiFetch(`/intelligence/${examId}/analyze-all`, {
        method: 'POST'
    }),
    
    generateGapQuestions: (examId, criteria) => apiFetch(`/intelligence/${examId}/generate-gap-questions`, {
        method: 'POST',
        body: JSON.stringify(criteria)
    }),

    // --- Phase 5 Additions ---
    
    // Background Jobs
    getJobStatus: (jobId) => apiFetch(`/ai/questions/jobs/${jobId}`),
    
    // Recommendation Engine
    getRecommendations: (examId) => apiFetch(`/ai/questions/exam/${examId}/recommendations`),
    
    // Slot Generation
    generateSlots: (examId, config) => apiFetch(`/intelligence/${examId}/generate-slots`, {
        method: 'POST',
        body: JSON.stringify(config)
    }),
    getSlots: (examId) => apiFetch(`/intelligence/${examId}/slots`),
    
    // Duplicates Analysis
    runDeduplication: (examId) => apiFetch(`/ai/questions/deduplicate`, {
        method: 'POST',
        body: JSON.stringify({exam_id: examId})
    }),
    getDuplicates: (examId) => apiFetch(`/ai/questions/duplicates?exam_id=${examId}`),
    reviewDuplicate: (groupId, decisionData) => apiFetch(`/ai/questions/duplicates/${groupId}/review`, {
        method: 'POST',
        body: JSON.stringify(decisionData)
    })
};
