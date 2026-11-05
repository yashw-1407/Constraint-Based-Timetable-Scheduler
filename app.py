"""
app.py - Flask web application for the Timetable Scheduling Engine.

Serves the single-page frontend and provides a JSON API for:
  - CRUD operations on configuration, rooms, faculty, sections, batches, courses
  - Generating timetables via the SchedulingEngine (CSP backtracking)
  - Retrieving timetable views (master, section, faculty, room)
  - Post-generation validation and demo data loading

All data is stored in-memory (no database required for the MVP).
"""

from flask import Flask, jsonify, request, render_template, send_file
import os
import io
from models import WorkingConfig, Room, Faculty, Section, Batch, Course, RoomType, CourseType, AcademicTerm, Department
from time_slots import generate_time_slots, time_to_minutes
from scheduler_trace import SchedulerTrace
from scheduler import SchedulingEngine
from constraints import validate_timetable
from demo_data import get_demo_data
from database import load_data, save_data, DEFAULT_TERMS, DEFAULT_DEPARTMENTS
import importer
import exporter
import adjuster

app = Flask(__name__)

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
    'engine': None,          # SchedulingEngine (for view queries after generation)
    'result': None,          # dict from engine.solve()
}

# Load existing data on startup
load_data(app_data)


# ---------------------------------------------------------------------------
# Frontend route
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    """Serve the single-page application."""
    return render_template('index.html')


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
    if request.method == 'GET':
        return jsonify([f.to_dict() for f in app_data['faculty']])
    try:
        data = request.get_json()
        app_data['faculty'].append(Faculty(id=data['id'], name=data['name']))
        save_data(app_data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/faculty/<id>', methods=['DELETE', 'PUT'])
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
@app.route('/api/timetable/master', methods=['GET'])
def get_master_timetable():
    """Return the master timetable as a flat list."""
    engine = app_data.get('engine')
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
    engine = app_data.get('engine')
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
def select_variant(index):
    engine = app_data.get('engine')
    result = app_data.get('result')
    if not engine or not result or result.get('status') not in ('success', 'partial'):
        return jsonify({'error': 'No generated timetable found'}), 400
        
    variants = result.get('variants', [])
    if index < 0 or index >= len(variants):
        return jsonify({'error': 'Invalid variant index'}), 400
        
    engine.load_assignments_data(variants[index]['assignments_data'])
    result['active_variant_index'] = index
    result['assignments'] = engine._format_assignments()
    result['soft_score'] = variants[index].get('soft_score', {})
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
        'published_at': None,
        'term': 'Academic Year 2026-27 (Term 1)'
    }
    return jsonify(pub)


@app.route('/api/timetable/publish', methods=['POST'])
def publish_timetable():
    if not app_data.get('engine') or not app_data.get('result'):
        return jsonify({'error': 'No generated timetable available to publish'}), 400
    from datetime import datetime, timezone
    data = request.get_json(silent=True) or {}
    term = data.get('term', 'Academic Year 2026-27 (Term 1)')
    pub = {
        'status': 'PUBLISHED',
        'published_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'term': term
    }
    app_data['publishing'] = pub
    save_data(app_data)
    return jsonify({'status': 'ok', 'publishing': pub})


def _get_or_restore_engine():
    engine = app_data.get('engine')
    if engine and hasattr(engine, 'assignments') and len(engine.assignments) > 0:
        return engine
    result = app_data.get('result')
    if result and result.get('assignments_data') and app_data.get('config'):
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
    return engine


@app.route('/api/timetable/validate-move', methods=['POST'])
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

    valid, message, details = adjuster.validate_move(
        engine, session_id, target_day, target_start_slot, target_room_id
    )
    return jsonify({
        'valid': valid,
        'message': message,
        'details': details
    })


@app.route('/api/timetable/move', methods=['POST'])
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


@app.route('/api/timetable/swap', methods=['POST'])
def api_execute_swap():
    engine = _get_or_restore_engine()
    if not engine or not app_data.get('result'):
        return jsonify({'status': 'error', 'message': 'No generated timetable found', 'details': {'code': 'NO_TIMETABLE'}}), 400

    data = request.get_json(silent=True) or {}
    session_a_id = data.get('session_a_id')
    session_b_id = data.get('session_b_id')

    if not session_a_id or not session_b_id:
        return jsonify({'status': 'error', 'message': 'Both session_a_id and session_b_id are required'}), 400

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


@app.route('/api/timetable/unpublish', methods=['POST'])
def unpublish_timetable():
    pub = {
        'status': 'DRAFT',
        'published_at': None,
        'term': (app_data.get('publishing') or {}).get('term', 'Academic Year 2026-27 (Term 1)')
    }
    app_data['publishing'] = pub
    save_data(app_data)
    return jsonify({'status': 'ok', 'publishing': pub})


@app.route('/api/generate-multiple', methods=['POST'])
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
            result['active_variant_index'] = 0
            if result['variants']:
                engine.load_assignments_data(result['variants'][0]['assignments_data'])
                result['assignments'] = engine._format_assignments()
                result['soft_score'] = result['variants'][0]['soft_score']
                result['status'] = 'success'
            
        save_data(app_data)
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ---------------------------------------------------------------------------
# Validation API


# ---------------------------------------------------------------------------

@app.route('/api/debug/trace/config', methods=['GET', 'POST'])
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
def validate_current_timetable():
    """Post-generation validation: re-check all hard constraints."""
    engine = app_data.get('engine')
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


# ---------------------------------------------------------------------------
# Demo Data / Clear API
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Excel Import API — REMOVED in v1 (demo data only)
# ---------------------------------------------------------------------------
# Deferred to a future version. Use /api/load-demo or manual entry.


# ---------------------------------------------------------------------------
# Pre-Generate Summary API  (v1 addition)
# ---------------------------------------------------------------------------
@app.route('/api/summary', methods=['GET'])
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
def clear_data():
    """Reset all application state."""
    for key in app_data:
        app_data[key] = None if key in ('config', 'engine', 'result') else []
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
    try:
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
