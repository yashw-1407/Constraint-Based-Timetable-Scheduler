"""Database persistence and service layer for AutoSchedule.

Uses SQLite with SQLAlchemy ORM as the primary persistence layer.
Supports PostgreSQL through DATABASE_URL configuration.
Includes Flask-Migrate integration, atomic transactions, password hashing,
and backward-compatible in-memory dataclass translation for scheduler decoupling.
"""

import os
import json
import hashlib
import hmac
import threading
from datetime import datetime, timezone
from contextlib import contextmanager
from flask import has_app_context
from flask_migrate import Migrate

from models import (
    WorkingConfig, Room, Faculty, Section, Batch, Course,
    AcademicTerm, Department, User, UserRole, Assignment
)
from db_models import (
    db, DBAcademicTerm, DBDepartment, DBUser, DBWorkingConfig,
    DBRoom, DBFaculty, DBSection, DBBatch, DBCourse,
    course_faculty, course_lab_batches, DBTimetablePublication,
    DBTimetableAssignment, DBScheduleVersion, DBChangeAlert
)

DB_FILE = 'database.json'
_lock = threading.RLock()
migrate = None
_app = None

@contextmanager
def db_context():
    if not has_app_context() and _app is not None:
        with _app.app_context():
            yield
    else:
        yield

def get_database_uri():
    """Return configured database URI or default SQLite database in project directory."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'autoschedule.db').replace('\\', '/')
    return os.environ.get('DATABASE_URL', f'sqlite:///{db_path}')

def hash_password(password: str, salt: str = None) -> tuple:
    if not salt:
        salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return dk.hex(), salt

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return hmac.compare_digest(dk.hex(), password_hash)

def get_default_users():
    admin_h, admin_s = hash_password('admin123', 'seededsaltadmin1')
    coord_h, coord_s = hash_password('coord123', 'seededsaltcoord1')
    fac_h, fac_s = hash_password('faculty123', 'seededsaltfaculty1')
    student_h, student_s = hash_password('student123', 'seededsaltstudent1')
    return [
        User(id='user_admin', username='admin', password_hash=admin_h, salt=admin_s, role=UserRole.ADMIN, name='System Administrator'),
        User(id='user_coord', username='coordinator', password_hash=coord_h, salt=coord_s, role=UserRole.COORDINATOR, name='Academic Coordinator'),
        User(id='user_faculty', username='faculty', password_hash=fac_h, salt=fac_s, role=UserRole.FACULTY, name='Faculty Member'),
        User(id='user_student', username='student', password_hash=student_h, salt=student_s, role=UserRole.STUDENT, name='Student User')
    ]

DEFAULT_TERMS = [
    AcademicTerm(id='term_2026_fall', name='Fall 2026-27 (Term 1)', academic_year='2026-27', semester_type='ODD', is_active=True),
    AcademicTerm(id='term_2026_spring', name='Spring 2026-27 (Term 2)', academic_year='2026-27', semester_type='EVEN', is_active=False)
]

DEFAULT_DEPARTMENTS = [
    Department(id='dept_cse', name='Computer Science & Engineering', code='CSE'),
    Department(id='dept_ece', name='Electronics & Communication', code='ECE')
]

def init_db(app):
    """Initialize SQLAlchemy, Flask-Migrate, create tables, and seed defaults."""
    global migrate, _app
    _app = app
    app.config.setdefault('SQLALCHEMY_DATABASE_URI', get_database_uri())
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)

    if 'sqlalchemy' not in app.extensions:
        db.init_app(app)
        migrate = Migrate(app, db)

    with app.app_context():
        db.create_all()

        # Seed terms if empty
        if not db.session.query(DBAcademicTerm).first():
            for t in DEFAULT_TERMS:
                db.session.add(DBAcademicTerm(
                    id=t.id,
                    name=t.name,
                    academic_year=t.academic_year,
                    semester_type=t.semester_type,
                    is_active=t.is_active
                ))

        # Seed departments if empty
        if not db.session.query(DBDepartment).first():
            for d in DEFAULT_DEPARTMENTS:
                db.session.add(DBDepartment(id=d.id, name=d.name, code=d.code))

        # Seed users if empty
        if not db.session.query(DBUser).first():
            for u in get_default_users():
                db.session.add(DBUser(
                    id=u.id,
                    username=u.username,
                    password_hash=u.password_hash,
                    salt=u.salt,
                    role=u.role,
                    name=u.name,
                    faculty_id=getattr(u, 'faculty_id', None)
                ))

        db.session.commit()

def load_data(app_data):
    """Load institutional data from database into application memory."""
    with _lock, db_context():
        try:
            # 1. Terms
            db_terms = db.session.query(DBAcademicTerm).all()
            if db_terms:
                app_data['terms'] = [
                    AcademicTerm(
                        id=t.id,
                        name=t.name,
                        academic_year=t.academic_year,
                        semester_type=t.semester_type,
                        is_active=t.is_active
                    ) for t in db_terms
                ]
                active_term = next((t for t in db_terms if t.is_active), db_terms[0])
                app_data['active_term_id'] = active_term.id
            else:
                app_data['terms'] = [t for t in DEFAULT_TERMS]
                app_data['active_term_id'] = 'term_2026_fall'

            active_term_id = app_data.get('active_term_id', 'term_2026_fall')

            # 2. Departments
            db_depts = db.session.query(DBDepartment).all()
            app_data['departments'] = [
                Department(id=d.id, name=d.name, code=d.code) for d in db_depts
            ] if db_depts else [d for d in DEFAULT_DEPARTMENTS]

            # 3. Users
            db_users = db.session.query(DBUser).all()
            app_data['users'] = [
                User(
                    id=u.id,
                    username=u.username,
                    password_hash=u.password_hash,
                    salt=u.salt,
                    role=u.role,
                    name=u.name,
                    faculty_id=getattr(u, 'faculty_id', None)
                ) for u in db_users
            ] if db_users else get_default_users()

            # 4. Working Config
            db_cfg = db.session.query(DBWorkingConfig).filter_by(academic_term_id=active_term_id).first()
            if not db_cfg:
                db_cfg = db.session.query(DBWorkingConfig).first()

            if db_cfg:
                app_data['config'] = WorkingConfig(
                    working_days=json.loads(db_cfg.working_days_json) if db_cfg.working_days_json else [],
                    start_time=db_cfg.start_time,
                    end_time=db_cfg.end_time,
                    slot_duration_minutes=db_cfg.slot_duration_minutes,
                    lunch_start=db_cfg.lunch_start,
                    lunch_end=db_cfg.lunch_end,
                    breaks=json.loads(db_cfg.breaks_json) if db_cfg.breaks_json else []
                )
            else:
                app_data['config'] = None

            # 5. Rooms
            db_rooms = db.session.query(DBRoom).all()
            app_data['rooms'] = [
                Room(
                    id=r.id,
                    name=r.name,
                    room_type=r.room_type,
                    capacity=r.capacity,
                    category=r.category
                ) for r in db_rooms
            ]

            # 6. Faculty
            db_faculty = db.session.query(DBFaculty).all()
            app_data['faculty'] = [
                Faculty(
                    id=f.id,
                    name=f.name,
                    available_days=json.loads(f.available_days_json) if f.available_days_json else None,
                    unavailable_slots=json.loads(f.unavailable_slots_json) if f.unavailable_slots_json else None
                ) for f in db_faculty
            ]

            # 7. Sections
            db_sections = db.session.query(DBSection).all()
            app_data['sections'] = [
                Section(
                    id=s.id,
                    name=s.name,
                    semester=s.semester,
                    division=s.division,
                    strength=s.strength,
                    home_room_id=s.home_room_id
                ) for s in db_sections
            ]

            # 8. Batches
            db_batches = db.session.query(DBBatch).all()
            app_data['batches'] = [
                Batch(
                    id=b.id,
                    name=b.name,
                    section_id=b.section_id,
                    strength=b.strength,
                    home_room_id=b.home_room_id
                ) for b in db_batches
            ]

            # 9. Courses
            db_courses = db.session.query(DBCourse).all()
            loaded_courses = []
            for c in db_courses:
                # Get linked faculty
                lead_fac = [r[0] for r in db.session.query(course_faculty.c.faculty_id).filter_by(course_id=c.id, is_assistant=False).all()]
                asst_fac = [r[0] for r in db.session.query(course_faculty.c.faculty_id).filter_by(course_id=c.id, is_assistant=True).all()]
                batches = [r[0] for r in db.session.query(course_lab_batches.c.batch_id).filter_by(course_id=c.id).all()]

                loaded_courses.append(Course(
                    id=c.id,
                    name=c.name,
                    code=c.code,
                    section_id=c.section_id,
                    l=c.l,
                    t=c.t,
                    p=c.p,
                    faculty_ids=lead_fac,
                    assistant_faculty_ids=asst_fac,
                    room_type=c.room_type,
                    required_room_id=c.required_room_id,
                    lab_batches=batches
                ))
            app_data['courses'] = loaded_courses

            # 10. Publication
            db_pub = db.session.query(DBTimetablePublication).filter_by(academic_term_id=active_term_id).first()
            if db_pub:
                app_data['publishing'] = {
                    'status': db_pub.status,
                    'is_published': db_pub.is_published,
                    'published_at': db_pub.published_at,
                    'term': db_pub.term_name
                }
            else:
                app_data['publishing'] = None

            # 11. Schedule Assignments & Result
            db_assignments = db.session.query(DBTimetableAssignment).filter_by(academic_term_id=active_term_id, variant_index=0).all()
            db_version = db.session.query(DBScheduleVersion).filter_by(academic_term_id=active_term_id).order_by(DBScheduleVersion.id.desc()).first()

            if db_assignments:
                assignments_data = [
                    {
                        'session_id': a.session_id,
                        'day': a.day,
                        'start_slot_index': a.start_slot_index,
                        'room_id': a.room_id
                    } for a in db_assignments
                ]

                result_dict = {}
                if db_version and db_version.result_json:
                    try:
                        result_dict = json.loads(db_version.result_json)
                    except Exception:
                        pass

                result_dict['status'] = result_dict.get('status', 'SUCCESS')
                result_dict['assignments_data'] = assignments_data
                if 'soft_score' not in result_dict and db_version and db_version.soft_score is not None:
                    result_dict['soft_score'] = {'total_score': db_version.soft_score}

                app_data['result'] = result_dict
            elif db_version and db_version.result_json:
                try:
                    app_data['result'] = json.loads(db_version.result_json)
                except Exception:
                    app_data['result'] = None
            else:
                app_data['result'] = None

            # 12. Restore SchedulingEngine
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
            print(f"Error loading from relational database: {e}")
            _load_from_json_fallback(app_data)

def _load_from_json_fallback(app_data):
    """Fallback loader from database.json if database connection fails."""
    if not os.path.exists(DB_FILE):
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
        app_data['terms'] = [AcademicTerm.from_dict(d) for d in data.get('terms', [])]
        app_data['departments'] = [Department.from_dict(d) for d in data.get('departments', [])]
        app_data['active_term_id'] = data.get('active_term_id', 'term_2026_fall')
        app_data['users'] = [User.from_dict(d) for d in data.get('users', [])]
    except Exception as e:
        print(f"Fallback json load error: {e}")

def save_data(app_data):
    """Transactional persistence to relational database and backup JSON."""
    with _lock, db_context():
        try:
            active_term_id = app_data.get('active_term_id', 'term_2026_fall')

            # 1. Academic Terms
            for t in app_data.get('terms', []):
                db_t = db.session.get(DBAcademicTerm, t.id)
                is_act = (t.id == active_term_id) or getattr(t, 'is_active', False)
                if not db_t:
                    db.session.add(DBAcademicTerm(
                        id=t.id, name=t.name, academic_year=t.academic_year,
                        semester_type=getattr(t, 'semester_type', 'ODD'), is_active=is_act
                    ))
                else:
                    db_t.name = t.name
                    db_t.academic_year = t.academic_year
                    db_t.semester_type = getattr(t, 'semester_type', db_t.semester_type)
                    db_t.is_active = is_act

            # 2. Departments
            for d in app_data.get('departments', []):
                db_d = db.session.get(DBDepartment, d.id)
                if not db_d:
                    db.session.add(DBDepartment(id=d.id, name=d.name, code=d.code))
                else:
                    db_d.name = d.name
                    db_d.code = d.code

            # 3. Users
            for u in app_data.get('users', []):
                db_u = db.session.get(DBUser, u.id)
                if not db_u:
                    db.session.add(DBUser(
                        id=u.id, username=u.username, password_hash=u.password_hash,
                        salt=u.salt, role=u.role, name=u.name, faculty_id=getattr(u, 'faculty_id', None)
                    ))
                else:
                    db_u.username = u.username
                    db_u.password_hash = u.password_hash
                    db_u.salt = u.salt
                    db_u.role = u.role
                    db_u.name = u.name
                    db_u.faculty_id = getattr(u, 'faculty_id', None)

            # 4. Working Config
            cfg = app_data.get('config')
            if cfg:
                db_cfg = db.session.query(DBWorkingConfig).filter_by(academic_term_id=active_term_id).first()
                working_days = json.dumps(cfg.working_days)
                breaks = json.dumps(cfg.breaks)
                if not db_cfg:
                    db.session.add(DBWorkingConfig(
                        academic_term_id=active_term_id,
                        working_days_json=working_days,
                        start_time=cfg.start_time,
                        end_time=cfg.end_time,
                        slot_duration_minutes=cfg.slot_duration_minutes,
                        lunch_start=cfg.lunch_start,
                        lunch_end=cfg.lunch_end,
                        breaks_json=breaks
                    ))
                else:
                    db_cfg.working_days_json = working_days
                    db_cfg.start_time = cfg.start_time
                    db_cfg.end_time = cfg.end_time
                    db_cfg.slot_duration_minutes = cfg.slot_duration_minutes
                    db_cfg.lunch_start = cfg.lunch_start
                    db_cfg.lunch_end = cfg.lunch_end
                    db_cfg.breaks_json = breaks

            # 5. Rooms (reconcile)
            current_room_ids = {r.id for r in app_data.get('rooms', [])}
            # Remove rooms no longer present
            for db_r in db.session.query(DBRoom).all():
                if db_r.id not in current_room_ids:
                    db.session.query(DBTimetableAssignment).filter_by(room_id=db_r.id).delete()
                    db.session.delete(db_r)
            for r in app_data.get('rooms', []):
                db_r = db.session.get(DBRoom, r.id)
                if not db_r:
                    db.session.add(DBRoom(
                        id=r.id, name=r.name, room_type=r.room_type,
                        capacity=r.capacity, category=r.category
                    ))
                else:
                    db_r.name = r.name
                    db_r.room_type = r.room_type
                    db_r.capacity = r.capacity
                    db_r.category = r.category

            # 6. Faculty (reconcile)
            current_fac_ids = {f.id for f in app_data.get('faculty', [])}
            for db_f in db.session.query(DBFaculty).all():
                if db_f.id not in current_fac_ids:
                    db.session.delete(db_f)
            for f in app_data.get('faculty', []):
                db_f = db.session.get(DBFaculty, f.id)
                avail_days = json.dumps(f.available_days) if f.available_days is not None else None
                unavail_slots = json.dumps(f.unavailable_slots) if f.unavailable_slots is not None else None
                if not db_f:
                    db.session.add(DBFaculty(
                        id=f.id, name=f.name, available_days_json=avail_days,
                        unavailable_slots_json=unavail_slots
                    ))
                else:
                    db_f.name = f.name
                    db_f.available_days_json = avail_days
                    db_f.unavailable_slots_json = unavail_slots

            # 7. Sections (reconcile)
            current_sec_ids = {s.id for s in app_data.get('sections', [])}
            for db_s in db.session.query(DBSection).all():
                if db_s.id not in current_sec_ids:
                    db.session.delete(db_s)
            for s in app_data.get('sections', []):
                db_s = db.session.get(DBSection, s.id)
                if not db_s:
                    db.session.add(DBSection(
                        id=s.id, name=s.name, semester=s.semester,
                        division=s.division, strength=s.strength,
                        home_room_id=s.home_room_id, academic_term_id=active_term_id
                    ))
                else:
                    db_s.name = s.name
                    db_s.semester = s.semester
                    db_s.division = s.division
                    db_s.strength = s.strength
                    db_s.home_room_id = s.home_room_id
                    db_s.academic_term_id = active_term_id

            # 8. Batches (reconcile)
            current_batch_ids = {b.id for b in app_data.get('batches', [])}
            for db_b in db.session.query(DBBatch).all():
                if db_b.id not in current_batch_ids:
                    db.session.delete(db_b)
            for b in app_data.get('batches', []):
                db_b = db.session.get(DBBatch, b.id)
                if not db_b:
                    db.session.add(DBBatch(
                        id=b.id, name=b.name, section_id=b.section_id,
                        strength=b.strength, home_room_id=b.home_room_id
                    ))
                else:
                    db_b.name = b.name
                    db_b.section_id = b.section_id
                    db_b.strength = b.strength
                    db_b.home_room_id = b.home_room_id

            # 9. Courses (reconcile)
            current_course_ids = {c.id for c in app_data.get('courses', [])}
            for db_c in db.session.query(DBCourse).all():
                if db_c.id not in current_course_ids:
                    db.session.delete(db_c)
            for c in app_data.get('courses', []):
                db_c = db.session.get(DBCourse, c.id)
                if not db_c:
                    db.session.add(DBCourse(
                        id=c.id, name=c.name, code=c.code, section_id=c.section_id,
                        academic_term_id=active_term_id, l=c.l, t=c.t, p=c.p,
                        room_type=c.room_type, required_room_id=c.required_room_id
                    ))
                else:
                    db_c.name = c.name
                    db_c.code = c.code
                    db_c.section_id = c.section_id
                    db_c.academic_term_id = active_term_id
                    db_c.l = c.l
                    db_c.t = c.t
                    db_c.p = c.p
                    db_c.room_type = c.room_type
                    db_c.required_room_id = c.required_room_id

            db.session.flush()

            # Course associations
            for c in app_data.get('courses', []):
                db.session.execute(course_faculty.delete().where(course_faculty.c.course_id == c.id))
                db.session.execute(course_lab_batches.delete().where(course_lab_batches.c.course_id == c.id))
                for f_id in getattr(c, 'faculty_ids', []):
                    if f_id in current_fac_ids:
                        db.session.execute(course_faculty.insert().values(
                            course_id=c.id, faculty_id=f_id, is_assistant=False
                        ))
                for f_id in getattr(c, 'assistant_faculty_ids', []):
                    if f_id in current_fac_ids:
                        db.session.execute(course_faculty.insert().values(
                            course_id=c.id, faculty_id=f_id, is_assistant=True
                        ))
                for b_id in getattr(c, 'lab_batches', []):
                    if b_id in current_batch_ids:
                        db.session.execute(course_lab_batches.insert().values(
                            course_id=c.id, batch_id=b_id
                        ))

            # 10. Publication
            pub = app_data.get('publishing')
            db_pub = db.session.query(DBTimetablePublication).filter_by(academic_term_id=active_term_id).first()
            if pub:
                if not db_pub:
                    db.session.add(DBTimetablePublication(
                        academic_term_id=active_term_id,
                        status=pub.get('status', 'DRAFT'),
                        is_published=pub.get('is_published', False),
                        published_at=pub.get('published_at'),
                        term_name=pub.get('term')
                    ))
                else:
                    db_pub.status = pub.get('status', db_pub.status)
                    db_pub.is_published = pub.get('is_published', db_pub.is_published)
                    db_pub.published_at = pub.get('published_at', db_pub.published_at)
                    db_pub.term_name = pub.get('term', db_pub.term_name)
            elif db_pub:
                db_pub.is_published = False
                db_pub.status = 'DRAFT'

            # 11. Timetable Assignments
            res = app_data.get('result')
            if res and res.get('assignments_data'):
                db.session.query(DBTimetableAssignment).filter_by(academic_term_id=active_term_id).delete()
                for a in res['assignments_data']:
                    session_id = a.get('session_id', '')
                    # Resolve course and section
                    c_id = None
                    s_id = None
                    for course_id in current_course_ids:
                        if session_id.startswith(course_id):
                            c_id = course_id
                            break
                    for section_id in current_sec_ids:
                        if f"_{section_id}_" in session_id or session_id.endswith(f"_{section_id}"):
                            s_id = section_id
                            break

                    db.session.add(DBTimetableAssignment(
                        academic_term_id=active_term_id,
                        session_id=session_id,
                        course_id=c_id,
                        section_id=s_id,
                        day=a.get('day'),
                        start_slot_index=int(a.get('start_slot_index', 0)),
                        duration_slots=int(a.get('duration_slots', 1)),
                        room_id=a.get('room_id'),
                        variant_index=0
                    ))

                # Schedule Version
                soft_score = None
                raw_soft = res.get('soft_score')
                if isinstance(raw_soft, dict):
                    soft_score = float(raw_soft.get('percentage', raw_soft.get('total_score', 0.0)))
                elif isinstance(raw_soft, (int, float)):
                    soft_score = float(raw_soft)

                db.session.add(DBScheduleVersion(
                    academic_term_id=active_term_id,
                    version_tag=datetime.now(timezone.utc).strftime('v%Y%m%d_%H%M%S'),
                    note='Generated or updated schedule',
                    soft_score=soft_score,
                    assignments_json=json.dumps(res['assignments_data']),
                    result_json=json.dumps(res)
                ))
            elif res is None:
                db.session.query(DBTimetableAssignment).filter_by(academic_term_id=active_term_id).delete()

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error persisting to relational database: {e}")

        # Also maintain database.json as backup
        _save_json_backup(app_data)

def _save_json_backup(app_data):
    """Write backup copy to database.json."""
    try:
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
    except Exception as e:
        print(f"JSON backup write error: {e}")

def update_assignment_in_db(academic_term_id: str, session_id: str, day: str, start_slot_index: int, room_id: str):
    """Atomically update an assignment record in the database."""
    with _lock, db_context():
        assignment = db.session.query(DBTimetableAssignment).filter_by(
            academic_term_id=academic_term_id, session_id=session_id
        ).first()
        if assignment:
            assignment.day = day
            assignment.start_slot_index = start_slot_index
            assignment.room_id = room_id
            db.session.commit()
            return True
        return False

def swap_assignments_in_db(academic_term_id: str, session_id_1: str, move_1: dict, session_id_2: str, move_2: dict):
    """Atomically swap two assignments in the database with rollback protection."""
    with _lock, db_context():
        try:
            a1 = db.session.query(DBTimetableAssignment).filter_by(
                academic_term_id=academic_term_id, session_id=session_id_1
            ).first()
            a2 = db.session.query(DBTimetableAssignment).filter_by(
                academic_term_id=academic_term_id, session_id=session_id_2
            ).first()

            if not a1 or not a2:
                return False

            a1.day = move_1['day']
            a1.start_slot_index = move_1['start_slot_index']
            a1.room_id = move_1['room_id']

            a2.day = move_2['day']
            a2.start_slot_index = move_2['start_slot_index']
            a2.room_id = move_2['room_id']

            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e

def get_schedule_versions(academic_term_id: str = None):
    """Retrieve audit history of schedule versions for an academic term."""
    with _lock, db_context():
        query = db.session.query(DBScheduleVersion)
        if academic_term_id:
            query = query.filter_by(academic_term_id=academic_term_id)
        versions = query.order_by(DBScheduleVersion.id.desc()).all()
        
        result = []
        for v in versions:
            assign_count = 0
            if v.assignments_json:
                try:
                    assign_count = len(json.loads(v.assignments_json))
                except Exception:
                    pass
            result.append({
                'id': v.id,
                'academic_term_id': v.academic_term_id,
                'version_tag': v.version_tag,
                'note': v.note,
                'soft_score': v.soft_score,
                'created_by': v.created_by,
                'created_at': v.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if v.created_at else None,
                'assignment_count': assign_count
            })
        return result

def create_schedule_snapshot(academic_term_id: str, version_tag: str, note: str = None, user_id: str = None, app_data: dict = None):
    """Create an immutable named snapshot of current assignments and quality score."""
    with _lock, db_context():
        try:
            res = (app_data or {}).get('result') or {}
            assignments_data = res.get('assignments_data', [])
            if not assignments_data:
                # Query directly from DB
                db_assigns = db.session.query(DBTimetableAssignment).filter_by(
                    academic_term_id=academic_term_id, variant_index=0
                ).all()
                assignments_data = [
                    {
                        'session_id': a.session_id,
                        'day': a.day,
                        'start_slot_index': a.start_slot_index,
                        'room_id': a.room_id
                    } for a in db_assigns
                ]

            soft_score = None
            raw_soft = res.get('soft_score')
            if isinstance(raw_soft, dict):
                soft_score = float(raw_soft.get('percentage', raw_soft.get('total_score', 0.0)))
            elif isinstance(raw_soft, (int, float)):
                soft_score = float(raw_soft)

            snapshot = DBScheduleVersion(
                academic_term_id=academic_term_id,
                version_tag=version_tag,
                note=note,
                soft_score=soft_score,
                created_by=user_id,
                assignments_json=json.dumps(assignments_data),
                result_json=json.dumps(res) if res else None
            )
            db.session.add(snapshot)
            db.session.commit()

            return {
                'id': snapshot.id,
                'academic_term_id': snapshot.academic_term_id,
                'version_tag': snapshot.version_tag,
                'note': snapshot.note,
                'soft_score': snapshot.soft_score,
                'created_at': snapshot.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if snapshot.created_at else None,
                'assignment_count': len(assignments_data)
            }
        except Exception as e:
            db.session.rollback()
            raise e

def restore_schedule_version(version_id: int, app_data: dict):
    """Restore a historical schedule version to active operational assignments."""
    with _lock, db_context():
        try:
            snapshot = db.session.get(DBScheduleVersion, version_id)
            if not snapshot:
                return False, "Schedule version not found."

            academic_term_id = snapshot.academic_term_id
            assignments_data = json.loads(snapshot.assignments_json) if snapshot.assignments_json else []

            # Clear current assignments for this term
            db.session.query(DBTimetableAssignment).filter_by(academic_term_id=academic_term_id).delete()

            # Map current courses and sections
            courses_by_id = {c.id: c for c in app_data.get('courses', [])}
            sections_by_id = {s.id: s for s in app_data.get('sections', [])}

            for a in assignments_data:
                sess_id = a.get('session_id', '')
                c_id = None
                s_id = None
                for cid in courses_by_id:
                    if sess_id.startswith(cid):
                        c_id = cid
                        break
                for sid in sections_by_id:
                    if f"_{sid}_" in sess_id or sess_id.endswith(f"_{sid}"):
                        s_id = sid
                        break

                db.session.add(DBTimetableAssignment(
                    academic_term_id=academic_term_id,
                    session_id=sess_id,
                    course_id=c_id,
                    section_id=s_id,
                    day=a.get('day'),
                    start_slot_index=int(a.get('start_slot_index', 0)),
                    room_id=a.get('room_id'),
                    variant_index=0
                ))

            # Update app_data['result']
            result_dict = {}
            if snapshot.result_json:
                try:
                    result_dict = json.loads(snapshot.result_json)
                except Exception:
                    pass

            result_dict['status'] = 'SUCCESS'
            result_dict['assignments_data'] = assignments_data
            if snapshot.soft_score is not None and 'soft_score' not in result_dict:
                result_dict['soft_score'] = {'total_score': snapshot.soft_score}

            app_data['result'] = result_dict

            # Restore engine
            if app_data.get('config') and app_data.get('courses'):
                try:
                    from scheduler import SchedulingEngine
                    eng = SchedulingEngine(
                        app_data['config'],
                        app_data['courses'],
                        app_data['rooms'],
                        app_data['faculty'],
                        app_data['sections'],
                        app_data.get('batches', [])
                    )
                    eng.load_assignments_data(assignments_data)
                    app_data['engine'] = eng
                    result_dict['assignments'] = eng._format_assignments()
                except Exception as ex:
                    print(f"Warning restoring engine during rollback: {ex}")

            # Mark publishing state as modified / draft
            if app_data.get('publishing'):
                app_data['publishing']['status'] = 'DRAFT'
                app_data['publishing']['modified_after_publish'] = True
                pub = db.session.query(DBTimetablePublication).filter_by(academic_term_id=academic_term_id).first()
                if pub:
                    pub.status = 'DRAFT'

            db.session.commit()
            _save_json_backup(app_data)

            # Record rollback change alert
            record_change_alert(
                academic_term_id=academic_term_id,
                event_type='ROLLBACK',
                session_id=f"version_{snapshot.version_tag}",
                details={'version_tag': snapshot.version_tag, 'restored_assignments': len(assignments_data)}
            )

            return True, f"Successfully restored timetable to version {snapshot.version_tag}."
        except Exception as e:
            db.session.rollback()
            raise e

def record_change_alert(academic_term_id: str, event_type: str, session_id: str, details: dict):
    """Record an operational timetable modification event."""
    with _lock, db_context():
        try:
            alert = DBChangeAlert(
                academic_term_id=academic_term_id,
                event_type=event_type,
                session_id=session_id,
                details_json=json.dumps(details or {})
            )
            db.session.add(alert)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Failed to record change alert: {e}")
            return False

def get_change_alerts(academic_term_id: str = None, limit: int = 50):
    """Retrieve chronologically ordered change alerts for timetable alterations."""
    with _lock, db_context():
        query = db.session.query(DBChangeAlert)
        if academic_term_id:
            query = query.filter_by(academic_term_id=academic_term_id)
        alerts = query.order_by(DBChangeAlert.id.desc()).limit(limit).all()
        result = []
        for a in alerts:
            det = {}
            if a.details_json:
                try:
                    det = json.loads(a.details_json)
                except Exception:
                    pass
            result.append({
                'id': a.id,
                'academic_term_id': a.academic_term_id,
                'event_type': a.event_type,
                'session_id': a.session_id,
                'details': det,
                'created_at': a.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if a.created_at else None
            })
        return result

def clear_change_alerts(academic_term_id: str = None):
    """Clear acknowledged timetable change alerts."""
    with _lock, db_context():
        try:
            query = db.session.query(DBChangeAlert)
            if academic_term_id:
                query = query.filter_by(academic_term_id=academic_term_id)
            query.delete()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False
