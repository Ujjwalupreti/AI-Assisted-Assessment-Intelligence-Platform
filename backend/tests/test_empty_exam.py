import requests

base_url = 'http://127.0.0.1:5000/api'

def run_test():
    # Login as teacher
    r = requests.post(f"{base_url}/auth/login", json={'username': 'phase2_teacher', 'password': 'password123'})
    teacher_token = r.json().get('token')
    teacher_headers = {'Authorization': f'Bearer {teacher_token}'}
    
    # Create empty exam
    r = requests.post(f"{base_url}/exams", json={
        'title': 'Empty Test Exam',
        'duration': 60
    }, headers=teacher_headers)
    exam_id = r.json()['exam_id']
    print(f"Created empty exam {exam_id}")
    
    # Fetch as teacher (should see it)
    r = requests.get(f"{base_url}/exams", headers=teacher_headers)
    exams = r.json()
    print(f"Teacher sees {len(exams)} exams.")
    
    # Login as student
    r = requests.post(f"{base_url}/auth/login", json={'username': 'student2', 'password': 'password123'})
    student_token = r.json().get('token')
    student_headers = {'Authorization': f'Bearer {student_token}'}
    
    # Fetch as student (should NOT see the empty one)
    r = requests.get(f"{base_url}/exams", headers=student_headers)
    student_exams = r.json()
    print(f"Student sees {len(student_exams)} exams.")
    
    for e in student_exams:
        if e['id'] == exam_id:
            print("FAIL: Student saw the empty exam!")
            return
            
    print("PASS: Student cannot see the empty exam.")

if __name__ == "__main__":
    run_test()
