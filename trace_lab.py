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
for s in engine.sessions:
    if '26EMAB229' in s.course_code and s.course_type == 'LAB':
        print(f"{s.id}: type={s.course_type}, room_type={s.room_type}, req={s.required_room_id}")
        print(f"Suitable rooms: {[r.id for r in engine._get_suitable_rooms(s)]}")
