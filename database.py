import json
import os
import threading
import hashlib
from models import WorkingConfig, Room, Faculty, Section, Batch, Course, AcademicTerm, Department, User, UserRole

DB_FILE = 'database.json'
_lock = threading.Lock()

def hash_password(password: str, salt: str = None) -> tuple:
    if not salt:
        salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return dk.hex(), salt

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return dk.hex() == password_hash

def get_default_users():
    admin_h, admin_s = hash_password('admin123', 'seededsaltadmin1')
    coord_h, coord_s = hash_password('coord123', 'seededsaltcoord1')
    fac_h, fac_s = hash_password('faculty123', 'seededsaltfaculty1')
    return [
        User(id='user_admin', username='admin', password_hash=admin_h, salt=admin_s, role=UserRole.ADMIN, name='System Administrator'),
        User(id='user_coord', username='coordinator', password_hash=coord_h, salt=coord_s, role=UserRole.COORDINATOR, name='Academic Coordinator'),
        User(id='user_faculty', username='faculty', password_hash=fac_h, salt=fac_s, role=UserRole.FACULTY, name='Faculty Member')
    ]

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
            'config': app_data['config'].to_dict() if app_data.get('config') else None,
            'rooms': [r.to_dict() for r in app_data.get('rooms', [])],
            'faculty': [f.to_dict() for f in app_data.get('faculty', [])],
            'sections': [s.to_dict() for s in app_data.get('sections', [])],
            'batches': [b.to_dict() for b in app_data.get('batches', [])],
            'courses': [c.to_dict() for c in app_data.get('courses', [])],
            'publishing': app_data.get('publishing'),
            'result': app_data.get('result'),
            'terms': [t.to_dict() for t in app_data.get('terms', [])],
            'departments': [d.to_dict() for d in app_data.get('departments', [])],
            'active_term_id': app_data.get('active_term_id', 'term_2026_fall'),
            'users': [u.to_dict() for u in app_data.get('users', [])],
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
            app_data.setdefault('users', get_default_users())
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
            app_data['result'] = data.get('result')

            loaded_terms = [AcademicTerm.from_dict(d) for d in data.get('terms', [])]
            app_data['terms'] = loaded_terms if loaded_terms else [t for t in DEFAULT_TERMS]

            loaded_depts = [Department.from_dict(d) for d in data.get('departments', [])]
            app_data['departments'] = loaded_depts if loaded_depts else [d for d in DEFAULT_DEPARTMENTS]

            loaded_term_id = data.get('active_term_id', 'term_2026_fall')
            app_data['active_term_id'] = loaded_term_id if isinstance(loaded_term_id, str) and loaded_term_id else 'term_2026_fall'

            loaded_users = [User.from_dict(d) for d in data.get('users', [])]
            app_data['users'] = loaded_users if loaded_users else get_default_users()

            if app_data.get('result') and app_data.get('config') and app_data['result'].get('assignments_data'):
                try:
                    from scheduler import SchedulingEngine
                    eng = SchedulingEngine(
                        app_data['config'],
                        app_data['courses'],
                        app_data['rooms'],
                        app_data['faculty'],
                        app_data['sections'],
                        app_data['batches']
                    )
                    eng.load_assignments_data(app_data['result']['assignments_data'])
                    app_data['engine'] = eng
                except Exception as e:
                    print(f"Engine restore warning in load_data: {e}")
        except Exception as e:
            print(f"Error loading database: {e}")
