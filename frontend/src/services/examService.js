// frontend/src/services/examService.js
import { apiFetch } from './api';

export const examService = {
    getAllExams: () => apiFetch('/exams'),
    
    getExamDetails: (examId) => apiFetch(`/exams/${examId}/details`),
    
    createExam: (examData) => apiFetch('/exams', {
        method: 'POST',
        body: JSON.stringify(examData)
    }),
    
    deleteExam: (examId) => apiFetch(`/exams/${examId}`, {
        method: 'DELETE'
    }),
    
    togglePublish: (examId) => apiFetch(`/exams/${examId}/toggle_publish`, {
        method: 'POST'
    }),

    getExamResults: (examId) => apiFetch(`/exams/${examId}/results`),
    
    deleteResult: (resultId) => apiFetch(`/exams/results/${resultId}`, {
        method: 'DELETE'
    }),
    
    previewAssembly: (payload) => apiFetch('/intelligence/assemble', {
        method: 'POST',
        body: JSON.stringify(payload)
    })
};
