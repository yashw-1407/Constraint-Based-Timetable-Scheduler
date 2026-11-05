import json
from models import WorkingConfig, Room, Faculty, Section, Course
from scheduler import SchedulingEngine

with open('database.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

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

def test_session_rooms(sess_id, desc, expected_type, expected_room=None):
    try:
        s = next(s for s in engine.sessions if sess_id in s.id and s.course_type == expected_type)
        if expected_room and expected_type == 'THEORY' and 'project' not in desc.lower():
            s.required_room_id = ''
        if expected_type == 'LAB' and expected_room is None:
            s.required_room_id = ''
            
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

test_session_rooms('C5A06', '5A FIXED (Mini Project)', 'LAB', 'R007')
