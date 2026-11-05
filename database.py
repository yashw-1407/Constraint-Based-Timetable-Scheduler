import json
import os
import threading
from models import WorkingConfig, Room, Faculty, Section, Batch, Course, AcademicTerm, Department

DB_FILE = 'database.json'
_lock = threading.Lock()

DEFAULT_TERMS = [
    AcademicTerm(id='term_2026_fall', name='Fall 2026-27 (Term 1)', academic_year='2026-27', semester_type='ODD', is_active=True),
    AcademicTerm(id='term_2026_spring', name='Spring 2026-27 (Term 2)', academic_year='2026-27', semester_type='EVEN', is_active=False)
]

DEFAULT_DEPARTMENTS = [
    Department(id='dept_cse', name='Computer Science & Engineering', code='CSE'),
    Department(id='dept_ece', name='Electronics & Communication', code='ECE')
]

def _dataclass_to_dict(obj):
    return obj.to_dict()

def save_data(app_data):
    """Transactional save to JSON file."""
    with _lock:
        data = {
            'config': app_data['config'].to_dict() if app_data['config'] else None,
            'rooms': [r.to_dict() for r in app_data['rooms']],
            'faculty': [f.to_dict() for f in app_data['faculty']],
            'sections': [s.to_dict() for s in app_data['sections']],
            'batches': [b.to_dict() for b in app_data['batches']],
            'courses': [c.to_dict() for c in app_data['courses']],
            'publishing': app_data.get('publishing'),
            'terms': [t.to_dict() for t in app_data.get('terms', [])],
            'departments': [d.to_dict() for d in app_data.get('departments', [])],
            'active_term_id': app_data.get('active_term_id', 'term_2026_fall'),
        }
        temp_file = DB_FILE + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(temp_file, DB_FILE)

def load_data(app_data):
    """Load from JSON file into app_data."""
    with _lock:
        if not os.path.exists(DB_FILE):
            app_data.setdefault('terms', [t for t in DEFAULT_TERMS])
            app_data.setdefault('departments', [d for d in DEFAULT_DEPARTMENTS])
            app_data.setdefault('active_term_id', 'term_2026_fall')
            return
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('config'):
                app_data['config'] = WorkingConfig.from_dict(data['config'])
            app_data['rooms'] = [Room.from_dict(d) for d in data.get('rooms', [])]
            app_data['faculty'] = [Faculty.from_dict(d) for d in data.get('faculty', [])]
            app_data['sections'] = [Section.from_dict(d) for d in data.get('sections', [])]
            app_data['batches'] = [Batch.from_dict(d) for d in data.get('batches', [])]
            app_data['courses'] = [Course.from_dict(d) for d in data.get('courses', [])]
            app_data['publishing'] = data.get('publishing')

            loaded_terms = [AcademicTerm.from_dict(d) for d in data.get('terms', [])]
            app_data['terms'] = loaded_terms if loaded_terms else [t for t in DEFAULT_TERMS]

            loaded_depts = [Department.from_dict(d) for d in data.get('departments', [])]
            app_data['departments'] = loaded_depts if loaded_depts else [d for d in DEFAULT_DEPARTMENTS]

            app_data['active_term_id'] = data.get('active_term_id', 'term_2026_fall')
        except Exception as e:
            print(f"Error loading database: {e}")
