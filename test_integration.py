import requests
import json
import time

BASE_URL = 'http://localhost:5000'

def test():
    # 1. Clear database
    res = requests.post(f"{BASE_URL}/api/clear")
    assert res.json()['status'] == 'ok'
    print("Database cleared.")

    # 2. Upload template Excel
    with open('timetable_import_template.xlsx', 'rb') as f:
        res = requests.post(f"{BASE_URL}/api/import-excel", files={'file': f})
    assert res.status_code == 200
    print("Excel imported.")

    # 3. Check data
    res = requests.get(f"{BASE_URL}/api/courses")
    courses = res.json()
    assert len(courses) == 2, "Expected 2 courses from template"
    print("Courses verified.")

    # 4. Generate timetable
    # First we need to configure time slots for it to work
    requests.post(f"{BASE_URL}/api/config", json={
        'working_days': ['Monday', 'Tuesday'],
        'start_time': '09:00',
        'end_time': '16:00',
        'slot_duration_minutes': 60,
        'lunch_start': '13:00',
        'lunch_end': '14:00',
        'breaks': []
    })
    
    res = requests.post(f"{BASE_URL}/api/generate")
    data = res.json()
    assert data['status'] == 'success'
    print("Timetable generated.")
    
    print("All integration tests passed!")

if __name__ == '__main__':
    test()
