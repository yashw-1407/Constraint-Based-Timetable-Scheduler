import json
from scheduler import SchedulingEngine
from models import WorkingConfig, Room, Faculty, Section, Course, Batch

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

print("==================================================")
print("SECTIONS")
print("==================================================")
for s in sections:
    print(f"{s.id} home_room_id = {s.home_room_id}")

engine = SchedulingEngine(config, courses, rooms, faculty, sections, batches)

print("\n==================================================")
print("DIRECT TESTS")
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
            if not any(r.id in ['R003', 'R004', 'R005', 'R006', 'R007'] for r in suitable):
                print("  -> PASS (Valid LAB rooms only)")
            else:
                print("  -> FAIL (Used non-lab room)")
    except StopIteration:
        print(f"TEST: {desc} -> Session not found")

test_session_rooms('C3A01', '3A theory', 'THEORY', 'R005')
test_session_rooms('C3B01', '3B theory', 'THEORY', 'R006')
test_session_rooms('C5A01', '5A theory', 'THEORY', 'R003')
test_session_rooms('C5B01', '5B theory', 'THEORY', 'R004')

print("\nNormal LAB:")
test_session_rooms('C3A06', '3A lab', 'LAB', None)

print("\nMini Project:")
test_session_rooms('C5A06', '5A Mini Project', 'LAB', 'R007')

print("\nAI-Assisted Software Development:")
test_session_rooms('C5A08', '5A AI-Assisted', 'THEORY', 'R007')

print("\n==================================================")
print("TEST SOLVE")
print("==================================================")
res = engine.solve_multiple(requested_count=1)
if res['status'] == 'success':
    print("Solve successful!")
else:
    print("Solve failed!")
    print(res.get('diagnostics', ''))
