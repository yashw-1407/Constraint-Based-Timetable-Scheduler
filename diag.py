import json
from models import WorkingConfig, Room, Faculty, Section, Course, Batch
from scheduler import SchedulingEngine

with open('database.json', 'r') as f:
    app_data = json.load(f)

config = WorkingConfig.from_dict(app_data['config'])
rooms = [Room.from_dict(d) for d in app_data.get('rooms', [])]
faculty = [Faculty.from_dict(d) for d in app_data.get('faculty', [])]
sections = [Section.from_dict(d) for d in app_data.get('sections', [])]
batches = [Batch.from_dict(d) for d in app_data.get('batches', [])]
courses = [Course.from_dict(d) for d in app_data.get('courses', [])]

engine = SchedulingEngine(config, courses, rooms, faculty, sections, batches)

def check_domain(s_id_prefix):
    for s in engine.sessions:
        if s.course_id == s_id_prefix:
            c = engine.courses_by_id[s.course_id]
            req_room = engine.rooms_by_id.get(s.required_room_id)
            strength = engine._get_scheduling_strength(s)
            
            suitable_rooms = engine._get_suitable_rooms(s)
            domain = engine._get_domain(s)
            time_pos = len(set((d, t) for d, t, r in domain))
            
            print(f'{s.id}:')
            print(f'course_type = {s.course_type}')
            print(f'required_room = {s.required_room_id}')
            print(f'room_capacity = {req_room.capacity if req_room else "None"}')
            print(f'strength = {strength}')
            print(f'duration_slots = {s.duration_slots}')
            print(f'candidate_room_count = {len(suitable_rooms)} ({[r.id for r in suitable_rooms]})')
            print(f'candidate_time_positions = {time_pos}')
            print(f'final_domain_count = {len(domain)}')
            print('-'*40)

check_domain('C5A06')
check_domain('C5A08')
check_domain('C5B06')
check_domain('C5B08')
