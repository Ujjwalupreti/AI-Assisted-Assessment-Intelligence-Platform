import requests
import json
import base64
from datetime import datetime, timedelta

base_url = 'http://127.0.0.1:5000/api'

def run_test():
    print("1. Login as Admin...")
    r = requests.post(f"{base_url}/auth/login", json={'username': 'admin', 'password': 'adminpass'})
    if r.status_code != 200:
        print("Admin login failed:", r.text)
        return
    admin_token = r.json().get('token')
    admin_headers = {'Authorization': f'Bearer {admin_token}'}
    print("Admin Token acquired")

    print("2. Create a Teacher...")
    r = requests.post(f"{base_url}/admin/users", json={
        'username': 'teacher1',
        'password': 'password123',
        'role': 'teacher'
    }, headers=admin_headers)
    
    print("3. Login as Teacher...")
    r = requests.post(f"{base_url}/auth/login", json={'username': 'teacher1', 'password': 'password123'})
    teacher_token = r.json().get('token')
    teacher_headers = {'Authorization': f'Bearer {teacher_token}'}
    print("Teacher Token acquired")

    print("4. Create an Exam...")
    start_dt = datetime.now()
    end_dt = start_dt + timedelta(hours=2)
    r = requests.post(f"{base_url}/exams", json={
        'title': 'Test Exam 1',
        'duration': 60,
        'start_date': start_dt.isoformat(),
        'end_date': end_dt.isoformat(),
        'password': ''
    }, headers=teacher_headers)
    
    if r.status_code != 201:
        print("Exam creation failed:", r.text)
        return
    exam_id = r.json()['exam_id']
    print("Exam created with ID:", exam_id)

    print("5. Create a Student...")
    r = requests.post(f"{base_url}/admin/users", json={
        'username': 'student2',
        'password': 'password123',
        'role': 'student',
        'enrollment_id': 'STU002'
    }, headers=admin_headers)
    
    print("6. Login as Student...")
    r = requests.post(f"{base_url}/auth/login", json={'username': 'student2', 'password': 'password123'})
    student_token = r.json().get('token')
    student_headers = {'Authorization': f'Bearer {student_token}'}
    print("Student Token acquired")
    
    print("7. Add Question as Teacher...")
    # I need to use the question routes to add a question
    # wait, the question routes are in question_routes.py
    r = requests.post(f"{base_url}/exams/{exam_id}/questions", json={
        'text': 'What is 2+2?',
        'option_a': '3',
        'option_b': '4',
        'option_c': '5',
        'option_d': '6',
        'correct_option_hash': 'testhash123'
    }, headers=teacher_headers)
    if r.status_code != 201:
        print("Add question failed:", r.text)
        # We will continue anyway

    print("8. Start Exam as Student...")
    r = requests.post(f"{base_url}/exams/{exam_id}/start", headers=student_headers)
    if r.status_code != 201:
        print("Failed to start exam:", r.text)

    print("9. Fetch questions as Student...")
    r = requests.get(f"{base_url}/exams/{exam_id}/questions", headers=student_headers)
    if r.status_code != 200:
        print("Failed to fetch questions:", r.text)
    else:
        questions = r.json()
        print(f"Fetched {len(questions)} questions")
        
    print("10. Submit Exam as Student...")
    dummy_img = "data:image/jpeg;base64," + base64.b64encode(b"dummy image data").decode('utf-8')
    r = requests.post(f"{base_url}/exams/{exam_id}/submit", json={
        'answers': {},
        'tab_switches': 1,
        'audio_warnings': 2,
        'id_image': dummy_img,
        'face_image': dummy_img,
        'mid_exam_photo': dummy_img
    }, headers=student_headers)
    
    print("Submit response status:", r.status_code)
    print("Submit response:", r.text)
    
    if r.status_code == 200:
        print("Submit successful!")
    
    print("11. Fetch Results as Teacher...")
    r = requests.get(f"{base_url}/exams/{exam_id}/results", headers=teacher_headers)
    print("Results response:", r.status_code)
    
    print("12. Delete Exam as Teacher...")
    r = requests.delete(f"{base_url}/exams/{exam_id}", headers=teacher_headers)
    print("Delete response:", r.status_code)

if __name__ == "__main__":
    run_test()
