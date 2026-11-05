"""
demo_data.py - Demonstration datasets with multiple scenario cases.

Provides ready-to-use academic datasets:
  - 'standard': Balanced 4 sections, 8 faculty, 6 rooms (4 theory + 2 labs).
  - 'bottleneck': Tight resource contention (only 2 theory rooms + 1 lab) showcasing MRV search.
  - 'infeasible': Over-constrained scenario (lab courses exist but 0 lab rooms) demonstrating graceful conflict detection.
  - 'single_section': Minimal 1-section dataset, ideal for stepping through slot-by-slot in viva.
"""

from models import (WorkingConfig, Room, Faculty, Section, Batch, Course,
                    CourseType, RoomType)


def get_demo_data(scenario: str = 'standard') -> dict:
    """Return demonstration dataset by scenario name.

    Scenarios:
      - 'standard': Standard academic workload (4 sections, 60 sessions, 100% placed)
      - 'bottleneck': Highly constrained rooms (2 theory, 1 lab) forcing deep backtracking
      - 'infeasible': Impossible constraints (lab sessions but no lab room)
      - 'single_section': 1 section, minimal demonstration
    """
    config = WorkingConfig(
        working_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
        start_time='09:00',
        end_time='17:00',
        slot_duration_minutes=60,
        breaks=[],
        lunch_start='13:00',
        lunch_end='14:00'
    )

    if scenario == 'single_section':
        rooms = [
            Room(id='R101', name='Room 101', room_type=RoomType.THEORY_ROOM, capacity=70),
            Room(id='LAB6', name='LAB6', room_type=RoomType.LAB, capacity=35, category='CS'),
        ]
        faculty = [
            Faculty(id='F1', name='Dr. Sharma'),
            Faculty(id='F2', name='Prof. Patel'),
            Faculty(id='F3', name='Dr. Gupta'),
            Faculty(id='F4', name='Prof. Singh'),
        ]
        sections = [
            Section(id='3A', name='3A', semester=3, division='A', strength=70),
        ]
        batches = [
            Batch(id='A1', name='A1', section_id='3A', strength=35),
            Batch(id='A2', name='A2', section_id='3A', strength=35),
        ]
        courses = [
            Course(id='CS301_3A', name='Data Structures', code='CS301', section_id='3A',
                   l=4, t=0, p=2, faculty_ids=['F1'], room_type=RoomType.THEORY_ROOM, lab_batches=['A1']),
            Course(id='CS302_3A', name='Digital Logic', code='CS302', section_id='3A',
                   l=3, t=0, p=2, faculty_ids=['F2'], room_type=RoomType.THEORY_ROOM, lab_batches=['A2']),
            Course(id='CS303_3A', name='Discrete Mathematics', code='CS303', section_id='3A',
                   l=3, t=0, p=0, faculty_ids=['F3'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),
            Course(id='CS304_3A', name='Computer Organization', code='CS304', section_id='3A',
                   l=3, t=0, p=0, faculty_ids=['F4'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),
        ]
        return {'config': config, 'rooms': rooms, 'faculty': faculty, 'sections': sections, 'batches': batches, 'courses': courses}

    if scenario == 'bottleneck':
        # High contention: only 2 theory rooms and 1 lab room for 4 sections!
        rooms = [
            Room(id='R101', name='Room 101', room_type=RoomType.THEORY_ROOM, capacity=70),
            Room(id='R102', name='Room 102', room_type=RoomType.THEORY_ROOM, capacity=70),
            Room(id='LAB6', name='LAB6', room_type=RoomType.LAB, capacity=35, category='CS'),
        ]
        faculty = [
            Faculty(id='F1', name='Dr. Sharma'),
            Faculty(id='F2', name='Prof. Patel'),
            Faculty(id='F3', name='Dr. Gupta'),
            Faculty(id='F4', name='Prof. Singh'),
            Faculty(id='F5', name='Dr. Kumar'),
            Faculty(id='F6', name='Prof. Verma'),
        ]
        sections = [
            Section(id='3A', name='3A', semester=3, division='A', strength=70),
            Section(id='3B', name='3B', semester=3, division='B', strength=70),
        ]
        batches = [
            Batch(id='A1', name='A1', section_id='3A', strength=35),
            Batch(id='A2', name='A2', section_id='3A', strength=35),
            Batch(id='B1', name='B1', section_id='3B', strength=35),
            Batch(id='B2', name='B2', section_id='3B', strength=35),
        ]
        courses = [
            Course(id='CS301_3A', name='Data Structures', code='CS301', section_id='3A',
                   l=4, t=0, p=2, faculty_ids=['F1'], room_type=RoomType.THEORY_ROOM, lab_batches=['A1']),
            Course(id='CS302_3A', name='Digital Logic', code='CS302', section_id='3A',
                   l=3, t=0, p=2, faculty_ids=['F2'], room_type=RoomType.THEORY_ROOM, lab_batches=['A2']),
            Course(id='CS303_3A', name='Discrete Mathematics', code='CS303', section_id='3A',
                   l=3, t=0, p=0, faculty_ids=['F3'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),
            Course(id='CS304_3A', name='Computer Organization', code='CS304', section_id='3A',
                   l=3, t=0, p=0, faculty_ids=['F4'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),
            Course(id='CS301_3B', name='Data Structures', code='CS301', section_id='3B',
                   l=4, t=0, p=2, faculty_ids=['F1', 'F5'], room_type=RoomType.THEORY_ROOM, lab_batches=['B1']),
            Course(id='CS302_3B', name='Digital Logic', code='CS302', section_id='3B',
                   l=3, t=0, p=2, faculty_ids=['F5', 'F2'], room_type=RoomType.THEORY_ROOM, lab_batches=['B2']),
            Course(id='CS303_3B', name='Discrete Mathematics', code='CS303', section_id='3B',
                   l=3, t=0, p=0, faculty_ids=['F3'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),
            Course(id='CS304_3B', name='Computer Organization', code='CS304', section_id='3B',
                   l=3, t=0, p=0, faculty_ids=['F6'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),
        ]
        return {'config': config, 'rooms': rooms, 'faculty': faculty, 'sections': sections, 'batches': batches, 'courses': courses}

    if scenario == 'infeasible':
        # Zero lab rooms defined, but lab courses require lab rooms!
        rooms = [
            Room(id='R101', name='Room 101', room_type=RoomType.THEORY_ROOM, capacity=70),
            Room(id='R102', name='Room 102', room_type=RoomType.THEORY_ROOM, capacity=70),
        ]
        faculty = [
            Faculty(id='F1', name='Dr. Sharma'),
            Faculty(id='F2', name='Prof. Patel'),
        ]
        sections = [
            Section(id='3A', name='3A', semester=3, division='A', strength=70),
        ]
        batches = [
            Batch(id='A1', name='A1', section_id='3A', strength=35),
        ]
        courses = [
            # Requires LAB room, but no LAB room exists!
            Course(id='CS301_3A', name='Data Structures Lab Only', code='CS301', section_id='3A',
                   l=0, t=0, p=2, faculty_ids=['F1'], room_type=RoomType.THEORY_ROOM, lab_batches=['A1']),
        ]
        return {'config': config, 'rooms': rooms, 'faculty': faculty, 'sections': sections, 'batches': batches, 'courses': courses}

    # Default 'standard' scenario
    rooms = [
        Room(id='R101', name='Room 101', room_type=RoomType.THEORY_ROOM, capacity=70),
        Room(id='R102', name='Room 102', room_type=RoomType.THEORY_ROOM, capacity=70),
        Room(id='R103', name='Room 103', room_type=RoomType.THEORY_ROOM, capacity=70),
        Room(id='R104', name='Room 104', room_type=RoomType.THEORY_ROOM, capacity=70),
        Room(id='LAB6', name='LAB6', room_type=RoomType.LAB, capacity=35, category='CS'),
        Room(id='LHC201_L', name='LHC201_L', room_type=RoomType.LAB, capacity=35, category='CS'),
    ]

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

    sections = [
        Section(id='3A', name='3A', semester=3, division='A', strength=70),
        Section(id='3B', name='3B', semester=3, division='B', strength=70),
        Section(id='5A', name='5A', semester=5, division='A', strength=60),
        Section(id='5B', name='5B', semester=5, division='B', strength=60),
    ]

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

    courses = [
        Course(id='CS301_3A', name='Data Structures', code='CS301', section_id='3A',
               l=4, t=0, p=2, faculty_ids=['F1'], room_type=RoomType.THEORY_ROOM, lab_batches=['A1']),
        Course(id='CS302_3A', name='Digital Logic', code='CS302', section_id='3A',
               l=3, t=0, p=2, faculty_ids=['F2'], room_type=RoomType.THEORY_ROOM, lab_batches=['A2']),
        Course(id='CS303_3A', name='Discrete Mathematics', code='CS303', section_id='3A',
               l=3, t=0, p=0, faculty_ids=['F3'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),
        Course(id='CS304_3A', name='Computer Organization', code='CS304', section_id='3A',
               l=3, t=0, p=0, faculty_ids=['F4'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),

        Course(id='CS301_3B', name='Data Structures', code='CS301', section_id='3B',
               l=4, t=0, p=2, faculty_ids=['F1', 'F5'], room_type=RoomType.THEORY_ROOM, lab_batches=['B1']),
        Course(id='CS302_3B', name='Digital Logic', code='CS302', section_id='3B',
               l=3, t=0, p=2, faculty_ids=['F5', 'F3'], room_type=RoomType.THEORY_ROOM, lab_batches=['B2']),
        Course(id='CS303_3B', name='Discrete Mathematics', code='CS303', section_id='3B',
               l=3, t=0, p=0, faculty_ids=['F3'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),
        Course(id='CS304_3B', name='Computer Organization', code='CS304', section_id='3B',
               l=3, t=0, p=0, faculty_ids=['F4'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),

        Course(id='CS501_5A', name='Design & Analysis of Algorithms', code='CS501', section_id='5A',
               l=4, t=0, p=2, faculty_ids=['F6'], room_type=RoomType.THEORY_ROOM, lab_batches=['5A1']),
        Course(id='CS502_5A', name='Operating Systems', code='CS502', section_id='5A',
               l=3, t=0, p=0, faculty_ids=['F7'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),
        Course(id='CS503_5A', name='Database Management', code='CS503', section_id='5A',
               l=3, t=0, p=2, faculty_ids=['F2', 'F8'], room_type=RoomType.THEORY_ROOM, lab_batches=['5A2']),
        Course(id='CS504_5A', name='Computer Networks', code='CS504', section_id='5A',
               l=3, t=0, p=0, faculty_ids=['F8'], room_type=RoomType.THEORY_ROOM, lab_batches=[]),

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
