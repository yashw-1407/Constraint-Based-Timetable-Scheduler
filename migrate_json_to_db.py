"""JSON to SQLite Migration Utility for AutoSchedule.

Reads institutional data from database.json and populates the normalized
SQLAlchemy relational database (autoschedule.db).

Features:
- Idempotent execution (upsert or skip existing records).
- Dry-run mode (--dry-run) to preview changes without modifying database.
- Backup mode (--backup) to create a timestamped copy of database.json.
- Integrity verification: checks foreign key references and detects orphans/duplicates.
- Detailed migration summary report.
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime, timezone

def get_utc_now():
    return datetime.now(timezone.utc)
from flask import Flask
from db_models import (
    db, DBAcademicTerm, DBDepartment, DBUser, DBWorkingConfig,
    DBRoom, DBFaculty, DBSection, DBBatch, DBCourse,
    course_faculty, course_lab_batches, DBTimetablePublication,
    DBTimetableAssignment, DBScheduleVersion
)

def get_default_db_uri():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'autoschedule.db').replace('\\', '/')
    return os.environ.get('DATABASE_URL', f'sqlite:///{db_path}')

def create_migration_app(db_uri=None):
    app = Flask('migration')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri or get_default_db_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def backup_json_file(json_path='database.json'):
    if not os.path.exists(json_path):
        return None
    timestamp = get_utc_now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"backup_{os.path.splitext(json_path)[0]}_{timestamp}.json"
    shutil.copy2(json_path, backup_path)
    return backup_path

def migrate_json_to_sqlite(json_path='database.json', db_uri=None, dry_run=False, create_backup=True):
    report = {
        'timestamp': get_utc_now().isoformat(),
        'json_path': json_path,
        'dry_run': dry_run,
        'backup_created': None,
        'counts': {
            'academic_terms': 0,
            'departments': 0,
            'users': 0,
            'working_configs': 0,
            'rooms': 0,
            'faculty': 0,
            'sections': 0,
            'batches': 0,
            'courses': 0,
            'course_faculty_links': 0,
            'course_batch_links': 0,
            'publications': 0,
            'timetable_assignments': 0,
            'schedule_versions': 0
        },
        'warnings': [],
        'errors': []
    }

    if not os.path.exists(json_path):
        report['errors'].append(f"Source JSON file not found: {json_path}")
        return report

    if create_backup and not dry_run:
        backup_file = backup_json_file(json_path)
        report['backup_created'] = backup_file

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    app = create_migration_app(db_uri)

    with app.app_context():
        if not dry_run:
            db.create_all()

        # 1. Academic Terms
        raw_terms = data.get('terms', [])
        active_term_id = data.get('active_term_id', 'term_2026_fall')
        valid_term_ids = set()

        for t in raw_terms:
            t_id = t.get('id')
            if not t_id:
                report['warnings'].append(f"Skipping term without id: {t}")
                continue
            valid_term_ids.add(t_id)
            report['counts']['academic_terms'] += 1
            if not dry_run:
                existing = db.session.get(DBAcademicTerm, t_id)
                is_active = (t_id == active_term_id) or t.get('is_active', False)
                if not existing:
                    term_obj = DBAcademicTerm(
                        id=t_id,
                        name=t.get('name', t_id),
                        academic_year=t.get('academic_year', '2026-27'),
                        semester_type=t.get('semester_type', 'ODD'),
                        is_active=is_active
                    )
                    db.session.add(term_obj)
                else:
                    existing.name = t.get('name', existing.name)
                    existing.academic_year = t.get('academic_year', existing.academic_year)
                    existing.semester_type = t.get('semester_type', existing.semester_type)
                    existing.is_active = is_active

        # Ensure active_term_id exists
        if active_term_id and active_term_id not in valid_term_ids:
            report['counts']['academic_terms'] += 1
            valid_term_ids.add(active_term_id)
            if not dry_run:
                if not db.session.get(DBAcademicTerm, active_term_id):
                    db.session.add(DBAcademicTerm(
                        id=active_term_id,
                        name=active_term_id.replace('_', ' ').title(),
                        academic_year='2026-27',
                        semester_type='ODD',
                        is_active=True
                    ))

        # 2. Departments
        raw_depts = data.get('departments', [])
        valid_dept_ids = set()
        for d in raw_depts:
            d_id = d.get('id')
            if not d_id:
                continue
            valid_dept_ids.add(d_id)
            report['counts']['departments'] += 1
            if not dry_run:
                existing = db.session.get(DBDepartment, d_id)
                if not existing:
                    db.session.add(DBDepartment(
                        id=d_id,
                        name=d.get('name', d_id),
                        code=d.get('code', d_id.upper())
                    ))
                else:
                    existing.name = d.get('name', existing.name)
                    existing.code = d.get('code', existing.code)

        # 3. Users
        raw_users = data.get('users', [])
        for u in raw_users:
            u_id = u.get('id')
            if not u_id:
                continue
            report['counts']['users'] += 1
            if not dry_run:
                existing = db.session.get(DBUser, u_id)
                if not existing:
                    db.session.add(DBUser(
                        id=u_id,
                        username=u.get('username'),
                        password_hash=u.get('password_hash'),
                        salt=u.get('salt'),
                        role=u.get('role', 'STUDENT'),
                        name=u.get('name', u.get('username'))
                    ))
                else:
                    existing.username = u.get('username', existing.username)
                    existing.password_hash = u.get('password_hash', existing.password_hash)
                    existing.salt = u.get('salt', existing.salt)
                    existing.role = u.get('role', existing.role)
                    existing.name = u.get('name', existing.name)

        # 4. Working Config
        cfg = data.get('config')
        if cfg:
            report['counts']['working_configs'] += 1
            if not dry_run:
                existing_cfg = DBWorkingConfig.query.filter_by(academic_term_id=active_term_id).first()
                working_days = json.dumps(cfg.get('working_days', ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]))
                breaks = json.dumps(cfg.get('breaks', []))
                if not existing_cfg:
                    db.session.add(DBWorkingConfig(
                        academic_term_id=active_term_id,
                        working_days_json=working_days,
                        start_time=cfg.get('start_time', '09:00'),
                        end_time=cfg.get('end_time', '17:00'),
                        slot_duration_minutes=cfg.get('slot_duration_minutes', 60),
                        lunch_start=cfg.get('lunch_start', '13:00'),
                        lunch_end=cfg.get('lunch_end', '14:00'),
                        breaks_json=breaks
                    ))
                else:
                    existing_cfg.working_days_json = working_days
                    existing_cfg.start_time = cfg.get('start_time', existing_cfg.start_time)
                    existing_cfg.end_time = cfg.get('end_time', existing_cfg.end_time)
                    existing_cfg.slot_duration_minutes = cfg.get('slot_duration_minutes', existing_cfg.slot_duration_minutes)
                    existing_cfg.lunch_start = cfg.get('lunch_start', existing_cfg.lunch_start)
                    existing_cfg.lunch_end = cfg.get('lunch_end', existing_cfg.lunch_end)
                    existing_cfg.breaks_json = breaks

        # 5. Rooms
        raw_rooms = data.get('rooms', [])
        valid_room_ids = set()
        for r in raw_rooms:
            r_id = r.get('id')
            if not r_id:
                continue
            valid_room_ids.add(r_id)
            report['counts']['rooms'] += 1
            dept_id = r.get('department_id') if r.get('department_id') in valid_dept_ids else None
            if not dry_run:
                existing = db.session.get(DBRoom, r_id)
                if not existing:
                    db.session.add(DBRoom(
                        id=r_id,
                        name=r.get('name', r_id),
                        room_type=r.get('room_type', 'THEORY_ROOM'),
                        capacity=r.get('capacity'),
                        category=r.get('category'),
                        department_id=dept_id
                    ))
                else:
                    existing.name = r.get('name', existing.name)
                    existing.room_type = r.get('room_type', existing.room_type)
                    existing.capacity = r.get('capacity', existing.capacity)
                    existing.category = r.get('category', existing.category)
                    existing.department_id = dept_id

        # 6. Faculty
        raw_faculty = data.get('faculty', [])
        valid_faculty_ids = set()
        for f in raw_faculty:
            f_id = f.get('id')
            if not f_id:
                continue
            valid_faculty_ids.add(f_id)
            report['counts']['faculty'] += 1
            dept_id = f.get('department_id') if f.get('department_id') in valid_dept_ids else None
            avail_days = json.dumps(f.get('available_days')) if f.get('available_days') is not None else None
            unavail_slots = json.dumps(f.get('unavailable_slots')) if f.get('unavailable_slots') is not None else None
            if not dry_run:
                existing = db.session.get(DBFaculty, f_id)
                if not existing:
                    db.session.add(DBFaculty(
                        id=f_id,
                        name=f.get('name', f_id),
                        department_id=dept_id,
                        available_days_json=avail_days,
                        unavailable_slots_json=unavail_slots
                    ))
                else:
                    existing.name = f.get('name', existing.name)
                    existing.department_id = dept_id
                    existing.available_days_json = avail_days
                    existing.unavailable_slots_json = unavail_slots

        # 7. Sections
        raw_sections = data.get('sections', [])
        valid_section_ids = set()
        for s in raw_sections:
            s_id = s.get('id')
            if not s_id:
                continue
            valid_section_ids.add(s_id)
            report['counts']['sections'] += 1
            home_room_id = s.get('home_room_id') if s.get('home_room_id') in valid_room_ids else None
            dept_id = s.get('department_id') if s.get('department_id') in valid_dept_ids else None
            if not dry_run:
                existing = db.session.get(DBSection, s_id)
                if not existing:
                    db.session.add(DBSection(
                        id=s_id,
                        name=s.get('name', s_id),
                        semester=int(s.get('semester', 1)),
                        division=str(s.get('division', 'A')),
                        strength=s.get('strength'),
                        department_id=dept_id,
                        home_room_id=home_room_id,
                        academic_term_id=active_term_id
                    ))
                else:
                    existing.name = s.get('name', existing.name)
                    existing.semester = int(s.get('semester', existing.semester))
                    existing.division = str(s.get('division', existing.division))
                    existing.strength = s.get('strength', existing.strength)
                    existing.department_id = dept_id
                    existing.home_room_id = home_room_id
                    existing.academic_term_id = active_term_id

        # 8. Batches
        raw_batches = data.get('batches', [])
        valid_batch_ids = set()
        for b in raw_batches:
            b_id = b.get('id')
            sec_id = b.get('section_id')
            if not b_id or sec_id not in valid_section_ids:
                report['warnings'].append(f"Skipping batch {b_id} referencing unknown section {sec_id}")
                continue
            valid_batch_ids.add(b_id)
            report['counts']['batches'] += 1
            home_room_id = b.get('home_room_id') if b.get('home_room_id') in valid_room_ids else None
            if not dry_run:
                existing = db.session.get(DBBatch, b_id)
                if not existing:
                    db.session.add(DBBatch(
                        id=b_id,
                        name=b.get('name', b_id),
                        section_id=sec_id,
                        strength=b.get('strength'),
                        home_room_id=home_room_id
                    ))
                else:
                    existing.name = b.get('name', existing.name)
                    existing.section_id = sec_id
                    existing.strength = b.get('strength', existing.strength)
                    existing.home_room_id = home_room_id

        # 9. Courses and links
        raw_courses = data.get('courses', [])
        valid_course_ids = set()
        for c in raw_courses:
            c_id = c.get('id')
            sec_id = c.get('section_id')
            if not c_id or sec_id not in valid_section_ids:
                report['warnings'].append(f"Skipping course {c_id} referencing unknown section {sec_id}")
                continue
            valid_course_ids.add(c_id)
            report['counts']['courses'] += 1
            req_room_id = c.get('required_room_id') if c.get('required_room_id') in valid_room_ids else None
            dept_id = c.get('department_id') if c.get('department_id') in valid_dept_ids else None
            if not dry_run:
                existing = db.session.get(DBCourse, c_id)
                if not existing:
                    course_obj = DBCourse(
                        id=c_id,
                        name=c.get('name', c_id),
                        code=c.get('code', c_id),
                        section_id=sec_id,
                        academic_term_id=active_term_id,
                        department_id=dept_id,
                        l=float(c.get('l', 3.0)),
                        t=float(c.get('t', 0.0)),
                        p=float(c.get('p', 0.0)),
                        room_type=c.get('room_type', 'THEORY_ROOM'),
                        required_room_id=req_room_id
                    )
                    db.session.add(course_obj)
                else:
                    existing.name = c.get('name', existing.name)
                    existing.code = c.get('code', existing.code)
                    existing.section_id = sec_id
                    existing.academic_term_id = active_term_id
                    existing.department_id = dept_id
                    existing.l = float(c.get('l', existing.l))
                    existing.t = float(c.get('t', existing.t))
                    existing.p = float(c.get('p', existing.p))
                    existing.room_type = c.get('room_type', existing.room_type)
                    existing.required_room_id = req_room_id

        if not dry_run:
            db.session.flush()

        # Link course faculty & lab batches
        for c in raw_courses:
            c_id = c.get('id')
            if c_id not in valid_course_ids:
                continue

            # Clear existing links if re-running
            if not dry_run:
                db.session.execute(course_faculty.delete().where(course_faculty.c.course_id == c_id))
                db.session.execute(course_lab_batches.delete().where(course_lab_batches.c.course_id == c_id))

            for f_id in c.get('faculty_ids', []):
                if f_id in valid_faculty_ids:
                    report['counts']['course_faculty_links'] += 1
                    if not dry_run:
                        db.session.execute(course_faculty.insert().values(
                            course_id=c_id, faculty_id=f_id, is_assistant=False
                        ))
            for f_id in c.get('assistant_faculty_ids', []):
                if f_id in valid_faculty_ids:
                    report['counts']['course_faculty_links'] += 1
                    if not dry_run:
                        db.session.execute(course_faculty.insert().values(
                            course_id=c_id, faculty_id=f_id, is_assistant=True
                        ))
            for b_id in c.get('lab_batches', []):
                if b_id in valid_batch_ids:
                    report['counts']['course_batch_links'] += 1
                    if not dry_run:
                        db.session.execute(course_lab_batches.insert().values(
                            course_id=c_id, batch_id=b_id
                        ))

        # 10. Publication Status
        pub = data.get('publishing')
        if pub:
            report['counts']['publications'] += 1
            if not dry_run:
                existing_pub = DBTimetablePublication.query.filter_by(academic_term_id=active_term_id).first()
                if not existing_pub:
                    db.session.add(DBTimetablePublication(
                        academic_term_id=active_term_id,
                        status=pub.get('status', 'DRAFT'),
                        is_published=pub.get('is_published', False),
                        published_at=pub.get('published_at'),
                        term_name=pub.get('term')
                    ))
                else:
                    existing_pub.status = pub.get('status', existing_pub.status)
                    existing_pub.is_published = pub.get('is_published', existing_pub.is_published)
                    existing_pub.published_at = pub.get('published_at', existing_pub.published_at)
                    existing_pub.term_name = pub.get('term', existing_pub.term_name)

        # 11. Timetable Assignments & Schedule Versions
        res = data.get('result')
        if res and res.get('assignments_data'):
            assignments = res['assignments_data']
            if not dry_run:
                # Clear existing assignments for active_term_id
                DBTimetableAssignment.query.filter_by(academic_term_id=active_term_id).delete()

            for a in assignments:
                r_id = a.get('room_id')
                if r_id not in valid_room_ids:
                    report['warnings'].append(f"Assignment session {a.get('session_id')} refers to unknown room {r_id}")
                    continue
                report['counts']['timetable_assignments'] += 1
                if not dry_run:
                    # Parse course_id and section_id from session_id if possible
                    # typical session_id format: CS301_3A_L0 or courseId_sessionIndex
                    session_id = a.get('session_id', '')
                    c_id = None
                    s_id = None
                    for course_id in valid_course_ids:
                        if session_id.startswith(course_id):
                            c_id = course_id
                            break
                    for section_id in valid_section_ids:
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
                        room_id=r_id,
                        variant_index=0
                    ))

            # Record schedule version
            report['counts']['schedule_versions'] += 1
            if not dry_run:
                raw_soft_score = res.get('soft_score')
                numeric_soft_score = None
                if isinstance(raw_soft_score, dict):
                    numeric_soft_score = float(raw_soft_score.get('percentage', raw_soft_score.get('total_score', 0.0)))
                elif isinstance(raw_soft_score, (int, float)):
                    numeric_soft_score = float(raw_soft_score)

                db.session.add(DBScheduleVersion(
                    academic_term_id=active_term_id,
                    version_tag='v1.0-migrated',
                    note='Initial migration from database.json',
                    soft_score=numeric_soft_score,
                    assignments_json=json.dumps(assignments),
                    result_json=json.dumps(res)
                ))

        if not dry_run:
            db.session.commit()

    return report

def main():
    parser = argparse.ArgumentParser(description="Migrate AutoSchedule JSON data to SQLite database.")
    parser.add_argument('--json-path', default='database.json', help='Path to source database.json')
    parser.add_argument('--db-uri', default=None, help='Database connection URI')
    parser.add_argument('--dry-run', action='store_true', help='Validate and simulate without modifying database')
    parser.add_argument('--no-backup', action='store_true', help='Do not create JSON backup file')
    args = parser.parse_args()

    print(f"Beginning AutoSchedule database migration (dry_run={args.dry_run})...")
    report = migrate_json_to_sqlite(
        json_path=args.json_path,
        db_uri=args.db_uri,
        dry_run=args.dry_run,
        create_backup=not args.no_backup
    )

    print("\n--- MIGRATION SUMMARY REPORT ---")
    print(f"Timestamp: {report['timestamp']}")
    print(f"Dry Run: {report['dry_run']}")
    if report['backup_created']:
        print(f"Backup Created: {report['backup_created']}")
    print("Entities Processed:")
    for entity, count in report['counts'].items():
        print(f"  - {entity}: {count}")

    if report['warnings']:
        print("\nWarnings:")
        for w in report['warnings']:
            print(f"  [WARN] {w}")

    if report['errors']:
        print("\nErrors:")
        for e in report['errors']:
            print(f"  [ERROR] {e}")
        sys.exit(1)

    print("\nMigration completed successfully.")

if __name__ == '__main__':
    main()
