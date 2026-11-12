// frontend/src/services/questionService.js
import { apiFetch } from './api';

export const questionService = {
    getQuestions: (examId) => apiFetch(`/exams/${examId}/questions`),
    
    addQuestion: (examId, questionData) => apiFetch(`/exams/${examId}/questions`, {
        method: 'POST',
        body: JSON.stringify(questionData)
    }),
    
    updateQuestion: (questionId, questionData) => apiFetch(`/exams/question/${questionId}`, {
        method: 'PUT',
        body: JSON.stringify(questionData)
    }),
    
    deleteQuestion: (questionId) => apiFetch(`/exams/question/${questionId}`, {
        method: 'DELETE'
    }),
    
    analyzeQuestion: (examId, textData) => apiFetch(`/exams/${examId}/questions/analyze`, {
        method: 'POST',
        body: JSON.stringify(textData)
    }),
    
    bulkUpload: (examId, formData) => {
        // We do NOT JSON.stringify FormData, and we don't set Content-Type header manually 
        // so browser boundary is preserved. apiFetch handles this.
        return apiFetch(`/exams/${examId}/bulk_questions`, {
            method: 'POST',
            body: formData
        });
    }
};
