"""
demo_data.py - Default demonstration dataset with batch-wise lab scheduling.

Provides a ready-to-use dataset for 4 sections (3A, 3B, 5A, 5B) across
semesters 3 and 5. Each section is divided into two lab batches.

Demonstrates:
  - Batch-wise lab scheduling (A1/A2 may run simultaneously in different labs)
  - Faculty conflict avoidance (shared faculty across sections)
  - Section-level theory scheduling
  - Room capacity checked against batch strength (not section strength) for labs
  - Lab consecutive-period scheduling
"""

from models import (WorkingConfig, Room, Faculty, Section, Batch, Course,
                    CourseType, RoomType)


def get_demo_data() -> dict:
    """Return a complete demo dataset ready for scheduling.

    Returns:
        Dictionary with keys: config, rooms, faculty, sections, batches, courses.
    """

    # --- Time Configuration ---
    # Working hours 09:00-17:00, lunch 13:00-14:00, no extra breaks
    # This produces 7 slots/day:
    #   09:00-10:00, 10:00-11:00, 11:00-12:00, 12:00-13:00,
    #   14:00-15:00, 15:00-16:00, 16:00-17:00
    # = 35 total slots per week
    config = WorkingConfig(
        working_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
        start_time='09:00',
        end_time='17:00',
        slot_duration_minutes=60,
        breaks=[],
        lunch_start='13:00',
        lunch_end='14:00'
    )

    # --- Rooms ---
    # 4 theory rooms (capacity 70 each, fits full sections)
    # 2 labs (capacity 35 each, fits one batch)
    rooms = [
        Room(id='R101', name='Room 101', room_type=RoomType.THEORY_ROOM, capacity=70),
        Room(id='R102', name='Room 102', room_type=RoomType.THEORY_ROOM, capacity=70),
        Room(id='R103', name='Room 103', room_type=RoomType.THEORY_ROOM, capacity=70),
        Room(id='R104', name='Room 104', room_type=RoomType.THEORY_ROOM, capacity=70),
        Room(id='LAB6', name='LAB6', room_type=RoomType.LAB, capacity=35, category='CS'),
        Room(id='LHC201_L', name='LHC201_L', room_type=RoomType.LAB, capacity=35, category='CS'),
    ]

    # --- Faculty ---
    # 8 faculty members, some shared across sections to create constraints
    faculty = [
        Faculty(id='F1', name='Dr. Sharma'),
        Faculty(id='F2', name='Prof. Patel'),
        Faculty(id='F3', name='Dr. Gupta'),
        Faculty(id='F4', name='Prof. Singh'),
        Faculty(id='F5', name='Dr. Kumar'),
        Faculty(id='F6', name='Prof. Verma'),
        Faculty(id='F7', name='Dr. Joshi'),
        Faculty(id='F8', name='Prof. Mehta'),
    ]

    # --- Sections ---
    # Section strength = full class size (used for theory room capacity check)
    sections = [
        Section(id='3A', name='3A', semester=3, division='A', strength=70),
        Section(id='3B', name='3B', semester=3, division='B', strength=70),
        Section(id='5A', name='5A', semester=5, division='A', strength=60),
        Section(id='5B', name='5B', semester=5, division='B', strength=60),
    ]

    # --- Batches ---
    # Each section is divided into 2 lab batches.
    # Batch strength must be <= lab room capacity (35) for scheduling.
    batches = [
        Batch(id='A1', name='A1', section_id='3A', strength=35),
        Batch(id='A2', name='A2', section_id='3A', strength=35),
        Batch(id='B1', name='B1', section_id='3B', strength=35),
        Batch(id='B2', name='B2', section_id='3B', strength=35),
        Batch(id='5A1', name='5A1', section_id='5A', strength=30),
        Batch(id='5A2', name='5A2', section_id='5A', strength=30),
        Batch(id='5B1', name='5B1', section_id='5B', strength=30),
        Batch(id='5B2', name='5B2', section_id='5B', strength=30),
    ]

    # --- Courses ---
    courses = [
        # ---- Semester 3, Section A ----
        Course(id='CS301_3A', name='Data Structures', code='CS301', section_id='3A',
               l=4, t=0, p=2, faculty_ids=['F1'], room_type=RoomType.THEORY_ROOM, lab_batches=['A1']),
        
        Course(id='CS302_3A', name='Digital Logic', code='CS302', section_id='3A',
               l=3, t=0, p=2, faculty_ids=['F2'], room_type=RoomType.THEORY_ROOM, lab_batches=['A2']),
        
        Course(id='CS303_3A', name='Discrete Mathematics', code='CS303', section_id='3A',
               l=3, t=0, p=0, faculty_ids=['F3'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),
        
        Course(id='CS304_3A', name='Computer Organization', code='CS304', section_id='3A',
               l=3, t=0, p=0, faculty_ids=['F4'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),

        # ---- Semester 3, Section B ----
        Course(id='CS301_3B', name='Data Structures', code='CS301', section_id='3B',
               l=4, t=0, p=2, faculty_ids=['F1', 'F5'], room_type=RoomType.THEORY_ROOM, lab_batches=['B1']),
               
        Course(id='CS302_3B', name='Digital Logic', code='CS302', section_id='3B',
               l=3, t=0, p=2, faculty_ids=['F5', 'F3'], room_type=RoomType.THEORY_ROOM, lab_batches=['B2']),
               
        Course(id='CS303_3B', name='Discrete Mathematics', code='CS303', section_id='3B',
               l=3, t=0, p=0, faculty_ids=['F3'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),
               
        Course(id='CS304_3B', name='Computer Organization', code='CS304', section_id='3B',
               l=3, t=0, p=0, faculty_ids=['F4'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),

        # ---- Semester 5, Section A ----
        Course(id='CS501_5A', name='Design & Analysis of Algorithms', code='CS501', section_id='5A',
               l=4, t=0, p=2, faculty_ids=['F6'], room_type=RoomType.THEORY_ROOM, lab_batches=['5A1']),
               
        Course(id='CS502_5A', name='Operating Systems', code='CS502', section_id='5A',
               l=3, t=0, p=0, faculty_ids=['F7'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),
               
        Course(id='CS503_5A', name='Database Management', code='CS503', section_id='5A',
               l=3, t=0, p=2, faculty_ids=['F2', 'F8'], room_type=RoomType.THEORY_ROOM, lab_batches=['5A2']),
               
        Course(id='CS504_5A', name='Computer Networks', code='CS504', section_id='5A',
               l=3, t=0, p=0, faculty_ids=['F8'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),

        # ---- Semester 5, Section B ----
        Course(id='CS501_5B', name='Design & Analysis of Algorithms', code='CS501', section_id='5B',
               l=4, t=0, p=2, faculty_ids=['F6', 'F7'], room_type=RoomType.THEORY_ROOM, lab_batches=['5B1']),
               
        Course(id='CS502_5B', name='Operating Systems', code='CS502', section_id='5B',
               l=3, t=0, p=0, faculty_ids=['F7'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),
               
        Course(id='CS503_5B', name='Database Management', code='CS503', section_id='5B',
               l=3, t=0, p=2, faculty_ids=['F2', 'F5'], room_type=RoomType.THEORY_ROOM, lab_batches=['5B2']),
               
        Course(id='CS504_5B', name='Computer Networks', code='CS504', section_id='5B',
               l=3, t=0, p=0, faculty_ids=['F8'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),
    ]

    return {
        'config': config,
        'rooms': rooms,
        'faculty': faculty,
        'sections': sections,
        'batches': batches,
        'courses': courses,
    }
