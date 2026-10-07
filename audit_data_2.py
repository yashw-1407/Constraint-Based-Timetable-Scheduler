import json
from models import WorkingConfig, Room, Faculty, Section, Course
from scheduler import SchedulingEngine

with open('database.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

# Clear ALL required rooms just for the test engine so dedicated_room_ids is empty
for c in db['courses']:
    if 'Mini Project' not in c['name'] and 'AI-Assisted' not in c['name']:
        c['required_room_id'] = ''

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

print("==================================================")
print("DIRECT ROOM-DOMAIN TESTS")
print("==================================================")

def test_session_rooms(sess_id, desc, expected_type, expected_room=None):
    try:
        s = next(s for s in engine.sessions if sess_id in s.id and s.course_type == expected_type)
        suitable = engine._get_suitable_rooms(s)
        suitable_ids = [r.id for r in suitable]
        print(f"TEST: {desc}")
        print(f"  Result: {suitable_ids}")
        if expected_room:
            if suitable_ids == [expected_room]: print("  -> PASS")
            else: print(f"  -> FAIL (Expected [{expected_room}])")
        else:
            if not any(r.id in ['R003', 'R004', 'R005', 'R006', 'R007'] for r in suitable): # Check it doesn't use theory rooms
                print("  -> PASS (Valid LAB rooms only)")
            else:
                print("  -> FAIL (Used non-lab room)")
    except StopIteration:
        print(f"TEST: {desc} -> Session not found")

test_session_rooms('C3A01', '3A THEORY', 'THEORY', 'R005')
test_session_rooms('C3B01', '3B THEORY', 'THEORY', 'R006')
test_session_rooms('C5A01', '5A THEORY', 'THEORY', 'R003')
test_session_rooms('C5B01', '5B THEORY', 'THEORY', 'R004')
test_session_rooms('C3A06', '3A LAB', 'LAB', None)
test_session_rooms('C3B06', '3B LAB', 'LAB', None)
test_session_rooms('C5A06', '5A FIXED (Mini Project)', 'THEORY', 'R007')

print("\n==================================================")
print("L/T/P SESSION GENERATION BEHAVIOR")
print("==================================================")
ltp_course = next((c for c in courses if (c.l + c.t) > 0 and c.p > 0), None)
if ltp_course:
    print(f"Found course: {ltp_course.name} ({ltp_course.code})")
    print(f"  L={ltp_course.l}, T={ltp_course.t}, P={ltp_course.p}")
    print("  Generated sessions:")
    for s in engine.sessions:
        if s.course_id == ltp_course.id:
            print(f"    Session {s.id}: type={s.course_type}, room_type={s.room_type}, req_room={s.required_room_id}, dur={s.duration_slots} slots, batch={s.batch_id}")
