from flask import Flask, jsonify, request, render_template, send_file
from models import WorkingConfig, Room, Faculty, Section, Batch, Course, RoomType
from time_slots import generate_time_slots
from scheduler import SchedulingEngine
from constraints import validate_timetable
from demo_data import get_demo_data
from database import load_data, save_data
import importer
import exporter

app = Flask(__name__)

# Application data stored in memory (and synced to database.json)
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

trace_config = {'level': 0, 'session_filter': None}
load_data(app_data)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def update_or_delete(entity_list, item_id, new_item=None):
    for i, item in enumerate(entity_list):
        if item.id == item_id:
            if new_item is None:
                entity_list.pop(i)
            else:
                entity_list[i] = new_item
            save_data(app_data)
            return True
    return False


# -----------------------------------------------------------------------------
# 1. Frontend Page
# -----------------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')


# -----------------------------------------------------------------------------
# 2. Timing Configuration API
# -----------------------------------------------------------------------------
@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    if request.method == 'GET':
        return jsonify(app_data['config'].to_dict() if app_data['config'] else None)

    data = request.get_json()
    app_data['config'] = WorkingConfig(
        working_days=data['working_days'],
        start_time=data['start_time'],
        end_time=data['end_time'],
        slot_duration_minutes=int(data.get('slot_duration_minutes', 60)),
        breaks=data.get('breaks', []),
        lunch_start=data['lunch_start'],
        lunch_end=data['lunch_end']
    )
    save_data(app_data)
    return jsonify({'status': 'ok'})


@app.route('/api/time-slots', methods=['GET'])
def get_time_slots():
    if not app_data['config']:
        return jsonify({'error': 'Configuration not set'}), 400
    slots = generate_time_slots(app_data['config'])
    return jsonify([s.to_dict() for s in slots])


# -----------------------------------------------------------------------------
# 3. Rooms API
# -----------------------------------------------------------------------------
@app.route('/api/rooms', methods=['GET', 'POST'])
def rooms_list():
    if request.method == 'GET':
        return jsonify([r.to_dict() for r in app_data['rooms']])

    data = request.get_json()
    room = Room(
        id=data['id'],
        name=data['name'],
        room_type=data['room_type'],
        capacity=int(data['capacity']) if data.get('capacity') else None,
        category=data.get('category') or None
    )
    app_data['rooms'].append(room)
    save_data(app_data)
    return jsonify({'status': 'ok'})


@app.route('/api/rooms/<id>', methods=['PUT', 'DELETE'])
def room_item(id):
    if request.method == 'DELETE':
        update_or_delete(app_data['rooms'], id)
        return jsonify({'status': 'ok'})

    data = request.get_json()
    updated = Room(
        id=data['id'],
        name=data['name'],
        room_type=data['room_type'],
        capacity=int(data['capacity']) if data.get('capacity') else None,
        category=data.get('category') or None
    )
    if update_or_delete(app_data['rooms'], id, updated):
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'Not found'}), 404


# -----------------------------------------------------------------------------
# 4. Faculty API
# -----------------------------------------------------------------------------
@app.route('/api/faculty', methods=['GET', 'POST'])
def faculty_list():
    if request.method == 'GET':
        return jsonify([f.to_dict() for f in app_data['faculty']])

    data = request.get_json()
    app_data['faculty'].append(Faculty(id=data['id'], name=data['name']))
    save_data(app_data)
    return jsonify({'status': 'ok'})


@app.route('/api/faculty/<id>', methods=['PUT', 'DELETE'])
def faculty_item(id):
    if request.method == 'DELETE':
        update_or_delete(app_data['faculty'], id)
        return jsonify({'status': 'ok'})

    data = request.get_json()
    if update_or_delete(app_data['faculty'], id, Faculty(id=data['id'], name=data['name'])):
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'Not found'}), 404


# -----------------------------------------------------------------------------
# 5. Sections & Batches API
# -----------------------------------------------------------------------------
@app.route('/api/sections', methods=['GET', 'POST'])
def sections_list():
    if request.method == 'GET':
        result = []
        for s in app_data['sections']:
            item = s.to_dict()
            item['batches'] = [b.to_dict() for b in app_data['batches'] if b.section_id == s.id]
            result.append(item)
        return jsonify(result)

    data = request.get_json()
    section = Section(
        id=data['id'],
        name=data['name'],
        semester=int(data['semester']),
        division=data['division'],
        strength=int(data['strength']) if data.get('strength') else None
    )
    app_data['sections'].append(section)
    save_data(app_data)
    return jsonify({'status': 'ok'})


@app.route('/api/sections/<id>', methods=['PUT', 'DELETE'])
def section_item(id):
    if request.method == 'DELETE':
        update_or_delete(app_data['sections'], id)
        # Also clean up batches associated with this section
        app_data['batches'] = [b for b in app_data['batches'] if b.section_id != id]
        save_data(app_data)
        return jsonify({'status': 'ok'})

    data = request.get_json()
    updated = Section(
        id=data['id'],
        name=data['name'],
        semester=int(data['semester']),
        division=data['division'],
        strength=int(data['strength']) if data.get('strength') else None
    )
    if update_or_delete(app_data['sections'], id, updated):
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/batches', methods=['GET', 'POST'])
def batches_list():
    if request.method == 'GET':
        return jsonify([b.to_dict() for b in app_data['batches']])

    data = request.get_json()
    batch = Batch(
        id=data['id'],
        name=data['name'],
        section_id=data['section_id'],
        strength=int(data['strength']) if data.get('strength') else None
    )
    app_data['batches'].append(batch)
    save_data(app_data)
    return jsonify({'status': 'ok'})


@app.route('/api/batches/<id>', methods=['PUT', 'DELETE'])
def batch_item(id):
    if request.method == 'DELETE':
        update_or_delete(app_data['batches'], id)
        return jsonify({'status': 'ok'})

    data = request.get_json()
    updated = Batch(
        id=data['id'],
        name=data['name'],
        section_id=data['section_id'],
        strength=int(data['strength']) if data.get('strength') else None
    )
    if update_or_delete(app_data['batches'], id, updated):
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'Not found'}), 404


# -----------------------------------------------------------------------------
# 6. Courses API
# -----------------------------------------------------------------------------
@app.route('/api/courses', methods=['GET', 'POST'])
def courses_list():
    if request.method == 'GET':
        return jsonify([c.to_dict() for c in app_data['courses']])

    data = request.get_json()
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


@app.route('/api/courses/<id>', methods=['PUT', 'DELETE'])
def course_item(id):
    if request.method == 'DELETE':
        update_or_delete(app_data['courses'], id)
        return jsonify({'status': 'ok'})

    data = request.get_json()
    updated = Course(
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
    if update_or_delete(app_data['courses'], id, updated):
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'Not found'}), 404


# -----------------------------------------------------------------------------
# 7. Summary & Diagnostics API
# -----------------------------------------------------------------------------
@app.route('/api/summary', methods=['GET'])
def summary():
    cfg = app_data['config']
    courses = app_data['courses']
    sections = app_data['sections']
    batches = app_data['batches']
    faculty = app_data['faculty']
    rooms = app_data['rooms']

    theory_count = sum(int(c.l) + int(c.t) for c in courses)
    lab_count = sum(len(c.lab_batches) for c in courses if c.lab_batches and c.p > 0)
    total_hours = sum(c.l + c.t + c.p for c in courses)

    slots_per_week = 0
    if cfg:
        slots_per_week = len(generate_time_slots(cfg)) * len(cfg.working_days)

    return jsonify({
        'sections': len(sections),
        'batches': len(batches),
        'faculty': len(faculty),
        'rooms': len(rooms),
        'lab_rooms': len([r for r in rooms if r.room_type == RoomType.LAB]),
        'theory_rooms': len([r for r in rooms if r.room_type == RoomType.THEORY_ROOM]),
        'courses': len(courses),
        'theory_sessions_per_week': theory_count,
        'lab_sessions_per_week': lab_count,
        'total_weekly_session_hours': round(total_hours, 1),
        'available_slots_per_week': slots_per_week,
        'working_days': cfg.working_days if cfg else [],
        'config_set': cfg is not None,
    })


# -----------------------------------------------------------------------------
# 8. Timetable Generation API
# -----------------------------------------------------------------------------
@app.route('/api/generate', methods=['POST'])
def generate():
    if not app_data['config']:
        return jsonify({'error': 'Configuration not set'}), 400
    if not app_data['rooms']:
        return jsonify({'error': 'No rooms defined'}), 400
    if not app_data['courses']:
        return jsonify({'error': 'No courses defined'}), 400

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

    return jsonify(result)


@app.route('/api/generate-multiple', methods=['POST'])
def generate_multiple():
    if not app_data['config'] or not app_data['rooms'] or not app_data['courses']:
        return jsonify({'error': 'Missing configuration, rooms, or courses'}), 400

    data = request.get_json() or {}
    count = int(data.get('count', 5))
    seed = int(data.get('seed', 1000))

    engine = SchedulingEngine(
        config=app_data['config'],
        courses=app_data['courses'],
        rooms=app_data['rooms'],
        faculty_list=app_data['faculty'],
        sections=app_data['sections'],
        batches=app_data['batches']
    )
    result = engine.solve_multiple(requested_count=count, base_seed=seed)
    app_data['engine'] = engine
    app_data['result'] = result

    if 'alternatives' in result:
        result['variants'] = result['alternatives']

    save_data(app_data)
    return jsonify(result)


# -----------------------------------------------------------------------------
# 9. Timetable Views API
# -----------------------------------------------------------------------------
def get_active_engine():
    engine = app_data.get('engine')
    result = app_data.get('result')
    if not engine or not result or result.get('status') not in ('success', 'partial'):
        return None
    return engine


@app.route('/api/timetable/master', methods=['GET'])
def view_master():
    engine = get_active_engine()
    if not engine:
        return jsonify({'error': 'No active timetable'}), 400
    return jsonify(engine._format_assignments())


@app.route('/api/timetable/section/<id>', methods=['GET'])
def view_section(id):
    engine = get_active_engine()
    if not engine:
        return jsonify({'error': 'No active timetable'}), 400
    return jsonify(engine.get_section_view(id))


@app.route('/api/timetable/faculty/<id>', methods=['GET'])
def view_faculty(id):
    engine = get_active_engine()
    if not engine:
        return jsonify({'error': 'No active timetable'}), 400
    return jsonify(engine.get_faculty_view(id))


@app.route('/api/timetable/room/<id>', methods=['GET'])
def view_room(id):
    engine = get_active_engine()
    if not engine:
        return jsonify({'error': 'No active timetable'}), 400
    return jsonify(engine.get_room_view(id))


@app.route('/api/timetable/variant/<int:index>', methods=['POST'])
def select_variant(index):
    result = app_data.get('result')
    engine = app_data.get('engine')
    if not engine or not result:
        return jsonify({'error': 'No timetable available'}), 400

    variants = result.get('variants', [])
    if index < 0 or index >= len(variants):
        return jsonify({'error': 'Invalid index'}), 400

    engine.load_assignments_data(variants[index]['assignments_data'])
    result['active_variant_index'] = index
    return jsonify({'status': 'ok'})


@app.route('/api/timetable/metadata', methods=['GET'])
def view_metadata():
    result = app_data.get('result')
    if not result:
        return jsonify({'error': 'No active timetable'}), 400

    variants = result.get('variants', [])
    active_idx = result.get('active_variant_index', 0)
    score = variants[active_idx]['soft_score'] if variants else {}
    return jsonify({
        'num_variants': len(variants),
        'active_variant_index': active_idx,
        'active_score': score
    })


@app.route('/api/validation', methods=['GET'])
def validate():
    engine = get_active_engine()
    if not engine:
        return jsonify({'error': 'No timetable to validate'}), 400

    val = validate_timetable(
        assignments=list(engine.assignments.values()),
        sessions_by_id=engine.sessions_by_id,
        sections_by_id=engine.sections_by_id,
        faculty_by_id=engine.faculty_by_id,
        rooms_by_id=engine.rooms_by_id,
        config=app_data['config'],
        time_slots=engine.time_slots,
        batches_by_id=engine.batches_by_id
    )
    return jsonify({'valid': val.get('is_valid', True), 'conflicts': val.get('conflicts', [])})


# -----------------------------------------------------------------------------
# 10. Demo Data & State Reset
# -----------------------------------------------------------------------------
@app.route('/api/load-demo', methods=['POST'])
def load_demo():
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
    return jsonify({'status': 'ok', 'message': f'Demo dataset ({scenario}) loaded'})


@app.route('/api/clear', methods=['POST'])
def clear_all():
    for key in app_data:
        app_data[key] = None if key in ('config', 'engine', 'result') else []
    save_data(app_data)
    return jsonify({'status': 'ok'})


# -----------------------------------------------------------------------------
# 11. Excel Import & Export
# -----------------------------------------------------------------------------
@app.route('/api/import/template', methods=['GET'])
def download_template():
    buf = importer.generate_import_template()
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='AutoSchedule_Data_Template.xlsx'
    )


@app.route('/api/import/excel', methods=['POST'])
def import_excel():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'errors': ['No file uploaded']}), 400

    file = request.files['file']
    success, counts, errors, parsed = importer.parse_and_validate_excel(file.read())
    if not success:
        return jsonify({'status': 'error', 'errors': errors}), 400

    app_data['rooms'] = parsed['rooms']
    app_data['faculty'] = parsed['faculty']
    app_data['sections'] = parsed['sections']
    app_data['batches'] = parsed['batches']
    app_data['courses'] = parsed['courses']
    app_data['engine'] = None
    app_data['result'] = None
    save_data(app_data)

    return jsonify({'status': 'ok', 'imported': counts})


@app.route('/api/export/excel', methods=['GET'])
def export_excel():
    try:
        buf = exporter.generate_timetable_excel(app_data)
        return send_file(
            buf,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='AutoSchedule_Master_Timetable.xlsx'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# -----------------------------------------------------------------------------
# 12. Trace Debug Setting (Simple Test Endpoint)
# -----------------------------------------------------------------------------
@app.route('/api/debug/trace/config', methods=['GET', 'POST'])
def trace_debug():
    if request.method == 'GET':
        return jsonify(trace_config)
    data = request.get_json() or {}
    trace_config['level'] = int(data.get('level', 0))
    filter_val = str(data.get('session_filter', '')).strip()
    trace_config['session_filter'] = [x.strip() for x in filter_val.split(',') if x.strip()] if filter_val else None
    return jsonify(trace_config)


if __name__ == '__main__':
    print("Timetable Scheduler Server running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
