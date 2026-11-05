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
result = engine.solve_multiple(requested_count=5, base_seed=1000, max_attempts=50, min_diversity_pct=25.0)

for i, alt in enumerate(result['alternatives']):
    print(f"Alternative {i+1}: feasible, score={alt['soft_score']['total_score']}, diversity={alt['diversity_pct']}%, changed={alt['changed_assignments']}, Signature={alt['signature']}")
