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

engine = SchedulingEngine(config, courses, rooms, faculty, sections, batches)
print(engine._diagnose())
