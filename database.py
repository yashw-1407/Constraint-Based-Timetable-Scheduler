"""
database.py - SQLite relational persistence layer for AutoSchedule.

Replaces JSON storage with SQLite.
Stores working configuration, rooms, faculty, sections, batches, courses,
and generated timetable assignments using normalized relational tables.
"""

import os
import sqlite3
import threading
from typing import Dict, Any, Optional
from models import WorkingConfig, Room, Faculty, Section, Batch, Course, RoomType

DB_FILE = os.environ.get(
    'DB_FILE',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'autoschedule.db')
)
_lock = threading.RLock()


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create and return a configured SQLite connection."""
    path = db_path or DB_FILE
    conn = sqlite3.connect(path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize SQLite database tables if they do not exist."""
    with _lock:
        conn = get_connection(db_path)
        try:
            with conn:
                conn.executescript("""
                CREATE TABLE IF NOT EXISTS config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    slot_duration_minutes INTEGER NOT NULL,
                    lunch_start TEXT NOT NULL,
                    lunch_end TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS config_working_days (
                    day_order INTEGER PRIMARY KEY,
                    day_name TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS config_breaks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    break_order INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rooms (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    room_type TEXT NOT NULL,
                    capacity INTEGER,
                    category TEXT
                );

                CREATE TABLE IF NOT EXISTS faculty (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sections (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    semester INTEGER NOT NULL,
                    division TEXT NOT NULL,
                    strength INTEGER,
                    home_room_id TEXT
                );

                CREATE TABLE IF NOT EXISTS batches (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    section_id TEXT NOT NULL,
                    strength INTEGER,
                    home_room_id TEXT,
                    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS courses (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    code TEXT NOT NULL,
                    section_id TEXT NOT NULL,
                    l REAL NOT NULL DEFAULT 0.0,
                    t REAL NOT NULL DEFAULT 0.0,
                    p REAL NOT NULL DEFAULT 0.0,
                    room_type TEXT NOT NULL DEFAULT 'THEORY_ROOM',
                    required_room_id TEXT,
                    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS course_faculty (
                    course_id TEXT NOT NULL,
                    faculty_id TEXT NOT NULL,
                    faculty_order INTEGER NOT NULL DEFAULT 0,
                    is_assistant INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (course_id, faculty_id, is_assistant),
                    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS course_lab_batches (
                    course_id TEXT NOT NULL,
                    batch_id TEXT NOT NULL,
                    batch_order INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (course_id, batch_id),
                    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                    FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS timetable_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    day TEXT NOT NULL,
                    start_slot_index INTEGER NOT NULL,
                    room_id TEXT NOT NULL,
                    course_name TEXT,
                    course_code TEXT,
                    section_name TEXT,
                    faculty_name TEXT,
                    room_name TEXT,
                    time_start TEXT,
                    time_end TEXT,
                    batch_name TEXT
                );

                CREATE TABLE IF NOT EXISTS timetable_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                """)
        finally:
            conn.close()


def save_data(app_data: Dict[str, Any], db_path: Optional[str] = None) -> None:
    """Transactional save of all entities from app_data to SQLite."""
    init_db(db_path)
    with _lock:
        conn = get_connection(db_path)
        try:
            with conn:
                cur = conn.cursor()
                # Clean existing records in child-first order to satisfy FKs
                cur.execute("DELETE FROM course_faculty")
                cur.execute("DELETE FROM course_lab_batches")
                cur.execute("DELETE FROM courses")
                cur.execute("DELETE FROM batches")
                cur.execute("DELETE FROM sections")
                cur.execute("DELETE FROM faculty")
                cur.execute("DELETE FROM rooms")
                cur.execute("DELETE FROM config_breaks")
                cur.execute("DELETE FROM config_working_days")
                cur.execute("DELETE FROM config")
                cur.execute("DELETE FROM timetable_assignments")
                cur.execute("DELETE FROM timetable_metadata")

                # Insert Config
                cfg = app_data.get('config')
                if cfg:
                    cur.execute(
                        """
                        INSERT INTO config (id, start_time, end_time, slot_duration_minutes, lunch_start, lunch_end)
                        VALUES (1, ?, ?, ?, ?, ?)
                        """,
                        (cfg.start_time, cfg.end_time, int(cfg.slot_duration_minutes), cfg.lunch_start, cfg.lunch_end)
                    )
                    for idx, day in enumerate(cfg.working_days):
                        cur.execute("INSERT INTO config_working_days (day_order, day_name) VALUES (?, ?)", (idx, day))
                    for idx, brk in enumerate(cfg.breaks or []):
                        cur.execute(
                            "INSERT INTO config_breaks (break_order, start_time, end_time) VALUES (?, ?, ?)",
                            (idx, brk['start_time'], brk['end_time'])
                        )

                # Insert Rooms
                for r in app_data.get('rooms', []):
                    cur.execute(
                        "INSERT INTO rooms (id, name, room_type, capacity, category) VALUES (?, ?, ?, ?, ?)",
                        (r.id, r.name, r.room_type, r.capacity, r.category)
                    )

                # Insert Faculty
                for f in app_data.get('faculty', []):
                    cur.execute("INSERT INTO faculty (id, name) VALUES (?, ?)", (f.id, f.name))

                # Insert Sections
                for s in app_data.get('sections', []):
                    cur.execute(
                        "INSERT INTO sections (id, name, semester, division, strength, home_room_id) VALUES (?, ?, ?, ?, ?, ?)",
                        (s.id, s.name, int(s.semester), s.division, s.strength, s.home_room_id)
                    )

                # Insert Batches
                for b in app_data.get('batches', []):
                    cur.execute(
                        "INSERT INTO batches (id, name, section_id, strength, home_room_id) VALUES (?, ?, ?, ?, ?)",
                        (b.id, b.name, b.section_id, b.strength, b.home_room_id)
                    )

                # Insert Courses and child links
                for c in app_data.get('courses', []):
                    cur.execute(
                        """
                        INSERT INTO courses (id, name, code, section_id, l, t, p, room_type, required_room_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (c.id, c.name, c.code, c.section_id, float(c.l), float(c.t), float(c.p), c.room_type, c.required_room_id)
                    )
                    for f_idx, fid in enumerate(c.faculty_ids or []):
                        cur.execute(
                            "INSERT OR IGNORE INTO course_faculty (course_id, faculty_id, faculty_order, is_assistant) VALUES (?, ?, ?, 0)",
                            (c.id, fid, f_idx)
                        )
                    for f_idx, fid in enumerate(c.assistant_faculty_ids or []):
                        cur.execute(
                            "INSERT OR IGNORE INTO course_faculty (course_id, faculty_id, faculty_order, is_assistant) VALUES (?, ?, ?, 1)",
                            (c.id, fid, f_idx)
                        )
                    for b_idx, bid in enumerate(c.lab_batches or []):
                        cur.execute(
                            "INSERT OR IGNORE INTO course_lab_batches (course_id, batch_id, batch_order) VALUES (?, ?, ?)",
                            (c.id, bid, b_idx)
                        )

                # Insert Timetable Assignments & Metadata (if generated result is present)
                result = app_data.get('result')
                if result and isinstance(result, dict):
                    status = result.get('status')
                    cur.execute("INSERT OR REPLACE INTO timetable_metadata (key, value) VALUES ('status', ?)", (str(status),))
                    assignments = result.get('assignments', [])
                    for a in assignments:
                        cur.execute(
                            """
                            INSERT INTO timetable_assignments
                            (session_id, day, start_slot_index, room_id, course_name, course_code, section_name, faculty_name, room_name, time_start, time_end, batch_name)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                a.get('session_id', ''),
                                a.get('day', ''),
                                int(a.get('slot_index', a.get('start_slot_index', 0))),
                                a.get('room_id', ''),
                                a.get('course_name', ''),
                                a.get('course_code', ''),
                                a.get('section_name', ''),
                                a.get('faculty_name', ''),
                                a.get('room_name', ''),
                                a.get('time_start', ''),
                                a.get('time_end', ''),
                                a.get('batch_name', '')
                            )
                        )
        finally:
            conn.close()


def load_data(app_data: Dict[str, Any], db_path: Optional[str] = None) -> None:
    """Load configuration, rooms, faculty, sections, batches, courses from SQLite into app_data."""
    init_db(db_path)
    with _lock:
        conn = get_connection(db_path)
        try:
            cur = conn.cursor()

            # 1. Config
            cur.execute("SELECT start_time, end_time, slot_duration_minutes, lunch_start, lunch_end FROM config WHERE id = 1")
            cfg_row = cur.fetchone()
            if cfg_row:
                cur.execute("SELECT day_name FROM config_working_days ORDER BY day_order ASC")
                days = [r[0] for r in cur.fetchall()]
                cur.execute("SELECT start_time, end_time FROM config_breaks ORDER BY break_order ASC")
                breaks = [{'start_time': r[0], 'end_time': r[1]} for r in cur.fetchall()]
                app_data['config'] = WorkingConfig(
                    working_days=days,
                    start_time=cfg_row[0],
                    end_time=cfg_row[1],
                    slot_duration_minutes=int(cfg_row[2]),
                    breaks=breaks,
                    lunch_start=cfg_row[3],
                    lunch_end=cfg_row[4]
                )
            else:
                app_data['config'] = None

            # 2. Rooms
            cur.execute("SELECT id, name, room_type, capacity, category FROM rooms ORDER BY id")
            app_data['rooms'] = [
                Room(
                    id=r[0],
                    name=r[1],
                    room_type=r[2],
                    capacity=r[3],
                    category=r[4]
                ) for r in cur.fetchall()
            ]

            # 3. Faculty
            cur.execute("SELECT id, name FROM faculty ORDER BY id")
            app_data['faculty'] = [
                Faculty(id=r[0], name=r[1]) for r in cur.fetchall()
            ]

            # 4. Sections
            cur.execute("SELECT id, name, semester, division, strength, home_room_id FROM sections ORDER BY id")
            app_data['sections'] = [
                Section(
                    id=r[0],
                    name=r[1],
                    semester=int(r[2]),
                    division=r[3],
                    strength=r[4],
                    home_room_id=r[5]
                ) for r in cur.fetchall()
            ]

            # 5. Batches
            cur.execute("SELECT id, name, section_id, strength, home_room_id FROM batches ORDER BY id")
            app_data['batches'] = [
                Batch(
                    id=r[0],
                    name=r[1],
                    section_id=r[2],
                    strength=r[3],
                    home_room_id=r[4]
                ) for r in cur.fetchall()
            ]

            # 6. Courses
            cur.execute("SELECT id, name, code, section_id, l, t, p, room_type, required_room_id FROM courses ORDER BY id")
            course_rows = cur.fetchall()
            courses = []
            for r in course_rows:
                cid = r[0]
                cur.execute("SELECT faculty_id FROM course_faculty WHERE course_id = ? AND is_assistant = 0 ORDER BY faculty_order ASC", (cid,))
                fac_ids = [row[0] for row in cur.fetchall()]
                cur.execute("SELECT faculty_id FROM course_faculty WHERE course_id = ? AND is_assistant = 1 ORDER BY faculty_order ASC", (cid,))
                asst_fac_ids = [row[0] for row in cur.fetchall()]
                cur.execute("SELECT batch_id FROM course_lab_batches WHERE course_id = ? ORDER BY batch_order ASC", (cid,))
                lab_batches = [row[0] for row in cur.fetchall()]

                courses.append(Course(
                    id=r[0],
                    name=r[1],
                    code=r[2],
                    section_id=r[3],
                    l=float(r[4]),
                    t=float(r[5]),
                    p=float(r[6]),
                    faculty_ids=fac_ids,
                    assistant_faculty_ids=asst_fac_ids,
                    room_type=r[7] or RoomType.THEORY_ROOM,
                    required_room_id=r[8],
                    lab_batches=lab_batches
                ))
            app_data['courses'] = courses
        finally:
            conn.close()
