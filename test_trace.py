import json
import time
from models import WorkingConfig, Room, Faculty, Section, Batch, Course
from scheduler import SchedulingEngine
from scheduler_trace import SchedulerTrace

# Load db
with open('database.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

config = WorkingConfig(**db['config'])
rooms = [Room(**r) for r in db['rooms']]
faculty = [Faculty(**f) for f in db['faculty']]
sections = [Section(**s) for s in db['sections']]
batches = [Batch(**b) for b in db.get('batches', [])]
courses = [Course(**c) for c in db['courses']]

# Test A: Trace OFF
print("TEST A: TRACE OFF")
engine_off = SchedulingEngine(config, courses, rooms, faculty, sections, batches)
res_off = engine_off.solve(seed=1234)
print(f"Status: {res_off['status']}")
print(f"Total sessions: {len(engine_off.sessions)}")
print(f"Backtracks: {engine_off.backtrack_count}")
print(f"Time: {res_off.get('stats',{}).get('time_ms')} ms")
print()

# Test B: Trace Level 2 ON
print("TEST B: TRACE LEVEL 2 ON")
trace = SchedulerTrace(level=2)
engine_on = SchedulingEngine(config, courses, rooms, faculty, sections, batches, trace=trace)
res_on = engine_on.solve(seed=1234)
trace.write()
print(f"Status: {res_on['status']}")
print(f"Total sessions: {len(engine_on.sessions)}")
print(f"Backtracks: {engine_on.backtrack_count}")
print(f"Time: {res_on.get('stats',{}).get('time_ms')} ms")
print()

# Compare actual scheduling result
def extract_assignments(engine):
    return sorted([f"{a.session_id}|{a.day}|{a.start_slot_index}|{a.room_id}" for a in engine.assignments.values()])

ass_off = extract_assignments(engine_off)
ass_on = extract_assignments(engine_on)

print(f"Are assignment decisions identical? {ass_off == ass_on}")
if ass_off != ass_on:
    print("WARNING: Trace changed the scheduling result!")
else:
    print("SUCCESS: Result is identical.")
