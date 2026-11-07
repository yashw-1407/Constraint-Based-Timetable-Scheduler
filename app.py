"""
app.py - Flask web application for the Timetable Scheduling Engine.

Provides web routes for:
  - Configuration, Rooms, Faculty, Sections, Batches, Courses management.
  - Generating conflict-free timetables using CSP backtracking.
  - Timetable views (Master, Section, Faculty, Room).
  - Excel workbook import and starter template download.
  - Demo dataset loading and data clearing.

All data is stored in SQLite (autoschedule.db).
"""

import os
from flask import Flask, jsonify, request, render_template, send_file
from models import WorkingConfig, Room, Faculty, Section, Batch, Course, RoomType
from scheduler import SchedulingEngine, generate_time_slots, validate_timetable
from database import load_data, save_data
from demo_data import get_demo_data
from excel_import import parse_excel, generate_template

app = Flask(__name__)

# Application state in-memory cache (backed by SQLite)
app_data = {
    'config': None,
    'rooms': [],
    'faculty': [],
    'sections': [],
    'batches': [],
    'courses': [],
    'engine': None,
    'result': None,
}

# Load saved state from SQLite on startup
load_data(app_data)


# ---------------------------------------------------------------------------
# Frontend Route
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')


# ---------------------------------------------------------------------------
# Configuration API
# ---------------------------------------------------------------------------
@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    if request.method == 'GET':
        cfg = app_data['config']
        if not cfg:
            return jsonify(None)
        return jsonify({
            'working_days': cfg.working_days,
            'start_time': cfg.start_time,
            'end_time': cfg.end_time,
            'slot_duration_minutes': cfg.slot_duration_minutes,
            'lunch_start': cfg.lunch_start,
            'lunch_end': cfg.lunch_end,
            'breaks': cfg.breaks,
        })

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
        if any(r.id == data['id'] for r in app_data['rooms']):
            return jsonify({'error': f"Room ID '{data['id']}' already exists"}), 400
        room = Room(
            id=data['id'],
            name=data['name'],
            room_type=data.get('room_type', RoomType.THEORY_ROOM),
            capacity=int(data['capacity']) if data.get('capacity') else None,
            category=data.get('category') or None
        )
        app_data['rooms'].append(room)
        save_data(app_data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/rooms/<room_id>', methods=['DELETE', 'PUT'])
def modify_room(room_id):
    if request.method == 'DELETE':
        app_data['rooms'] = [r for r in app_data['rooms'] if r.id != room_id]
        save_data(app_data)
        return jsonify({'status': 'ok'})

    try:
        data = request.get_json()
        for idx, r in enumerate(app_data['rooms']):
            if r.id == room_id:
                app_data['rooms'][idx] = Room(
                    id=room_id,
                    name=data['name'],
                    room_type=data.get('room_type', RoomType.THEORY_ROOM),
                    capacity=int(data['capacity']) if data.get('capacity') else None,
                    category=data.get('category') or None
                )
                save_data(app_data)
                return jsonify({'status': 'ok'})
        return jsonify({'error': 'Room not found'}), 404
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
        if any(f.id == data['id'] for r in app_data['faculty']):
            return jsonify({'error': f"Faculty ID '{data['id']}' already exists"}), 400
        app_data['faculty'].append(Faculty(id=data['id'], name=data['name']))
        save_data(app_data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/faculty/<faculty_id>', methods=['DELETE', 'PUT'])
def modify_faculty(faculty_id):
    if request.method == 'DELETE':
        app_data['faculty'] = [f for f in app_data['faculty'] if f.id != faculty_id]
        save_data(app_data)
        return jsonify({'status': 'ok'})

    try:
        data = request.get_json()
        for idx, f in enumerate(app_data['faculty']):
            if f.id == faculty_id:
                app_data['faculty'][idx] = Faculty(id=faculty_id, name=data['name'])
                save_data(app_data)
                return jsonify({'status': 'ok'})
        return jsonify({'error': 'Faculty not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ---------------------------------------------------------------------------
# Sections API
# ---------------------------------------------------------------------------
@app.route('/api/sections', methods=['GET', 'POST'])
def manage_sections():
    if request.method == 'GET':
        result = []
        for s in app_data['sections']:
            d = s.to_dict()
            d['batches'] = [b.to_dict() for b in app_data['batches'] if b.section_id == s.id]
            result.append(d)
        return jsonify(result)

    try:
        data = request.get_json()
        if any(s.id == data['id'] for s in app_data['sections']):
            return jsonify({'error': f"Section ID '{data['id']}' already exists"}), 400
        section = Section(
            id=data['id'],
            name=data['name'],
            semester=int(data['semester']),
            division=data['division'],
            strength=int(data['strength']) if data.get('strength') else None,
            home_room_id=data.get('home_room_id') or None
        )
        app_data['sections'].append(section)
        save_data(app_data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/sections/<section_id>', methods=['DELETE', 'PUT'])
def modify_section(section_id):
    if request.method == 'DELETE':
        app_data['sections'] = [s for s in app_data['sections'] if s.id != section_id]
        app_data['batches'] = [b for b in app_data['batches'] if b.section_id != section_id]
        app_data['courses'] = [c for c in app_data['courses'] if c.section_id != section_id]
        save_data(app_data)
        return jsonify({'status': 'ok'})

    try:
        data = request.get_json()
        for idx, s in enumerate(app_data['sections']):
            if s.id == section_id:
                app_data['sections'][idx] = Section(
                    id=section_id,
                    name=data['name'],
                    semester=int(data['semester']),
                    division=data['division'],
                    strength=int(data['strength']) if data.get('strength') else None,
                    home_room_id=data.get('home_room_id') or None
                )
                save_data(app_data)
                return jsonify({'status': 'ok'})
        return jsonify({'error': 'Section not found'}), 404
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
        if any(b.id == data['id'] for b in app_data['batches']):
            return jsonify({'error': f"Batch ID '{data['id']}' already exists"}), 400
        batch = Batch(
            id=data['id'],
            name=data['name'],
            section_id=data['section_id'],
            strength=int(data['strength']) if data.get('strength') else None
        )
        app_data['batches'].append(batch)
        save_data(app_data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/batches/<batch_id>', methods=['DELETE', 'PUT'])
def modify_batch(batch_id):
    if request.method == 'DELETE':
        app_data['batches'] = [b for b in app_data['batches'] if b.id != batch_id]
        save_data(app_data)
        return jsonify({'status': 'ok'})

    try:
        data = request.get_json()
        for idx, b in enumerate(app_data['batches']):
            if b.id == batch_id:
                app_data['batches'][idx] = Batch(
                    id=batch_id,
                    name=data['name'],
                    section_id=data['section_id'],
                    strength=int(data['strength']) if data.get('strength') else None
                )
                save_data(app_data)
                return jsonify({'status': 'ok'})
        return jsonify({'error': 'Batch not found'}), 404
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
        if any(c.id == data['id'] for c in app_data['courses']):
            return jsonify({'error': f"Course ID '{data['id']}' already exists"}), 400
        course = Course(
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
            lab_batches=data.get('lab_batches', [])
        )
        app_data['courses'].append(course)
        save_data(app_data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/courses/<course_id>', methods=['DELETE', 'PUT'])
def modify_course(course_id):
    if request.method == 'DELETE':
        app_data['courses'] = [c for c in app_data['courses'] if c.id != course_id]
        save_data(app_data)
        return jsonify({'status': 'ok'})

    try:
        data = request.get_json()
        for idx, c in enumerate(app_data['courses']):
            if c.id == course_id:
                app_data['courses'][idx] = Course(
                    id=course_id,
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
                    lab_batches=data.get('lab_batches', [])
                )
                save_data(app_data)
                return jsonify({'status': 'ok'})
        return jsonify({'error': 'Course not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ---------------------------------------------------------------------------
# Time Slots API
# ---------------------------------------------------------------------------
@app.route('/api/time-slots', methods=['GET'])
def get_time_slots():
    if not app_data['config']:
        return jsonify({'error': 'Configuration not set. Please save config first.'}), 400
    slots = generate_time_slots(app_data['config'])
    return jsonify([s.to_dict() for s in slots])


# ---------------------------------------------------------------------------
# Generate Timetable API
# ---------------------------------------------------------------------------
@app.route('/api/generate', methods=['POST'])
def generate_timetable():
    if not app_data['config']:
        return jsonify({'error': 'Configuration not set'}), 400
    if not app_data['rooms']:
        return jsonify({'error': 'No rooms defined'}), 400
    if not app_data['courses']:
        return jsonify({'error': 'No courses defined'}), 400

    try:
        engine = SchedulingEngine(
            config=app_data['config'],
            courses=app_data['courses'],
            rooms=app_data['rooms'],
            faculty_list=app_data['faculty'],
            sections=app_data['sections'],
            batches=app_data['batches']
        )
        result = engine.solve()
        app_data['engine'] = engine
        app_data['result'] = result

        if result['status'] == 'success':
            save_data(app_data)

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Pre-Generate Summary API
# ---------------------------------------------------------------------------
@app.route('/api/summary', methods=['GET'])
def get_summary():
    cfg = app_data['config']
    courses = app_data['courses']
    sections = app_data['sections']
    batches = app_data['batches']
    faculty = app_data['faculty']
    rooms = app_data['rooms']

    theory_sessions = 0
    lab_sessions = 0
    total_weekly_hours = 0.0

    for c in courses:
        theory_sessions += int(c.l) + int(c.t)
        lb = len(c.lab_batches) if c.lab_batches else 0
        if lb > 0 and c.p > 0:
            lab_sessions += lb
        total_weekly_hours += c.l + c.t + c.p

    slots_per_week = 0
    if cfg:
        slots = generate_time_slots(cfg)
        slots_per_week = len(slots) * len(cfg.working_days)

    return jsonify({
        'sections': len(sections),
        'batches': len(batches),
        'faculty': len(faculty),
        'rooms': len(rooms),
        'lab_rooms': len([r for r in rooms if r.room_type == RoomType.LAB]),
        'theory_rooms': len([r for r in rooms if r.room_type == RoomType.THEORY_ROOM]),
        'courses': len(courses),
        'theory_sessions_per_week': theory_sessions,
        'lab_sessions_per_week': lab_sessions,
        'total_weekly_session_hours': round(total_weekly_hours, 1),
        'available_slots_per_week': slots_per_week,
        'working_days': cfg.working_days if cfg else [],
        'config_set': cfg is not None,
    })


# ---------------------------------------------------------------------------
# Validation API
# ---------------------------------------------------------------------------
@app.route('/api/validation', methods=['GET'])
def validate_current_timetable():
    engine = app_data.get('engine')
    result = app_data.get('result')
    if not engine or not result or result.get('status') not in ('success', 'partial'):
        return jsonify({'error': 'No generated timetable to validate'}), 400

    report = validate_timetable(
        assignments=list(engine.assignments.values()),
        sessions_by_id=engine.sessions_by_id,
        sections_by_id=engine.sections_by_id,
        faculty_by_id=engine.faculty_by_id,
        rooms_by_id=engine.rooms_by_id,
        config=app_data['config'],
        time_slots=engine.time_slots,
        batches_by_id=engine.batches_by_id
    )
    return jsonify({
        'valid': report['is_valid'],
        'conflicts': report['conflicts']
    })


# ---------------------------------------------------------------------------
# Timetable Views API
# ---------------------------------------------------------------------------
@app.route('/api/timetable/master', methods=['GET'])
def get_master_timetable():
    engine = app_data.get('engine')
    result = app_data.get('result')
    if not engine or not result or result.get('status') != 'success':
        return jsonify({'error': 'Timetable not generated yet'}), 400
    return jsonify(engine._format_assignments())


@app.route('/api/timetable/section/<section_id>', methods=['GET'])
def get_section_timetable(section_id):
    engine = app_data.get('engine')
    result = app_data.get('result')
    if not engine or not result or result.get('status') != 'success':
        return jsonify({'error': 'Timetable not generated yet'}), 400
    return jsonify(engine.get_section_view(section_id))


@app.route('/api/timetable/faculty/<faculty_id>', methods=['GET'])
def get_faculty_timetable(faculty_id):
    engine = app_data.get('engine')
    result = app_data.get('result')
    if not engine or not result or result.get('status') != 'success':
        return jsonify({'error': 'Timetable not generated yet'}), 400
    return jsonify(engine.get_faculty_view(faculty_id))


@app.route('/api/timetable/room/<room_id>', methods=['GET'])
def get_room_timetable(room_id):
    engine = app_data.get('engine')
    result = app_data.get('result')
    if not engine or not result or result.get('status') != 'success':
        return jsonify({'error': 'Timetable not generated yet'}), 400
    return jsonify(engine.get_room_view(room_id))


# ---------------------------------------------------------------------------
# Demo Data and Clear API
# ---------------------------------------------------------------------------
@app.route('/api/load-demo', methods=['POST'])
def load_demo():
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
    for key in app_data:
        app_data[key] = None if key in ('config', 'engine', 'result') else []
    save_data(app_data)
    return jsonify({'status': 'ok'})


# ---------------------------------------------------------------------------
# Excel Import & Template API
# ---------------------------------------------------------------------------
@app.route('/api/import-excel', methods=['POST'])
def import_excel():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if not file.filename or not file.filename.endswith('.xlsx'):
        return jsonify({'error': 'Please upload an Excel .xlsx file'}), 400

    temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_upload.xlsx')
    file.save(temp_path)
    try:
        res = parse_excel(temp_path)
        if res.get('status') == 'error':
            return jsonify({'error': 'Validation failed', 'details': res.get('errors')}), 400

        data = res['data']
        if request.args.get('preview') == 'true':
            return jsonify({
                'status': 'ok',
                'counts': {
                    'faculty': len(data['faculty']),
                    'rooms': len(data['rooms']),
                    'sections': len(data['sections']),
                    'batches': len(data['batches']),
                    'courses': len(data['courses'])
                }
            })

        app_data['faculty'] = data['faculty']
        app_data['rooms'] = data['rooms']
        app_data['sections'] = data['sections']
        app_data['batches'] = data['batches']
        app_data['courses'] = data['courses']
        app_data['engine'] = None
        app_data['result'] = None
        save_data(app_data)

        return jsonify({
            'status': 'ok',
            'message': 'Dataset successfully imported and persisted to SQLite',
            'counts': {
                'faculty': len(data['faculty']),
                'rooms': len(data['rooms']),
                'sections': len(data['sections']),
                'batches': len(data['batches']),
                'courses': len(data['courses'])
            }
        })
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.route('/api/download-template', methods=['GET'])
def download_template():
    tmpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'timetable_import_template.xlsx')
    if not os.path.exists(tmpl_path):
        generate_template(tmpl_path, prefill_user_data=True)
    return send_file(tmpl_path, as_attachment=True, download_name='timetable_import_template.xlsx')


# ---------------------------------------------------------------------------
# Server Entry Point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 60)
    print("  Constraint-Based Academic Timetable Scheduler")
    print("  Open http://127.0.0.1:5000 in your browser")
    print("=" * 60)
    app.run(debug=True, port=5000)
