"""
app.py - Flask web application for the Timetable Scheduling Engine.

Serves the single-page frontend and provides a JSON API for:
  - CRUD operations on configuration, rooms, faculty, sections, batches, courses
  - Generating timetables via the SchedulingEngine (CSP backtracking)
  - Retrieving timetable views (master, section, faculty, room)
  - Post-generation validation and demo data loading

All data is stored in-memory (no database required for the MVP).
"""

from flask import Flask, jsonify, request, render_template, send_file, session, Response
import os
import io
import secrets
import hmac
from functools import wraps
from datetime import timedelta
from models import WorkingConfig, Room, Faculty, Section, Batch, Course, RoomType, CourseType, AcademicTerm, Department, User, UserRole
from time_slots import generate_time_slots, time_to_minutes
from scheduler_trace import SchedulerTrace
from scheduler import SchedulingEngine
from constraints import validate_timetable
from demo_data import get_demo_data
from database import (
    init_db, load_data, save_data, DEFAULT_TERMS, DEFAULT_DEPARTMENTS,
    verify_password, hash_password, get_default_users,
    get_schedule_versions, create_schedule_snapshot, restore_schedule_version,
    get_change_alerts, clear_change_alerts
)
from calendar_feed import generate_faculty_ical
import importer
import exporter
import adjuster

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'autoschedule-dev-secret-key-2026')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

# Initialize Relational Database & Migrations
init_db(app)

# ---------------------------------------------------------------------------
# Authentication & Role-Based Access Control Decorators
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user:
            return jsonify({'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_role(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = session.get('user')
            if not user:
                return jsonify({'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401
            role = user.get('role')
            if role not in allowed_roles:
                return jsonify({'error': 'Insufficient privileges', 'code': 'FORBIDDEN'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ---------------------------------------------------------------------------
# CSRF Protection Middleware
# ---------------------------------------------------------------------------
CSRF_EXEMPT_PATHS = {'/api/auth/login'}

@app.before_request
def csrf_protect():
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return
    if request.path in CSRF_EXEMPT_PATHS:
        return
    user = session.get('user')
    if user:
        token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
        expected = session.get('csrf_token')
        if not expected or not token or not hmac.compare_digest(token, expected):
            return jsonify({'error': 'CSRF token missing or invalid', 'code': 'CSRF_FAILED'}), 403

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File upload exceeds maximum allowed size (16MB)', 'code': 'FILE_TOO_LARGE'}), 413

# ---------------------------------------------------------------------------
# In-memory application state
# ---------------------------------------------------------------------------

# Trace config
trace_config = {
    'level': 0,
    'session_filter': None
}

app_data = {
    'config': None,          # WorkingConfig instance
    'rooms': [],             # List[Room]
    'faculty': [],           # List[Faculty]
    'sections': [],          # List[Section]
    'batches': [],           # List[Batch]
    'courses': [],           # List[Course]
    'terms': [],             # List[AcademicTerm]
    'departments': [],       # List[Department]
    'active_term_id': 'term_2026_fall',
    'users': [],             # List[User]
    'engine': None,          # SchedulingEngine (for view queries after generation)
    'result': None,          # dict from engine.solve()
}

# Load existing data on startup within app context
with app.app_context():
    load_data(app_data)

def _seed_initial_state_if_needed():
    if not app_data.get('config') or not app_data.get('courses') or not app_data.get('result'):
        try:
            demo = get_demo_data('standard')
            app_data['config'] = demo['config']
            app_data['rooms'] = demo['rooms']
            app_data['faculty'] = demo['faculty']
            app_data['sections'] = demo['sections']
            app_data['batches'] = demo.get('batches', [])
            app_data['courses'] = demo['courses']
            engine = SchedulingEngine(
                app_data['config'],
                app_data['courses'],
                app_data['rooms'],
                app_data['faculty'],
                app_data['sections'],
                app_data['batches']
            )
            res = engine.solve()
            app_data['engine'] = engine
            app_data['result'] = res
            app_data['publishing'] = {
                'status': 'PUBLISHED',
                'is_published': True,
                'published_at': 'Initial System Setup',
                'term': 'Fall 2026-27 (Term 1)'
            }
            save_data(app_data)
        except Exception as e:
            print(f"Startup seeding warning: {e}")

with app.app_context():
    _seed_initial_state_if_needed()


# ---------------------------------------------------------------------------
# Frontend route
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    """Serve the single-page application."""
    return render_template('index.html')


@app.route('/portal')
def portal():
    """Serve the public/student timetable portal."""
    return render_template('portal.html')


# ---------------------------------------------------------------------------
# Configuration API
# ---------------------------------------------------------------------------
@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    if request.method == 'GET':
        cfg = app_data['config']
        if cfg:
            return jsonify({
                'working_days': cfg.working_days,
                'start_time': cfg.start_time,
                'end_time': cfg.end_time,
                'slot_duration_minutes': cfg.slot_duration_minutes,
                'lunch_start': cfg.lunch_start,
                'lunch_end': cfg.lunch_end,
                'breaks': cfg.breaks,
            })
        return jsonify(None)

    user = session.get('user')
    if not user:
        return jsonify({'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401
    if user.get('role') not in (UserRole.ADMIN, UserRole.COORDINATOR):
        return jsonify({'error': 'Insufficient privileges', 'code': 'FORBIDDEN'}), 403

    try:
        data = request.get_json()
        config = WorkingConfig(
            working_days=data['working_days'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            slot_duration_minutes=int(data.get('slot_duration_minutes', 60)),
            breaks=data.get('breaks', []),
            lunch_start=data['lunch_start'],
            lunch_end=data['lunch_end']
        )
        app_data['config'] = config
        save_data(app_data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ---------------------------------------------------------------------------
# Rooms API
# ---------------------------------------------------------------------------
@app.route('/api/rooms', methods=['GET', 'POST'])
def manage_rooms():
    if request.method == 'GET':
        return jsonify([r.to_dict() for r in app_data['rooms']])

    user = session.get('user')
    if not user:
        return jsonify({'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401
    if user.get('role') not in (UserRole.ADMIN, UserRole.COORDINATOR):
        return jsonify({'error': 'Insufficient privileges', 'code': 'FORBIDDEN'}), 403

    try:
        data = request.get_json()
        room = Room(
            id=data['id'],
            name=data['name'],
            room_type=data['room_type'],
            capacity=int(data['capacity']) if data.get('capacity') else None,
            category=data.get('category') or None,
        )
        app_data['rooms'].append(room)
        save_data(app_data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/rooms/<id>', methods=['DELETE', 'PUT'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def manage_rooms_id(id):
    if request.method == 'DELETE':
        app_data['rooms'] = [r for r in app_data['rooms'] if r.id != id]
        save_data(app_data)
        return jsonify({'status': 'ok'})
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            new_obj = Room(
                id=data['id'],
                name=data['name'],
                room_type=data['room_type'],
                capacity=int(data['capacity']) if data.get('capacity') else None,
                category=data.get('category') or None,
            )
            for i, item in enumerate(app_data['rooms']):
                if item.id == id:
                    app_data['rooms'][i] = new_obj
                    break
            else:
                return jsonify({'error': 'Not found'}), 404
            save_data(app_data)
            return jsonify({'status': 'ok'})
        except Exception as e:
            return jsonify({'error': str(e)}), 400


# ---------------------------------------------------------------------------
# Faculty API
# ---------------------------------------------------------------------------
@app.route('/api/faculty', methods=['GET', 'POST'])
def manage_faculty():
    user = session.get('user')
    if request.method == 'GET':
        if not user:
            return jsonify({'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401
        if user.get('role') not in (UserRole.ADMIN, UserRole.COORDINATOR, UserRole.FACULTY):
            return jsonify({'error': 'Insufficient privileges', 'code': 'FORBIDDEN'}), 403
        return jsonify([f.to_dict() for f in app_data['faculty']])

    if not user:
        return jsonify({'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401
    if user.get('role') not in (UserRole.ADMIN, UserRole.COORDINATOR):
        return jsonify({'error': 'Insufficient privileges', 'code': 'FORBIDDEN'}), 403

    try:
        data = request.get_json()
        app_data['faculty'].append(Faculty(id=data['id'], name=data['name']))
        save_data(app_data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/faculty/<id>', methods=['DELETE', 'PUT'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def manage_faculty_id(id):
    if request.method == 'DELETE':
        app_data['faculty'] = [x for x in app_data['faculty'] if x.id != id]
        save_data(app_data)
        return jsonify({'status': 'ok'})
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            new_obj = Faculty(
                id=data['id'],
                name=data['name'],
            )
            for i, item in enumerate(app_data['faculty']):
                if item.id == id:
                    app_data['faculty'][i] = new_obj
                    break
            else:
                return jsonify({'error': 'Not found'}), 404
            save_data(app_data)
            return jsonify({'status': 'ok'})
        except Exception as e:
            return jsonify({'error': str(e)}), 400


# ---------------------------------------------------------------------------
# Sections API
# ---------------------------------------------------------------------------
@app.route('/api/sections', methods=['GET', 'POST'])
def manage_sections():
    if request.method == 'GET':
        # Return sections with their batches
        result = []
        for s in app_data['sections']:
            d = s.to_dict()
            d['batches'] = [b.to_dict() for b in app_data['batches']
                            if b.section_id == s.id]
            result.append(d)
        return jsonify(result)

    user = session.get('user')
    if not user:
        return jsonify({'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401
    if user.get('role') not in (UserRole.ADMIN, UserRole.COORDINATOR):
        return jsonify({'error': 'Insufficient privileges', 'code': 'FORBIDDEN'}), 403

    try:
        data = request.get_json()
        section = Section(
            id=data['id'],
            name=data['name'],
            semester=int(data['semester']),
            division=data['division'],
            strength=int(data['strength']) if data.get('strength') else None,
        )
        app_data['sections'].append(section)
        save_data(app_data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/sections/<id>', methods=['DELETE', 'PUT'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def manage_sections_id(id):
    if request.method == 'DELETE':
        app_data['sections'] = [s for s in app_data['sections'] if s.id != id]
        # Also delete batches of this section
        app_data['batches'] = [b for b in app_data['batches'] if b.section_id != id]
        save_data(app_data)
        return jsonify({'status': 'ok'})
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            new_obj = Section(
                id=data['id'],
                name=data['name'],
                semester=int(data['semester']),
                division=data['division'],
                strength=int(data['strength']) if data.get('strength') else None,
            )
            for i, item in enumerate(app_data['sections']):
                if item.id == id:
                    app_data['sections'][i] = new_obj
                    break
            else:
                return jsonify({'error': 'Not found'}), 404
            save_data(app_data)
            return jsonify({'status': 'ok'})
        except Exception as e:
            return jsonify({'error': str(e)}), 400


# ---------------------------------------------------------------------------
# Batches API
# ---------------------------------------------------------------------------
@app.route('/api/batches', methods=['GET', 'POST'])
def manage_batches():
    if request.method == 'GET':
        return jsonify([b.to_dict() for b in app_data['batches']])

    user = session.get('user')
    if not user:
        return jsonify({'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401
    if user.get('role') not in (UserRole.ADMIN, UserRole.COORDINATOR):
        return jsonify({'error': 'Insufficient privileges', 'code': 'FORBIDDEN'}), 403

    try:
        data = request.get_json()
        batch = Batch(
            id=data['id'],
            name=data['name'],
            section_id=data['section_id'],
            strength=int(data['strength']) if data.get('strength') else None,
        )
        app_data['batches'].append(batch)
        save_data(app_data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/batches/<id>', methods=['DELETE', 'PUT'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def manage_batches_id(id):
    if request.method == 'DELETE':
        app_data['batches'] = [b for b in app_data['batches'] if b.id != id]
        save_data(app_data)
        return jsonify({'status': 'ok'})
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            new_obj = Batch(
                id=data['id'],
                name=data['name'],
                section_id=data['section_id'],
                strength=int(data['strength']) if data.get('strength') else None,
            )
            for i, item in enumerate(app_data['batches']):
                if item.id == id:
                    app_data['batches'][i] = new_obj
                    break
            else:
                return jsonify({'error': 'Not found'}), 404
            save_data(app_data)
            return jsonify({'status': 'ok'})
        except Exception as e:
            return jsonify({'error': str(e)}), 400


# ---------------------------------------------------------------------------
# Courses API
# ---------------------------------------------------------------------------
@app.route('/api/courses', methods=['GET', 'POST'])
def manage_courses():
    if request.method == 'GET':
        return jsonify([c.to_dict() for c in app_data['courses']])

    user = session.get('user')
    if not user:
        return jsonify({'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401
    if user.get('role') not in (UserRole.ADMIN, UserRole.COORDINATOR):
        return jsonify({'error': 'Insufficient privileges', 'code': 'FORBIDDEN'}), 403

    try:
        data = request.get_json()
        course = Course(
            id=data['id'],
            name=data['name'],
            code=data['code'],
            section_id=data['section_id'],
            l=int(data.get('l', 0)),
            t=int(data.get('t', 0)),
            p=float(data.get('p', 0)),
            faculty_ids=data.get('faculty_ids', []),
            assistant_faculty_ids=data.get('assistant_faculty_ids', []),
            room_type=data.get('room_type', RoomType.THEORY_ROOM),
            required_room_id=data.get('required_room_id') or None,
            lab_batches=data.get('lab_batches', []),
        )
        app_data['courses'].append(course)
        save_data(app_data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/courses/<id>', methods=['DELETE', 'PUT'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def manage_courses_id(id):
    if request.method == 'DELETE':
        app_data['courses'] = [c for c in app_data['courses'] if c.id != id]
        save_data(app_data)
        return jsonify({'status': 'ok'})
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            new_obj = Course(
                id=data['id'],
                name=data['name'],
                code=data['code'],
                section_id=data['section_id'],
                l=float(data.get('l', 0)),
                t=float(data.get('t', 0)),
                p=float(data.get('p', 0)),
                faculty_ids=data.get('faculty_ids', []),
                assistant_faculty_ids=data.get('assistant_faculty_ids', []),
                room_type=data.get('room_type', RoomType.THEORY_ROOM),
                required_room_id=data.get('required_room_id') or None,
                lab_batches=data.get('lab_batches', []),
            )
            for i, item in enumerate(app_data['courses']):
                if item.id == id:
                    app_data['courses'][i] = new_obj
                    break
            else:
                return jsonify({'error': 'Not found'}), 404
            save_data(app_data)
            return jsonify({'status': 'ok'})
        except Exception as e:
            return jsonify({'error': str(e)}), 400


# ---------------------------------------------------------------------------
# Academic Terms & Departments API
# ---------------------------------------------------------------------------
@app.route('/api/terms', methods=['GET', 'POST'])
def handle_terms():
    if not app_data.get('terms'):
        app_data['terms'] = [t for t in DEFAULT_TERMS]
    if request.method == 'GET':
        terms = [t.to_dict() for t in app_data['terms']]
        active_id = app_data.get('active_term_id', 'term_2026_fall')
        return jsonify({
            'terms': terms,
            'active_term_id': active_id
        })
    elif request.method == 'POST':
        user = session.get('user')
        if not user:
            return jsonify({'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401
        if user.get('role') != UserRole.ADMIN:
            return jsonify({'error': 'Insufficient privileges', 'code': 'FORBIDDEN'}), 403

        data = request.get_json(silent=True) or {}
        term_id = data.get('id') or f"term_{len(app_data['terms']) + 1}"
        new_term = AcademicTerm(
            id=term_id,
            name=data.get('name', 'New Term'),
            academic_year=data.get('academic_year', '2026-27'),
            semester_type=data.get('semester_type', 'ODD'),
            is_active=bool(data.get('is_active', False))
        )
        app_data['terms'].append(new_term)
        save_data(app_data)
        return jsonify({'status': 'ok', 'term': new_term.to_dict()})


@app.route('/api/terms/activate/<term_id>', methods=['POST'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def activate_term(term_id):
    if not app_data.get('terms'):
        app_data['terms'] = [t for t in DEFAULT_TERMS]
    terms = app_data['terms']
    matched = next((t for t in terms if t.id == term_id), None)
    if not matched:
        return jsonify({'error': f'Term {term_id} not found'}), 404

    for t in terms:
        t.is_active = (t.id == term_id)
    app_data['active_term_id'] = term_id

    # Update publishing term label
    if 'publishing' not in app_data or not app_data['publishing']:
        app_data['publishing'] = {'status': 'DRAFT', 'published_at': None}
    app_data['publishing']['term'] = matched.name

    save_data(app_data)
    return jsonify({
        'status': 'ok',
        'active_term_id': term_id,
        'active_term': matched.to_dict()
    })


@app.route('/api/departments', methods=['GET', 'POST'])
def handle_departments():
    if not app_data.get('departments'):
        app_data['departments'] = [d for d in DEFAULT_DEPARTMENTS]
    if request.method == 'GET':
        depts = [d.to_dict() for d in app_data['departments']]
        return jsonify(depts)
    elif request.method == 'POST':
        user = session.get('user')
        if not user:
            return jsonify({'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401
        if user.get('role') != UserRole.ADMIN:
            return jsonify({'error': 'Insufficient privileges', 'code': 'FORBIDDEN'}), 403

        data = request.get_json(silent=True) or {}
        dept_id = data.get('id') or f"dept_{data.get('code', 'NEW').lower()}"
        new_dept = Department(
            id=dept_id,
            name=data.get('name', 'New Department'),
            code=data.get('code', 'NEW').upper()
        )
        app_data['departments'].append(new_dept)
        save_data(app_data)
        return jsonify({'status': 'ok', 'department': new_dept.to_dict()})


# ---------------------------------------------------------------------------
# Authentication & Role-Based Access Control API
# ---------------------------------------------------------------------------
@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    user = session.get('user')
    csrf_token = session.get('csrf_token')
    if user and not csrf_token:
        csrf_token = secrets.token_hex(32)
        session['csrf_token'] = csrf_token
    resp = jsonify({
        'authenticated': bool(user),
        'user': user,
        'csrf_token': csrf_token if user else None
    })
    if user and csrf_token:
        resp.set_cookie(
            'csrf_token',
            csrf_token,
            samesite='Lax',
            secure=(os.environ.get('FLASK_ENV') == 'production')
        )
    return resp


@app.route('/api/auth/login', methods=['POST'])
def login():
    if not app_data.get('users'):
        app_data['users'] = get_default_users()

    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    user = next((u for u in app_data['users'] if u.username == username), None)
    if not user or not verify_password(password, user.password_hash, user.salt):
        return jsonify({'error': 'Invalid username or password'}), 401

    session.clear()
    csrf_token = secrets.token_hex(32)
    user_info = {
        'id': user.id,
        'username': user.username,
        'role': user.role,
        'name': user.name,
        'faculty_id': getattr(user, 'faculty_id', None)
    }
    session['user'] = user_info
    session['csrf_token'] = csrf_token
    session.permanent = True

    resp = jsonify({
        'status': 'ok',
        'message': f'Signed in successfully as {user.name}',
        'user': user_info,
        'csrf_token': csrf_token
    })
    resp.set_cookie(
        'csrf_token',
        csrf_token,
        samesite='Lax',
        secure=(os.environ.get('FLASK_ENV') == 'production')
    )
    return resp


@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    session.clear()
    resp = jsonify({'status': 'ok', 'message': 'Signed out successfully'})
    resp.delete_cookie('csrf_token')
    return resp


@app.route('/api/auth/users', methods=['GET', 'POST'])
@login_required
@require_role(UserRole.ADMIN)
def manage_users():
    if not app_data.get('users'):
        app_data['users'] = get_default_users()

    if request.method == 'GET':
        users = [{
            'id': u.id,
            'username': u.username,
            'role': u.role,
            'name': u.name
        } for u in app_data['users']]
        return jsonify(users)
    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        role = data.get('role', UserRole.COORDINATOR)
        name = data.get('name') or username

        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400

        if any(u.username == username for u in app_data['users']):
            return jsonify({'error': f"User '{username}' already exists"}), 400

        p_hash, salt = hash_password(password)
        new_user = User(
            id=f"user_{len(app_data['users']) + 1}",
            username=username,
            password_hash=p_hash,
            salt=salt,
            role=role,
            name=name
        )
        app_data['users'].append(new_user)
        save_data(app_data)
        return jsonify({
            'status': 'ok',
            'user': {
                'id': new_user.id,
                'username': new_user.username,
                'role': new_user.role,
                'name': new_user.name
            }
        })


# ---------------------------------------------------------------------------
# Time Slots API
# ---------------------------------------------------------------------------
@app.route('/api/time-slots', methods=['GET'])
def get_time_slots():
    """Return the dynamically generated time slots for the current config."""
    if not app_data['config']:
        return jsonify({'error': 'Configuration not set. Save config first.'}), 400
    slots = generate_time_slots(app_data['config'])
    return jsonify([s.to_dict() for s in slots])


# ---------------------------------------------------------------------------
# Generate Timetable API
# ---------------------------------------------------------------------------
@app.route('/api/generate', methods=['POST'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def generate_timetable():
    """Run the CSP backtracking scheduler and return the result."""
    if not app_data['config']:
        return jsonify({'error': 'Configuration not set'}), 400
    if not app_data['rooms']:
        return jsonify({'error': 'No rooms defined'}), 400
    if not app_data['courses']:
        return jsonify({'error': 'No courses defined'}), 400

    try:
        from scheduler_trace import SchedulerTrace
        trace = SchedulerTrace(level=trace_config['level'], session_filter=trace_config['session_filter'])
        
        engine = SchedulingEngine(
            config=app_data['config'],
            courses=app_data['courses'],
            rooms=app_data['rooms'],
            faculty_list=app_data['faculty'],
            sections=app_data['sections'],
            batches=app_data['batches'],
            trace=trace
        )
        result = engine.solve()
        if hasattr(engine, 'trace') and engine.trace.enabled:
            engine.trace.write()
        app_data['engine'] = engine
        app_data['result'] = result

        if result['status'] == 'success':
            master = result.get('assignments', [])
            day_order = {d: i for i, d in enumerate(app_data['config'].working_days)}
            master.sort(key=lambda e: (day_order.get(e['day'], 99),
                                       e['time_start'], e['section_name']))
            result['master_timetable'] = master

        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Timetable View APIs
# ---------------------------------------------------------------------------
def _get_or_restore_engine():
    engine = app_data.get('engine')
    if engine and hasattr(engine, 'assignments') and len(engine.assignments) > 0:
        return engine
    result = app_data.get('result')
    if result and result.get('assignments_data') and app_data.get('config'):
        try:
            engine = SchedulingEngine(
                app_data['config'],
                app_data['courses'],
                app_data['rooms'],
                app_data['faculty'],
                app_data['sections'],
                app_data['batches']
            )
            engine.load_assignments_data(result['assignments_data'])
            app_data['engine'] = engine
            return engine
        except Exception as e:
            print(f"Error restoring engine in _get_or_restore_engine: {e}")
    return engine


@app.route('/api/timetable/master', methods=['GET'])
def get_master_timetable():
    """Return the master timetable as a flat list."""
    pub = app_data.get('publishing') or {}
    is_published = pub.get('is_published', False) or pub.get('status') == 'PUBLISHED'
    user = session.get('user')
    if not is_published:
        if not user:
            return jsonify({'error': 'Authentication required to view draft timetable', 'code': 'UNAUTHORIZED'}), 401
        if user.get('role') not in (UserRole.ADMIN, UserRole.COORDINATOR):
            return jsonify({'error': 'Timetable is unpublished and cannot be accessed by your role', 'code': 'FORBIDDEN'}), 403

    engine = _get_or_restore_engine()
    result = app_data.get('result')
    if not engine or not result or result.get('status') not in ('success', 'partial'):
        return jsonify({'error': 'Timetable not generated or failed'}), 400
    return jsonify(engine._format_assignments())


@app.route('/api/timetable/section/<section_id>', methods=['GET'])
def get_section_timetable(section_id):
    return _get_view('section', section_id)


@app.route('/api/timetable/faculty/<faculty_id>', methods=['GET'])
def get_faculty_timetable(faculty_id):
    return _get_view('faculty', faculty_id)


@app.route('/api/timetable/room/<room_id>', methods=['GET'])
def get_room_timetable(room_id):
    return _get_view('room', room_id)


def _get_view(view_type, entity_id):
    """Delegate to the engine's view method."""
    pub = app_data.get('publishing') or {}
    is_published = pub.get('is_published', False) or pub.get('status') == 'PUBLISHED'
    user = session.get('user')

    if not is_published:
        if not user:
            return jsonify({'error': 'Authentication required to view draft timetable', 'code': 'UNAUTHORIZED'}), 401
        role = user.get('role')
        if role not in (UserRole.ADMIN, UserRole.COORDINATOR):
            if view_type == 'faculty' and role == UserRole.FACULTY:
                # Faculty can only view their own draft timetable
                if user.get('id') != entity_id and user.get('username') != entity_id and user.get('name') != entity_id:
                    return jsonify({'error': 'Access denied to other faculty member draft schedules', 'code': 'FORBIDDEN'}), 403
            else:
                return jsonify({'error': 'Timetable is unpublished and cannot be accessed by your role', 'code': 'FORBIDDEN'}), 403

    engine = _get_or_restore_engine()
    result = app_data.get('result')
    if not engine or not result or result.get('status') not in ('success', 'partial'):
        return jsonify({'error': 'Timetable not generated or failed'}), 400

    if view_type == 'section':
        return jsonify(engine.get_section_view(entity_id))
    elif view_type == 'faculty':
        return jsonify(engine.get_faculty_view(entity_id))
    elif view_type == 'room':
        return jsonify(engine.get_room_view(entity_id))
    return jsonify({'error': 'Invalid view type'}), 400



@app.route('/api/timetable/variant/<int:index>', methods=['POST'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def select_variant(index):
    engine = _get_or_restore_engine()
    result = app_data.get('result')
    if not engine or not result or result.get('status') not in ('success', 'partial'):
        return jsonify({'error': 'No generated timetable found'}), 400
        
    variants = result.get('variants', [])
    if index < 0 or index >= len(variants):
        return jsonify({'error': 'Invalid variant index'}), 400
        
    engine.load_assignments_data(variants[index]['assignments_data'])
    result['assignments_data'] = variants[index]['assignments_data']
    result['active_variant_index'] = index
    result['assignments'] = engine._format_assignments()
    result['soft_score'] = variants[index].get('soft_score', {})
    result['status'] = 'success'
    save_data(app_data)
    return jsonify({
        'status': 'ok',
        'active_variant_index': index,
        'soft_score': result['soft_score']
    })


@app.route('/api/timetable/metadata', methods=['GET'])
def get_metadata():
    result = app_data.get('result')
    if not result or result.get('status') not in ('success', 'partial'):
        return jsonify({'error': 'No valid timetable'}), 400
    variants = result.get('variants', [])
    active_idx = result.get('active_variant_index', 0)
    score = variants[active_idx]['soft_score'] if variants else {}
    return jsonify({
        'num_variants': len(variants),
        'active_variant_index': active_idx,
        'active_score': score
    })


@app.route('/api/timetable/status', methods=['GET'])
def get_publishing_status():
    pub = app_data.get('publishing') or {
        'status': 'DRAFT',
        'is_published': False,
        'published_at': None,
        'term': 'Academic Year 2026-27 (Term 1)'
    }
    if 'is_published' not in pub:
        pub['is_published'] = (pub.get('status') == 'PUBLISHED')
    return jsonify(pub)


@app.route('/api/timetable/publish', methods=['POST'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def publish_timetable():
    engine = _get_or_restore_engine()
    if not engine or not app_data.get('result'):
        return jsonify({'error': 'No generated timetable available to publish'}), 400
    from datetime import datetime, timezone
    data = request.get_json(silent=True) or {}
    term = data.get('term', 'Academic Year 2026-27 (Term 1)')
    pub = {
        'status': 'PUBLISHED',
        'is_published': True,
        'published_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'term': term
    }
    app_data['publishing'] = pub
    save_data(app_data)
    return jsonify({'status': 'ok', 'publishing': pub})


@app.route('/api/timetable/validate-move', methods=['POST'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def api_validate_move():
    engine = _get_or_restore_engine()
    if not engine or not app_data.get('result'):
        return jsonify({'valid': False, 'message': 'No generated timetable found', 'details': {'code': 'NO_TIMETABLE'}}), 400

    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')
    target_day = data.get('target_day')
    target_start_slot = data.get('target_start_slot')
    target_room_id = data.get('target_room_id')

    if not session_id or not target_day or target_start_slot is None or not target_room_id:
        return jsonify({
            'valid': False,
            'message': 'Missing required fields: session_id, target_day, target_start_slot, target_room_id',
            'details': {'code': 'MISSING_FIELDS'}
        }), 400

    try:
        target_start_slot = int(target_start_slot)
    except (TypeError, ValueError):
        return jsonify({'valid': False, 'message': 'Invalid target_start_slot number', 'details': {'code': 'INVALID_SLOT'}}), 400

    try:
        valid, message, details = adjuster.validate_move(
            engine, session_id, target_day, target_start_slot, target_room_id
        )
        return jsonify({
            'valid': valid,
            'message': message,
            'details': details
        })
    except Exception as e:
        return jsonify({'valid': False, 'message': f'Validation exception: {str(e)}', 'details': {'code': 'INTERNAL_ERROR'}}), 500


@app.route('/api/timetable/move', methods=['POST'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def api_execute_move():
    engine = _get_or_restore_engine()
    if not engine or not app_data.get('result'):
        return jsonify({'status': 'error', 'message': 'No generated timetable found', 'details': {'code': 'NO_TIMETABLE'}}), 400

    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')
    target_day = data.get('target_day')
    target_start_slot = data.get('target_start_slot')
    target_room_id = data.get('target_room_id')

    if not session_id or not target_day or target_start_slot is None or not target_room_id:
        return jsonify({
            'status': 'error',
            'message': 'Missing required fields: session_id, target_day, target_start_slot, target_room_id',
            'details': {'code': 'MISSING_FIELDS'}
        }), 400

    try:
        target_start_slot = int(target_start_slot)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Invalid target_start_slot number', 'details': {'code': 'INVALID_SLOT'}}), 400

    try:
        success, message, details = adjuster.execute_move(
            engine, session_id, target_day, target_start_slot, target_room_id, app_data
        )
        if not success:
            return jsonify({'status': 'error', 'message': message, 'details': details}), 400

        return jsonify({
            'status': 'ok',
            'message': message,
            'details': details
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Move exception: {str(e)}', 'details': {'code': 'INTERNAL_ERROR'}}), 500


@app.route('/api/timetable/swap', methods=['POST'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def api_execute_swap():
    engine = _get_or_restore_engine()
    if not engine or not app_data.get('result'):
        return jsonify({'status': 'error', 'message': 'No generated timetable found', 'details': {'code': 'NO_TIMETABLE'}}), 400

    data = request.get_json(silent=True) or {}
    session_a_id = data.get('session_a_id')
    session_b_id = data.get('session_b_id')

    if not session_a_id or not session_b_id:
        return jsonify({'status': 'error', 'message': 'Both session_a_id and session_b_id are required'}), 400

    try:
        success, message, details = adjuster.execute_swap(
            engine, session_a_id, session_b_id, app_data
        )
        if not success:
            return jsonify({'status': 'error', 'message': message, 'details': details}), 400

        return jsonify({
            'status': 'ok',
            'message': message,
            'details': details
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Swap exception: {str(e)}', 'details': {'code': 'INTERNAL_ERROR'}}), 500


@app.route('/api/timetable/unpublish', methods=['POST'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def unpublish_timetable():
    pub = {
        'status': 'DRAFT',
        'is_published': False,
        'published_at': None,
        'term': (app_data.get('publishing') or {}).get('term', 'Academic Year 2026-27 (Term 1)')
    }
    app_data['publishing'] = pub
    save_data(app_data)
    return jsonify({'status': 'ok', 'publishing': pub})


@app.route('/api/timetable/versions', methods=['GET'])
@login_required
def api_get_schedule_versions():
    term_id = request.args.get('term_id') or app_data.get('active_term_id')
    versions = get_schedule_versions(term_id)
    return jsonify({'status': 'ok', 'versions': versions})


@app.route('/api/timetable/versions/snapshot', methods=['POST'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def api_create_schedule_snapshot():
    if not app_data.get('result') or not app_data['result'].get('assignments_data'):
        return jsonify({'error': 'No generated schedule available to snapshot', 'code': 'NO_TIMETABLE'}), 400

    data = request.get_json(silent=True) or {}
    from datetime import datetime, timezone
    default_tag = datetime.now(timezone.utc).strftime('v%Y%m%d_%H%M%S')
    version_tag = data.get('version_tag', '').strip() or default_tag
    note = data.get('note', '').strip() or 'Manual schedule snapshot'

    user = session.get('user', {})
    user_id = user.get('id') if isinstance(user, dict) else None

    try:
        snapshot = create_schedule_snapshot(
            academic_term_id=app_data.get('active_term_id', 'term_2026_fall'),
            version_tag=version_tag,
            note=note,
            user_id=user_id,
            app_data=app_data
        )
        return jsonify({'status': 'ok', 'message': 'Snapshot created', 'version': snapshot})
    except Exception as e:
        return jsonify({'error': f'Failed to create snapshot: {str(e)}', 'code': 'INTERNAL_ERROR'}), 500


@app.route('/api/timetable/versions/<int:version_id>/restore', methods=['POST'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def api_restore_schedule_version(version_id):
    try:
        success, message = restore_schedule_version(version_id, app_data)
        if not success:
            return jsonify({'status': 'error', 'message': message, 'code': 'NOT_FOUND'}), 404

        return jsonify({
            'status': 'ok',
            'message': message,
            'result': {
                'status': app_data['result'].get('status', 'SUCCESS'),
                'soft_score': app_data['result'].get('soft_score'),
                'assignments_count': len(app_data['result'].get('assignments_data', []))
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Rollback failed: {str(e)}', 'code': 'INTERNAL_ERROR'}), 500


@app.route('/api/faculty/<faculty_id>/calendar.ics', methods=['GET'])
def api_faculty_calendar_ics(faculty_id):
    fac = next((f for f in app_data.get('faculty', []) if f.id == faculty_id), None)
    if not fac:
        return jsonify({'error': 'Faculty member not found'}), 404

    pub = app_data.get('publishing') or {}
    is_published = pub.get('is_published', False)
    user = session.get('user')

    if not is_published:
        if not user:
            return jsonify({'error': 'Timetable is unpublished. Authentication required.', 'code': 'UNAUTHORIZED'}), 401

        role = user.get('role')
        if role not in (UserRole.ADMIN, UserRole.COORDINATOR):
            user_fac_id = user.get('faculty_id') or user.get('id')
            if role == UserRole.STUDENT:
                return jsonify({'error': 'Students cannot access unpublished schedule calendar feeds', 'code': 'FORBIDDEN'}), 403
            elif role == UserRole.FACULTY:
                if user_fac_id != faculty_id and user.get('username') != faculty_id:
                    return jsonify({'error': 'Faculty cannot access other faculty members unpublished calendars', 'code': 'FORBIDDEN'}), 403
            else:
                return jsonify({'error': 'Access denied to unpublished faculty schedule', 'code': 'FORBIDDEN'}), 403

    if not app_data.get('config') or not app_data.get('result'):
        return jsonify({'error': 'No timetable available'}), 400

    assignments = []
    courses_by_id = {c.id: c for c in app_data.get('courses', [])}

    for a in app_data['result'].get('assignments_data', []):
        sess_id = a.get('session_id', '')
        c = next((crs for cid, crs in courses_by_id.items() if sess_id.startswith(cid)), None)
        if c and (faculty_id in c.faculty_ids or faculty_id in getattr(c, 'assistant_faculty_ids', [])):
            assignments.append(a)

    rooms_by_id = {r.id: r for r in app_data.get('rooms', [])}
    sections_by_id = {s.id: s for s in app_data.get('sections', [])}
    term_name = pub.get('term') or app_data.get('active_term_id', 'Academic Term')

    ics_content = generate_faculty_ical(
        faculty=fac,
        assignments=assignments,
        courses_by_id=courses_by_id,
        rooms_by_id=rooms_by_id,
        sections_by_id=sections_by_id,
        config=app_data['config'],
        term_name=term_name
    )

    return Response(
        ics_content,
        mimetype='text/calendar; charset=utf-8',
        headers={
            'Content-Disposition': f'inline; filename="faculty_{faculty_id}_schedule.ics"',
            'Cache-Control': 'no-cache'
        }
    )


@app.route('/manifest.json', methods=['GET'])
def get_manifest():
    return send_file(os.path.join(app.root_path, 'static', 'manifest.json'), mimetype='application/manifest+json')


@app.route('/sw.js', methods=['GET'])
def get_service_worker():
    return send_file(os.path.join(app.root_path, 'static', 'sw.js'), mimetype='application/javascript')


@app.route('/api/faculty/me/schedule', methods=['GET'])
@login_required
def api_faculty_me_schedule():
    user = session.get('user') or {}
    role = user.get('role')

    target_faculty_id = None
    if role == UserRole.FACULTY:
        target_faculty_id = user.get('faculty_id')
        if not target_faculty_id:
            username = (user.get('username') or '').strip().lower()
            user_name = (user.get('name') or '').strip().lower()
            for f in app_data.get('faculty', []):
                if f.id.lower() == username or (user_name and (user_name == f.name.lower() or f.name.lower() in user_name)):
                    target_faculty_id = f.id
                    break
    elif role in (UserRole.ADMIN, UserRole.COORDINATOR):
        target_faculty_id = request.args.get('faculty_id') or (app_data['faculty'][0].id if app_data.get('faculty') else None)
    else:
        return jsonify({'error': 'Access restricted to faculty and academic administrators', 'code': 'FORBIDDEN'}), 403

    if not target_faculty_id:
        return jsonify({'error': 'No linked faculty profile found for user account', 'code': 'FACULTY_NOT_LINKED'}), 404

    fac = next((f for f in app_data.get('faculty', []) if f.id == target_faculty_id), None)
    if not fac:
        return jsonify({'error': f'Linked faculty profile {target_faculty_id} not found in database', 'code': 'FACULTY_NOT_FOUND'}), 404

    courses_taught = [c for c in app_data.get('courses', []) if target_faculty_id in c.faculty_ids or target_faculty_id in getattr(c, 'assistant_faculty_ids', [])]
    total_weekly_hours = sum(c.l + c.t + c.p for c in courses_taught)

    sessions = []
    if app_data.get('result') and app_data['result'].get('assignments_data'):
        courses_by_id = {c.id: c for c in app_data.get('courses', [])}
        rooms_by_id = {r.id: r for r in app_data.get('rooms', [])}
        sections_by_id = {s.id: s for s in app_data.get('sections', [])}

        for a in app_data['result']['assignments_data']:
            sess_id = a.get('session_id', '')
            c = next((crs for cid, crs in courses_by_id.items() if sess_id.startswith(cid)), None)
            if c and (target_faculty_id in c.faculty_ids or target_faculty_id in getattr(c, 'assistant_faculty_ids', [])):
                room = rooms_by_id.get(a.get('room_id'))
                sec = sections_by_id.get(a.get('section_id'))
                sessions.append({
                    'session_id': sess_id,
                    'day': a.get('day'),
                    'start_slot_index': a.get('start_slot_index'),
                    'duration_slots': a.get('duration_slots', 1),
                    'course_id': c.id,
                    'course_code': c.code,
                    'course_name': c.name,
                    'room_id': a.get('room_id'),
                    'room_name': room.name if room else a.get('room_id'),
                    'section_id': a.get('section_id'),
                    'section_name': sec.name if sec else a.get('section_id')
                })

    return jsonify({
        'status': 'ok',
        'faculty': {
            'id': fac.id,
            'name': fac.name,
            'available_days': fac.available_days,
            'weekly_contact_hours': total_weekly_hours,
            'course_count': len(courses_taught),
            'calendar_ics_url': f'/api/faculty/{target_faculty_id}/calendar.ics'
        },
        'courses': [
            {
                'id': c.id,
                'name': c.name,
                'code': c.code,
                'section_id': c.section_id,
                'hours': c.l + c.t + c.p,
                'room_type': c.room_type
            } for c in courses_taught
        ],
        'sessions': sessions,
        'publishing': app_data.get('publishing')
    })


@app.route('/api/timetable/change-log', methods=['GET'])
def api_get_change_log():
    term_id = request.args.get('term_id') or app_data.get('active_term_id')
    limit = int(request.args.get('limit', 50))
    alerts = get_change_alerts(term_id, limit=limit)
    return jsonify({
        'status': 'ok',
        'count': len(alerts),
        'alerts': alerts
    })


@app.route('/api/timetable/change-log/clear', methods=['POST'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def api_clear_change_log():
    term_id = app_data.get('active_term_id')
    clear_change_alerts(term_id)
    return jsonify({
        'status': 'ok',
        'message': 'Change alert log cleared successfully'
    })


@app.route('/api/reports/utilization', methods=['GET'])
def api_get_utilization_report():
    total_slots_per_room = 40
    if app_data.get('config'):
        days = len(app_data['config'].working_days)
        time_slots_count = len(generate_time_slots(app_data['config']))
        total_slots_per_room = max(1, days * time_slots_count)

    assignments = (app_data.get('result') or {}).get('assignments_data', [])
    rooms = app_data.get('rooms', [])
    faculty = app_data.get('faculty', [])
    courses = app_data.get('courses', [])
    sections = app_data.get('sections', [])
    depts = app_data.get('departments', [])

    room_counts = {}
    for a in assignments:
        rid = a.get('room_id')
        room_counts[rid] = room_counts.get(rid, 0) + 1

    room_metrics = []
    for r in rooms:
        occupied = room_counts.get(r.id, 0)
        pct = round((occupied * 100.0) / total_slots_per_room, 1)
        room_metrics.append({
            'room_id': r.id,
            'room_name': r.name,
            'room_type': r.room_type,
            'capacity': r.capacity,
            'occupied_slots': occupied,
            'total_slots': total_slots_per_room,
            'utilization_pct': pct
        })

    fac_metrics = []
    for f in faculty:
        taught = [c for c in courses if f.id in c.faculty_ids or f.id in getattr(c, 'assistant_faculty_ids', [])]
        hours = sum(c.l + c.t + c.p for c in taught)
        fac_metrics.append({
            'faculty_id': f.id,
            'faculty_name': f.name,
            'course_count': len(taught),
            'weekly_hours': hours
        })

    sec_metrics = []
    for s in sections:
        sec_assigns = [a for a in assignments if a.get('section_id') == s.id]
        sec_metrics.append({
            'section_id': s.id,
            'section_name': s.name,
            'semester': s.semester,
            'scheduled_sessions': len(sec_assigns)
        })

    return jsonify({
        'status': 'ok',
        'term_id': app_data.get('active_term_id'),
        'total_assignments': len(assignments),
        'rooms': sorted(room_metrics, key=lambda x: x['utilization_pct'], reverse=True),
        'faculty': sorted(fac_metrics, key=lambda x: x['weekly_hours'], reverse=True),
        'sections': sorted(sec_metrics, key=lambda x: x['semester']),
        'departments': [{'id': d.id, 'name': d.name, 'code': d.code} for d in depts]
    })


@app.route('/api/generate-multiple', methods=['POST'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def generate_multiple():
    if not app_data['config']:
        return jsonify({'error': 'Configuration not set'}), 400
    if not app_data['rooms']:
        return jsonify({'error': 'No rooms defined'}), 400
    if not app_data['courses']:
        return jsonify({'error': 'No courses defined'}), 400

    try:
        data = request.get_json() or {}
        count = int(data.get('count', 5))
        seed = int(data.get('seed', 1000))
        max_attempts = int(data.get('max_attempts', 50))
        min_div = float(data.get('min_diversity_pct', 25.0))
        
        from scheduler_trace import SchedulerTrace
        trace = SchedulerTrace(level=trace_config['level'], session_filter=trace_config['session_filter'])
        
        engine = SchedulingEngine(
            config=app_data['config'],
            courses=app_data['courses'],
            rooms=app_data['rooms'],
            faculty_list=app_data['faculty'],
            sections=app_data['sections'],
            batches=app_data['batches'],
            trace=trace
        )
        result = engine.solve_multiple(requested_count=count, base_seed=seed, max_attempts=max_attempts, min_diversity_pct=min_div)
        if hasattr(engine, 'trace') and engine.trace.enabled:
            engine.trace.write()
        
        # Save state
        app_data['engine'] = engine
        app_data['result'] = result
        
        # Convert variants -> alternatives mapping to maintain compatibility with existing variant code
        if 'alternatives' in result:
            result['variants'] = result['alternatives']
        variants = result.get('variants', [])
        if variants:
            result['active_variant_index'] = 0
            engine.load_assignments_data(variants[0]['assignments_data'])
            result['assignments_data'] = variants[0]['assignments_data']
            result['assignments'] = engine._format_assignments()
            result['soft_score'] = variants[0].get('soft_score', {})
            result['status'] = 'success'
            
        save_data(app_data)
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/debug/trace/config', methods=['GET', 'POST'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def manage_trace_config():
    if request.method == 'GET':
        return jsonify(trace_config)
    else:
        data = request.get_json() or {}
        trace_config['level'] = int(data.get('level', 0))
        filter_str = data.get('session_filter', '').strip()
        if filter_str:
            trace_config['session_filter'] = [x.strip() for x in filter_str.split(',') if x.strip()]
        else:
            trace_config['session_filter'] = None
        return jsonify(trace_config)


@app.route('/api/debug/trace/download/<fmt>', methods=['GET'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def download_trace(fmt):
    import os
    from flask import send_file
    if fmt == 'txt':
        path = 'scheduler_trace.txt'
    elif fmt == 'json':
        path = 'scheduler_trace.json'
    else:
        return jsonify({'error': 'invalid format'}), 400
        
    if not os.path.exists(path):
        return jsonify({'error': 'No trace file found'}), 404
    return send_file(path, as_attachment=True)


@app.route('/api/validation', methods=['GET'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def validate_current_timetable():
    """Post-generation validation: re-check all hard constraints."""
    engine = _get_or_restore_engine()
    result = app_data.get('result')
    if not engine or not result or result.get('status') not in ('success', 'partial'):
        return jsonify({'error': 'No valid timetable to validate'}), 400

    validation = validate_timetable(
        assignments=list(engine.assignments.values()),
        sessions_by_id=engine.sessions_by_id,
        sections_by_id=engine.sections_by_id,
        faculty_by_id=engine.faculty_by_id,
        rooms_by_id=engine.rooms_by_id,
        config=app_data['config'],
        time_slots=engine.time_slots,
        batches_by_id=engine.batches_by_id,
    )
    return jsonify({
        'valid': validation.get('is_valid', True),
        'conflicts': validation.get('conflicts', []),
    })


@app.route('/api/summary', methods=['GET'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def get_summary():
    """Return a summary of the current dataset before timetable generation."""
    cfg   = app_data['config']
    courses  = app_data['courses']
    sections = app_data['sections']
    batches  = app_data['batches']
    faculty  = app_data['faculty']
    rooms    = app_data['rooms']

    theory_sessions = 0
    lab_sessions    = 0
    total_weekly_hours = 0

    for c in courses:
        theory_sessions += int(c.l) + int(c.t)
        lb = len(c.lab_batches) if c.lab_batches else 0
        if lb > 0 and c.p > 0:
            lab_sessions += lb
        total_weekly_hours += c.l + c.t + c.p

    slots_per_week = 0
    if cfg:
        from time_slots import generate_time_slots
        slots = generate_time_slots(cfg)
        slots_per_week = len(slots) * len(cfg.working_days)

    return jsonify({
        'sections':                 len(sections),
        'batches':                  len(batches),
        'faculty':                  len(faculty),
        'rooms':                    len(rooms),
        'lab_rooms':                len([r for r in rooms if r.room_type == 'LAB']),
        'theory_rooms':             len([r for r in rooms if r.room_type == 'THEORY_ROOM']),
        'courses':                  len(courses),
        'theory_sessions_per_week': theory_sessions,
        'lab_sessions_per_week':    lab_sessions,
        'total_weekly_session_hours': round(total_weekly_hours, 1),
        'available_slots_per_week': slots_per_week,
        'working_days':             cfg.working_days if cfg else [],
        'config_set':               cfg is not None,
    })


@app.route('/api/load-demo', methods=['POST'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def load_demo():
    """Load the built-in demonstration dataset."""
    try:
        data = request.get_json(silent=True) or {}
        scenario = data.get('scenario', 'standard')
        demo = get_demo_data(scenario)
        app_data['config'] = demo['config']
        app_data['rooms'] = demo['rooms']
        app_data['faculty'] = demo['faculty']
        app_data['sections'] = demo['sections']
        app_data['batches'] = demo.get('batches', [])
        app_data['courses'] = demo['courses']
        app_data['engine'] = None
        app_data['result'] = None
        save_data(app_data)
        return jsonify({'status': 'ok', 'scenario': scenario, 'message': f'Demo dataset ({scenario}) loaded successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear', methods=['POST'])
@login_required
@require_role(UserRole.ADMIN)
def clear_data():
    """Reset all application state."""
    for key in ('config', 'engine', 'result', 'publishing'):
        app_data[key] = None
    for key in ('rooms', 'faculty', 'sections', 'batches', 'courses'):
        app_data[key] = []
    app_data['active_term_id'] = 'term_2026_fall'
    app_data['terms'] = [t for t in DEFAULT_TERMS]
    app_data['departments'] = [d for d in DEFAULT_DEPARTMENTS]
    app_data['users'] = get_default_users()
    save_data(app_data)
    return jsonify({'status': 'ok'})


# ---------------------------------------------------------------------------
# Data Import & Export API
# ---------------------------------------------------------------------------
@app.route('/api/import/template', methods=['GET'])
def download_import_template():
    """Download starter Excel template for institutional data ingestion."""
    try:
        buf = importer.generate_import_template()
        return send_file(
            buf,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='AutoSchedule_Data_Template.xlsx'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/import/excel', methods=['POST'])
@login_required
@require_role(UserRole.ADMIN, UserRole.COORDINATOR)
def import_excel_data():
    """Import and validate Excel workbook containing institutional assets."""
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'errors': ['No file uploaded. Please select an Excel workbook (.xlsx).']}), 400

    file = request.files['file']
    if not file.filename or not file.filename.endswith(('.xlsx', '.xlsm')):
        return jsonify({'status': 'error', 'errors': ['Unsupported file type. Please upload a valid .xlsx workbook.']}), 400

    try:
        file_bytes = file.read()
        success, counts, errors, parsed = importer.parse_and_validate_excel(file_bytes)

        if not success:
            return jsonify({
                'status': 'error',
                'message': f'Validation failed with {len(errors)} error(s). No data was imported.',
                'errors': errors
            }), 400

        # Merge or replace institutional data
        mode = request.form.get('mode', 'replace')
        if mode == 'replace':
            app_data['rooms'] = parsed['rooms']
            app_data['faculty'] = parsed['faculty']
            app_data['sections'] = parsed['sections']
            app_data['batches'] = parsed['batches']
            app_data['courses'] = parsed['courses']
        else:
            # Append avoiding duplicate IDs
            existing_room_ids = {r.id for r in app_data['rooms']}
            app_data['rooms'].extend([r for r in parsed['rooms'] if r.id not in existing_room_ids])

            existing_fac_ids = {f.id for f in app_data['faculty']}
            app_data['faculty'].extend([f for f in parsed['faculty'] if f.id not in existing_fac_ids])

            existing_sec_ids = {s.id for s in app_data['sections']}
            app_data['sections'].extend([s for s in parsed['sections'] if s.id not in existing_sec_ids])

            existing_bat_ids = {b.id for b in app_data['batches']}
            app_data['batches'].extend([b for b in parsed['batches'] if b.id not in existing_bat_ids])

            existing_crs_ids = {c.id for c in app_data['courses']}
            app_data['courses'].extend([c for c in parsed['courses'] if c.id not in existing_crs_ids])

        # Reset schedule engine state since data changed
        app_data['engine'] = None
        app_data['result'] = None
        save_data(app_data)

        return jsonify({
            'status': 'ok',
            'message': 'Excel workbook imported successfully.',
            'imported': counts
        })
    except Exception as e:
        return jsonify({'status': 'error', 'errors': [f'Server processing exception: {str(e)}']}), 500


@app.route('/api/export/excel', methods=['GET'])
def export_timetable_excel():
    """Download multi-tab formatted Excel workbook of current generated timetable."""
    pub = app_data.get('publishing') or {}
    is_published = pub.get('is_published', False) or pub.get('status') == 'PUBLISHED'
    user = session.get('user')
    if not is_published:
        if not user:
            return jsonify({'error': 'Authentication required to export draft timetable', 'code': 'UNAUTHORIZED'}), 401
        if user.get('role') not in (UserRole.ADMIN, UserRole.COORDINATOR):
            return jsonify({'error': 'Timetable is unpublished and cannot be exported by your role', 'code': 'FORBIDDEN'}), 403

    try:
        _get_or_restore_engine()
        buf = exporter.generate_timetable_excel(app_data)
        return send_file(
            buf,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='AutoSchedule_Master_Timetable.xlsx'
        )
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 60)
    print("  Constraint-Based Academic Timetable Scheduler")
    print("  Open http://127.0.0.1:5000 in your browser")
    print("=" * 60)
    app.run(debug=True, port=5000)
