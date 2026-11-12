// frontend/src/services/studentService.js
// Stub for Phase 6
import { apiFetch } from './api';

export const studentService = {
    getStudents: () => apiFetch('/students/list'),
    addStudent: (studentData) => apiFetch('/students/bulk_add', {
        method: 'POST',
        body: JSON.stringify({ students: [studentData] })
    }),
    bulkAddStudents: (students) => apiFetch('/students/bulk_add', {
        method: 'POST',
        body: JSON.stringify({ students })
    }),
    deleteStudent: (studentId) => apiFetch(`/students/${studentId}`, {
        method: 'DELETE'
    })
};
