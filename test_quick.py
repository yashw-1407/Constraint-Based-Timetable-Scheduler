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
    batches = [Batch(**b) for b in db['batches']]
courses = [Course(**c) for c in db['courses']]

print("Total courses:", len(courses))
print("Total rooms:", len(rooms))

engine = SchedulingEngine(config, courses, rooms, faculty, sections, batches)
print("Sessions to schedule:", len(engine.sessions))

res = engine.solve()
if res['status'] == 'success':
    print("Solve successful!")
    print("Soft score:", res.get('soft_score', {}).get('percentage', 0))
else:
    print("Solve failed!")
    print("Diagnostics:")
    print(res.get('diagnostics', 'No diagnostics'))
