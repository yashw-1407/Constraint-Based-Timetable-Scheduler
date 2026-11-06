"""SQLAlchemy ORM models for AutoSchedule.

Normalized relational schema supporting SQLite and PostgreSQL.
Includes users, academic terms, departments, rooms, faculty,
sections, batches, courses, timetable assignments, publications,
and schedule versions.
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, Table, Index, event
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import relationship

def get_utc_now():
    return datetime.now(timezone.utc)

db = SQLAlchemy()

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints on SQLite connections."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    except Exception:
        pass
    finally:
        cursor.close()


# Association Table: Course <-> Faculty (supports multiple faculty per course)
course_faculty = Table(
    'course_faculty',
    db.metadata,
    Column('course_id', String(64), ForeignKey('courses.id', ondelete='CASCADE'), primary_key=True),
    Column('faculty_id', String(64), ForeignKey('faculty.id', ondelete='CASCADE'), primary_key=True),
    Column('is_assistant', Boolean, default=False, nullable=False),
    Index('idx_cf_faculty', 'faculty_id')
)

# Association Table: Course <-> Batch (for practical lab batches)
course_lab_batches = Table(
    'course_lab_batches',
    db.metadata,
    Column('course_id', String(64), ForeignKey('courses.id', ondelete='CASCADE'), primary_key=True),
    Column('batch_id', String(64), ForeignKey('batches.id', ondelete='CASCADE'), primary_key=True),
    Index('idx_clb_batch', 'batch_id')
)


class DBAcademicTerm(db.Model):
    __tablename__ = 'academic_terms'

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    academic_year = Column(String(32), nullable=False)
    semester_type = Column(String(16), default='ODD', nullable=False)
    is_active = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    working_config = relationship('DBWorkingConfig', back_populates='term', uselist=False, cascade='all, delete-orphan')
    sections = relationship('DBSection', back_populates='term', cascade='all, delete-orphan')
    courses = relationship('DBCourse', back_populates='term', cascade='all, delete-orphan')
    publications = relationship('DBTimetablePublication', back_populates='term', cascade='all, delete-orphan')
    assignments = relationship('DBTimetableAssignment', back_populates='term', cascade='all, delete-orphan')
    schedule_versions = relationship('DBScheduleVersion', back_populates='term', cascade='all, delete-orphan')


class DBDepartment(db.Model):
    __tablename__ = 'departments'

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    code = Column(String(32), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    rooms = relationship('DBRoom', back_populates='department')
    faculty = relationship('DBFaculty', back_populates='department')
    sections = relationship('DBSection', back_populates='department')


class DBUser(db.Model):
    __tablename__ = 'users'

    id = Column(String(64), primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    salt = Column(String(64), nullable=False)
    role = Column(String(32), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    faculty_id = Column(String(64), ForeignKey('faculty.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)


class DBWorkingConfig(db.Model):
    __tablename__ = 'working_configs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_term_id = Column(String(64), ForeignKey('academic_terms.id', ondelete='CASCADE'), nullable=True, index=True)
    working_days_json = Column(Text, nullable=False)
    start_time = Column(String(16), nullable=False, default="09:00")
    end_time = Column(String(16), nullable=False, default="17:00")
    slot_duration_minutes = Column(Integer, nullable=False, default=60)
    lunch_start = Column(String(16), nullable=False, default="13:00")
    lunch_end = Column(String(16), nullable=False, default="14:00")
    breaks_json = Column(Text, nullable=False, default="[]")
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    term = relationship('DBAcademicTerm', back_populates='working_config')


class DBRoom(db.Model):
    __tablename__ = 'rooms'

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    room_type = Column(String(32), nullable=False, index=True)
    capacity = Column(Integer, nullable=True)
    category = Column(String(64), nullable=True)
    department_id = Column(String(64), ForeignKey('departments.id', ondelete='SET NULL'), nullable=True, index=True)

    department = relationship('DBDepartment', back_populates='rooms')
    assignments = relationship('DBTimetableAssignment', back_populates='room', cascade='all, delete-orphan', passive_deletes=True)


class DBFaculty(db.Model):
    __tablename__ = 'faculty'

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    department_id = Column(String(64), ForeignKey('departments.id', ondelete='SET NULL'), nullable=True, index=True)
    available_days_json = Column(Text, nullable=True)
    unavailable_slots_json = Column(Text, nullable=True)

    department = relationship('DBDepartment', back_populates='faculty')
    courses = relationship('DBCourse', secondary=course_faculty, back_populates='faculty_members')


class DBSection(db.Model):
    __tablename__ = 'sections'

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    semester = Column(Integer, nullable=False, index=True)
    division = Column(String(16), nullable=False)
    strength = Column(Integer, nullable=True)
    department_id = Column(String(64), ForeignKey('departments.id', ondelete='SET NULL'), nullable=True, index=True)
    home_room_id = Column(String(64), ForeignKey('rooms.id', ondelete='SET NULL'), nullable=True)
    academic_term_id = Column(String(64), ForeignKey('academic_terms.id', ondelete='CASCADE'), nullable=True, index=True)

    department = relationship('DBDepartment', back_populates='sections')
    home_room = relationship('DBRoom')
    term = relationship('DBAcademicTerm', back_populates='sections')
    batches = relationship('DBBatch', back_populates='section', cascade='all, delete-orphan')
    courses = relationship('DBCourse', back_populates='section', cascade='all, delete-orphan')


class DBBatch(db.Model):
    __tablename__ = 'batches'

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    section_id = Column(String(64), ForeignKey('sections.id', ondelete='CASCADE'), nullable=False, index=True)
    strength = Column(Integer, nullable=True)
    home_room_id = Column(String(64), ForeignKey('rooms.id', ondelete='SET NULL'), nullable=True)

    section = relationship('DBSection', back_populates='batches')
    home_room = relationship('DBRoom')


class DBCourse(db.Model):
    __tablename__ = 'courses'

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    code = Column(String(32), nullable=False, index=True)
    section_id = Column(String(64), ForeignKey('sections.id', ondelete='CASCADE'), nullable=False, index=True)
    academic_term_id = Column(String(64), ForeignKey('academic_terms.id', ondelete='CASCADE'), nullable=True, index=True)
    department_id = Column(String(64), ForeignKey('departments.id', ondelete='SET NULL'), nullable=True, index=True)
    l = Column(Float, nullable=False, default=3.0)
    t = Column(Float, nullable=False, default=0.0)
    p = Column(Float, nullable=False, default=0.0)
    room_type = Column(String(32), default='THEORY_ROOM', nullable=False)
    required_room_id = Column(String(64), ForeignKey('rooms.id', ondelete='SET NULL'), nullable=True)

    section = relationship('DBSection', back_populates='courses')
    term = relationship('DBAcademicTerm', back_populates='courses')
    required_room = relationship('DBRoom')
    faculty_members = relationship('DBFaculty', secondary=course_faculty, back_populates='courses')
    lab_batches = relationship('DBBatch', secondary=course_lab_batches)


class DBTimetablePublication(db.Model):
    __tablename__ = 'timetable_publications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_term_id = Column(String(64), ForeignKey('academic_terms.id', ondelete='CASCADE'), nullable=True, index=True)
    status = Column(String(32), default='DRAFT', nullable=False)
    is_published = Column(Boolean, default=False, nullable=False, index=True)
    published_at = Column(String(64), nullable=True)
    term_name = Column(String(128), nullable=True)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    term = relationship('DBAcademicTerm', back_populates='publications')


class DBTimetableAssignment(db.Model):
    __tablename__ = 'timetable_assignments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_term_id = Column(String(64), ForeignKey('academic_terms.id', ondelete='CASCADE'), nullable=True, index=True)
    session_id = Column(String(128), nullable=False, index=True)
    course_id = Column(String(64), ForeignKey('courses.id', ondelete='SET NULL'), nullable=True, index=True)
    section_id = Column(String(64), ForeignKey('sections.id', ondelete='SET NULL'), nullable=True, index=True)
    batch_id = Column(String(64), ForeignKey('batches.id', ondelete='SET NULL'), nullable=True, index=True)
    faculty_id = Column(String(64), ForeignKey('faculty.id', ondelete='SET NULL'), nullable=True, index=True)
    faculty_ids_json = Column(Text, nullable=True)
    day = Column(String(32), nullable=False, index=True)
    start_slot_index = Column(Integer, nullable=False, index=True)
    duration_slots = Column(Integer, default=1, nullable=False)
    room_id = Column(String(64), ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False, index=True)
    variant_index = Column(Integer, default=0, nullable=False, index=True)

    room = relationship('DBRoom', back_populates='assignments')
    course = relationship('DBCourse')
    section = relationship('DBSection')
    batch = relationship('DBBatch')
    term = relationship('DBAcademicTerm', back_populates='assignments')

    __table_args__ = (
        Index('idx_assign_term_day_slot_room', 'academic_term_id', 'day', 'start_slot_index', 'room_id'),
        Index('idx_assign_term_section_day_slot', 'academic_term_id', 'section_id', 'day', 'start_slot_index'),
    )


class DBScheduleVersion(db.Model):
    __tablename__ = 'schedule_versions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_term_id = Column(String(64), ForeignKey('academic_terms.id', ondelete='CASCADE'), nullable=True, index=True)
    version_tag = Column(String(64), nullable=False)
    note = Column(Text, nullable=True)
    soft_score = Column(Float, nullable=True)
    created_by = Column(String(64), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    assignments_json = Column(Text, nullable=False)
    result_json = Column(Text, nullable=True)

    term = relationship('DBAcademicTerm', back_populates='schedule_versions')


class DBChangeAlert(db.Model):
    __tablename__ = 'change_alerts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_term_id = Column(String(64), ForeignKey('academic_terms.id', ondelete='CASCADE'), nullable=True, index=True)
    event_type = Column(String(32), nullable=False, index=True)  # 'MOVE', 'SWAP', 'ROLLBACK'
    session_id = Column(String(128), nullable=False)
    details_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    term = relationship('DBAcademicTerm')
