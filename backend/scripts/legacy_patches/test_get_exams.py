import sys
import jwt
import requests
import json
from datetime import datetime, timedelta

def test():
    # 1. create token
    token = jwt.encode(
        {'user_id': 1, 'role': 'teacher'},
        'my_precious_secret',
        algorithm="HS256"
    )
    print(f"Token: {token}")

    # 2. make request
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Send GET request with Content-Type but no body (like the frontend)
    res = requests.get("http://127.0.0.1:5000/api/exams", headers=headers)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}")

if __name__ == "__main__":
    test()
