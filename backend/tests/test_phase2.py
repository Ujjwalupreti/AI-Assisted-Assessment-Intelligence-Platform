import requests
import json
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
        'username': 'phase2_teacher',
        'password': 'password123',
        'role': 'teacher'
    }, headers=admin_headers)
    
    print("3. Login as Teacher...")
    r = requests.post(f"{base_url}/auth/login", json={'username': 'phase2_teacher', 'password': 'password123'})
    teacher_token = r.json().get('token')
    teacher_headers = {'Authorization': f'Bearer {teacher_token}'}
    print("Teacher Token acquired")

    print("4. Create an Exam...")
    start_dt = datetime.now()
    end_dt = start_dt + timedelta(hours=2)
    r = requests.post(f"{base_url}/exams", json={
        'title': 'Phase 2 Exam',
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

    print("5. Test AI Analyze Endpoint...")
    question_text = "Explain how a binary search algorithm works and analyze its time complexity."
    r = requests.post(f"{base_url}/exams/{exam_id}/questions/analyze", json={
        'text': question_text
    }, headers=teacher_headers)
    
    print("Analyze response status:", r.status_code)
    
    if r.status_code == 200:
        ai_data = r.json()
        print("AI Metadata received:")
        print(json.dumps(ai_data, indent=2))
    else:
        print("Analyze failed:", r.text)
        return

    print("6. Test Adding Question with AI Metadata...")
    r = requests.post(f"{base_url}/exams/{exam_id}/questions", json={
        'text': question_text,
        'option_a': '',
        'option_b': '',
        'option_c': '',
        'option_d': '',
        'correct_option_hash': 'testhash123',
        'topic': ai_data['topic'],
        'difficulty': ai_data['difficulty'],
        'bloom_level': ai_data['bloom_level'],
        'ai_quality_score': ai_data['ai_quality_score'],
        'is_subjective': ai_data['is_subjective']
    }, headers=teacher_headers)
    
    if r.status_code != 201:
        print("Add question failed:", r.text)
        return
    print("Add Question Status:", r.status_code)

    print("7. Fetch questions to verify metadata...")
    r = requests.get(f"{base_url}/exams/{exam_id}/questions", headers=teacher_headers)
    if r.status_code != 200:
        print("Failed to fetch questions:", r.text)
    else:
        questions = r.json()
        print(f"Fetched {len(questions)} questions")
        q = questions[0]
        print("Question Metadata from DB:")
        print(f"Topic: {q.get('topic')}")
        print(f"Difficulty: {q.get('difficulty')}")
        print(f"Bloom Level: {q.get('bloom_level')}")
        print(f"Is Subjective: {q.get('is_subjective')}")
        print(f"AI Quality: {q.get('ai_quality_score')}")

    print("8. Test AI Analyze for Duplicates...")
    r = requests.post(f"{base_url}/exams/{exam_id}/questions/analyze", json={
        'text': question_text # sending the exact same text again
    }, headers=teacher_headers)
    
    if r.status_code == 200:
        ai_data_dup = r.json()
        print(f"Duplicate Score: {ai_data_dup['duplicate_score']} (Expected > 0.9)")
    
    print("Phase 2 Testing Complete.")

if __name__ == "__main__":
    run_test()
