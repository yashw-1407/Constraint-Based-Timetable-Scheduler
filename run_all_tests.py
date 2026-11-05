import json
from models import WorkingConfig, Room, Faculty, Section, Course
from scheduler import SchedulingEngine

with open('database.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

config = WorkingConfig(**db['config'])
rooms = [Room(**r) for r in db['rooms']]
faculty = [Faculty(**f) for f in db['faculty']]
sections = [Section(**s) for s in db['sections']]
batches = []
if 'batches' in db:
    from models import Batch
    batches = [Batch(**b) for b in db['batches']]
courses = [Course(**c) for c in db['courses']]

engine = SchedulingEngine(config, courses, rooms, faculty, sections, batches)
print("Testing engine on database...")
res = engine.solve_multiple(requested_count=1)

if res.get('status') in ['success', 'partial']:
    print(f"SUCCESS: Generated {res['generated']} timetables.")
    alt = res['alternatives'][0]
    assigns = alt['assignments_data']
    
    def check_tests():
        # TEST 1-4: Theory sessions use home room (UNLESS they have required_room_id)
        theory_3A = [a for a in assigns if engine.sessions_by_id[a['session_id']].section_id == 'S3A' and engine.sessions_by_id[a['session_id']].course_type == 'THEORY' and not engine.sessions_by_id[a['session_id']].required_room_id]
        if not theory_3A: print("FAIL: No 3A theory sessions found")
        for a in theory_3A:
            if a['room_id'] != 'R005': return f"TEST FAIL: 3A theory in {a['room_id']} instead of R005"
            
        theory_3B = [a for a in assigns if engine.sessions_by_id[a['session_id']].section_id == 'S3B' and engine.sessions_by_id[a['session_id']].course_type == 'THEORY' and not engine.sessions_by_id[a['session_id']].required_room_id]
        for a in theory_3B:
            if a['room_id'] != 'R006': return f"TEST FAIL: 3B theory in {a['room_id']} instead of R006"
            
        theory_5A = [a for a in assigns if engine.sessions_by_id[a['session_id']].section_id == 'S5A' and engine.sessions_by_id[a['session_id']].course_type == 'THEORY' and not engine.sessions_by_id[a['session_id']].required_room_id]
        for a in theory_5A:
            if a['room_id'] != 'R003': return f"TEST FAIL: 5A theory in {a['room_id']} instead of R003"
            
        theory_5B = [a for a in assigns if engine.sessions_by_id[a['session_id']].section_id == 'S5B' and engine.sessions_by_id[a['session_id']].course_type == 'THEORY' and not engine.sessions_by_id[a['session_id']].required_room_id]
        for a in theory_5B:
            if a['room_id'] != 'R004': return f"TEST FAIL: 5B theory in {a['room_id']} instead of R004"
            
        print("TEST 1-4: PASS (All regular theory sessions correctly placed in section home rooms)")
        
        # TEST 5-6: Labs are not in theory rooms
        labs = [a for a in assigns if engine.sessions_by_id[a['session_id']].course_type == 'LAB']
        for a in labs:
            if a['room_id'] in ['R005', 'R006', 'R003', 'R004']:
                return f"TEST FAIL: Lab {engine.sessions_by_id[a['session_id']].course_code} placed in theory home room {a['room_id']}"
        print("TEST 5-6: PASS (Labs correctly avoid generic home room fallback)")
        
        # TEST 7: Mini project fixed room
        mini = [a for a in assigns if 'Mini Project' in engine.sessions_by_id[a['session_id']].course_name]
        for a in mini:
            if a['room_id'] != 'R007':
                return f"TEST FAIL: Mini Project in {a['room_id']} instead of R007"
        print("TEST 7: PASS (Mini project correctly placed in R007)")
        
        return "ALL TESTS PASSED"
        
    print(check_tests())
else:
    print(f"FAILED: {res.get('message')}")
    print(res.get('diagnostics'))
