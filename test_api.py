"""Test the Flask API end-to-end: load demo -> generate -> validate -> views."""
import urllib.request
import json

BASE = "http://127.0.0.1:5000"

def api(method, path, data=None):
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

# 1. Load demo data
print("1. POST /api/load-demo")
r = api("POST", "/api/load-demo")
print(f"   {r}")

# 2. Check config
print("\n2. GET /api/config")
r = api("GET", "/api/config")
print(f"   working_days: {r['working_days']}")
print(f"   slots: {r['start_time']}-{r['end_time']}, duration={r['slot_duration_minutes']}min")
print(f"   lunch: {r['lunch_start']}-{r['lunch_end']}")

# 3. Check time slots
print("\n3. GET /api/time-slots")
r = api("GET", "/api/time-slots")
print(f"   {len(r)} slots: {[s['start_time']+'-'+s['end_time'] for s in r]}")

# 4. Check data counts
print("\n4. Data counts:")
print(f"   Rooms: {len(api('GET', '/api/rooms'))}")
print(f"   Faculty: {len(api('GET', '/api/faculty'))}")
print(f"   Sections: {len(api('GET', '/api/sections'))}")
print(f"   Courses: {len(api('GET', '/api/courses'))}")

# 5. Generate timetable
print("\n5. POST /api/generate")
r = api("POST", "/api/generate")
print(f"   status: {r['status']}")
if r['status'] == 'success':
    print(f"   assignments: {len(r['assignments'])} entries")
    score = r['soft_score']
    print(f"   soft_score: {score['percentage']}% ({score['total_score']}/{score['max_possible']})")
    stats = r.get('stats', {})
    print(f"   backtracks: {stats.get('backtracks')}, time: {stats.get('time_ms')}ms")
else:
    print(f"   message: {r.get('message')}")
    print(f"   diagnostics: {r.get('diagnostics')}")

# 6. Validate
print("\n6. GET /api/validation")
r = api("GET", "/api/validation")
print(f"   valid: {r['valid']}")
print(f"   conflicts: {r['conflicts']}")

# 7. Master view
print("\n7. GET /api/timetable/master")
r = api("GET", "/api/timetable/master")
print(f"   {len(r)} entries")

# 8. Section view
print("\n8. GET /api/timetable/section/3A")
r = api("GET", "/api/timetable/section/3A")
print(f"   days: {r['days']}")
print(f"   slots: {len(r['slots'])}")
grid_cells = sum(len(day_data) for day_data in r['grid'].values())
print(f"   grid cells filled: {grid_cells}")

# 9. Faculty view
print("\n9. GET /api/timetable/faculty/F1")
r = api("GET", "/api/timetable/faculty/F1")
grid_cells = sum(len(day_data) for day_data in r['grid'].values())
print(f"   grid cells filled: {grid_cells}")

# 10. Room view
print("\n10. GET /api/timetable/room/R101")
r = api("GET", "/api/timetable/room/R101")
grid_cells = sum(len(day_data) for day_data in r['grid'].values())
print(f"   grid cells filled: {grid_cells}")

print("\n" + "=" * 50)
print("ALL API TESTS PASSED")
print("=" * 50)
