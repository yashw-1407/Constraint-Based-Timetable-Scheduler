"""
demo_data.py - Demonstration datasets for test cases in the UI.

Cases:
  - 'standard': Balanced 4 sections, 8 faculty, 6 rooms (4 theory + 2 labs).
  - 'bottleneck': Tight resource contention (2 theory rooms, 1 lab).
  - 'infeasible': Over-constrained (lab courses exist but 0 lab rooms).
  - 'single_section': Minimal single section dataset for quick walkthrough.
"""

from models import WorkingConfig, Room, Faculty, Section, Batch, Course, RoomType


def get_demo_data(scenario: str = 'standard') -> dict:
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
            Room(id='LAB1', name='Computer Lab 1', room_type=RoomType.LAB, capacity=35, category='CS'),
        ]
        faculty = [
            Faculty(id='F1', name='Dr. Sharma'),
            Faculty(id='F2', name='Prof. Patel'),
            Faculty(id='F3', name='Dr. Gupta'),
            Faculty(id='F4', name='Prof. Singh'),
        ]
        sections = [
            Section(id='3A', name='3A', semester=3, division='A', strength=60),
        ]
        batches = [
            Batch(id='A1', name='A1', section_id='3A', strength=30),
            Batch(id='A2', name='A2', section_id='3A', strength=30),
        ]
        courses = [
            Course(id='CS301_3A', name='Data Structures', code='CS301', section_id='3A',
                   l=3, t=0, p=0, faculty_ids=['F1']),
            Course(id='CS302_3A', name='DBMS', code='CS302', section_id='3A',
                   l=3, t=0, p=0, faculty_ids=['F2']),
            Course(id='CS303_3A', name='Operating Systems', code='CS303', section_id='3A',
                   l=3, t=0, p=0, faculty_ids=['F3']),
            Course(id='CS304_3A', name='Maths III', code='CS304', section_id='3A',
                   l=3, t=1, p=0, faculty_ids=['F4']),
            Course(id='CS305_3A', name='DS Lab', code='CS305', section_id='3A',
                   l=0, t=0, p=2, faculty_ids=['F1'], room_type=RoomType.LAB, lab_batches=['A1', 'A2']),
            Course(id='CS306_3A', name='DBMS Lab', code='CS306', section_id='3A',
                   l=0, t=0, p=2, faculty_ids=['F2'], room_type=RoomType.LAB, lab_batches=['A1', 'A2']),
        ]
        return {'config': config, 'rooms': rooms, 'faculty': faculty, 'sections': sections, 'batches': batches, 'courses': courses}

    if scenario == 'infeasible':
        rooms = [
            Room(id='R101', name='Room 101', room_type=RoomType.THEORY_ROOM, capacity=70),
            Room(id='R102', name='Room 102', room_type=RoomType.THEORY_ROOM, capacity=70),
        ]
        faculty = [
            Faculty(id='F1', name='Dr. Sharma'),
            Faculty(id='F2', name='Prof. Patel'),
        ]
        sections = [
            Section(id='3A', name='3A', semester=3, division='A', strength=60),
        ]
        batches = [
            Batch(id='A1', name='A1', section_id='3A', strength=30),
        ]
        courses = [
            Course(id='CS301_3A', name='Data Structures', code='CS301', section_id='3A',
                   l=3, t=0, p=0, faculty_ids=['F1']),
            # Requires LAB room, but zero LAB rooms exist!
            Course(id='CS305_3A', name='DS Lab', code='CS305', section_id='3A',
                   l=0, t=0, p=2, faculty_ids=['F1'], room_type=RoomType.LAB, lab_batches=['A1']),
        ]
        return {'config': config, 'rooms': rooms, 'faculty': faculty, 'sections': sections, 'batches': batches, 'courses': courses}

    if scenario == 'bottleneck':
        rooms = [
            Room(id='R101', name='Room 101', room_type=RoomType.THEORY_ROOM, capacity=70),
            Room(id='R102', name='Room 102', room_type=RoomType.THEORY_ROOM, capacity=70),
            Room(id='LAB1', name='CS Lab 1', room_type=RoomType.LAB, capacity=35, category='CS'),
        ]
    else:  # 'standard'
        rooms = [
            Room(id='R101', name='Room 101', room_type=RoomType.THEORY_ROOM, capacity=70),
            Room(id='R102', name='Room 102', room_type=RoomType.THEORY_ROOM, capacity=70),
            Room(id='R103', name='Room 103', room_type=RoomType.THEORY_ROOM, capacity=70),
            Room(id='R104', name='Room 104', room_type=RoomType.THEORY_ROOM, capacity=70),
            Room(id='LAB1', name='CS Lab 1', room_type=RoomType.LAB, capacity=35, category='CS'),
            Room(id='LAB2', name='CS Lab 2', room_type=RoomType.LAB, capacity=35, category='CS'),
        ]

    faculty = [
        Faculty(id='F1', name='Dr. Sharma'),
        Faculty(id='F2', name='Prof. Patel'),
        Faculty(id='F3', name='Dr. Gupta'),
        Faculty(id='F4', name='Prof. Singh'),
        Faculty(id='F5', name='Dr. Verma'),
        Faculty(id='F6', name='Prof. Rao'),
        Faculty(id='F7', name='Dr. Joshi'),
        Faculty(id='F8', name='Prof. Kumar'),
    ]

    sections = [
        Section(id='3A', name='3A', semester=3, division='A', strength=60),
        Section(id='3B', name='3B', semester=3, division='B', strength=60),
        Section(id='5A', name='5A', semester=5, division='A', strength=60),
        Section(id='5B', name='5B', semester=5, division='B', strength=60),
    ]

    batches = [
        Batch(id='A1', name='A1', section_id='3A', strength=30),
        Batch(id='A2', name='A2', section_id='3A', strength=30),
        Batch(id='B1', name='B1', section_id='3B', strength=30),
        Batch(id='B2', name='B2', section_id='3B', strength=30),
        Batch(id='C1', name='C1', section_id='5A', strength=30),
        Batch(id='C2', name='C2', section_id='5A', strength=30),
        Batch(id='D1', name='D1', section_id='5B', strength=30),
        Batch(id='D2', name='D2', section_id='5B', strength=30),
    ]

    courses = [
        # Sem 3 - Section A
        Course(id='CS301_3A', name='Data Structures', code='CS301', section_id='3A',
               l=3, t=0, p=0, faculty_ids=['F1']),
        Course(id='CS302_3A', name='DBMS', code='CS302', section_id='3A',
               l=3, t=0, p=0, faculty_ids=['F2']),
        Course(id='CS303_3A', name='Computer Org', code='CS303', section_id='3A',
               l=3, t=0, p=0, faculty_ids=['F3']),
        Course(id='CS304_3A', name='Maths III', code='CS304', section_id='3A',
               l=3, t=1, p=0, faculty_ids=['F4']),
        Course(id='CS305_3A', name='DS Lab', code='CS305', section_id='3A',
               l=0, t=0, p=2, faculty_ids=['F1'], room_type=RoomType.LAB, lab_batches=['A1', 'A2']),
        Course(id='CS306_3A', name='DBMS Lab', code='CS306', section_id='3A',
               l=0, t=0, p=2, faculty_ids=['F2'], room_type=RoomType.LAB, lab_batches=['A1', 'A2']),

        # Sem 3 - Section B
        Course(id='CS301_3B', name='Data Structures', code='CS301', section_id='3B',
               l=3, t=0, p=0, faculty_ids=['F1']),
        Course(id='CS302_3B', name='DBMS', code='CS302', section_id='3B',
               l=3, t=0, p=0, faculty_ids=['F2']),
        Course(id='CS303_3B', name='Computer Org', code='CS303', section_id='3B',
               l=3, t=0, p=0, faculty_ids=['F3']),
        Course(id='CS304_3B', name='Maths III', code='CS304', section_id='3B',
               l=3, t=1, p=0, faculty_ids=['F4']),
        Course(id='CS305_3B', name='DS Lab', code='CS305', section_id='3B',
               l=0, t=0, p=2, faculty_ids=['F1'], room_type=RoomType.LAB, lab_batches=['B1', 'B2']),
        Course(id='CS306_3B', name='DBMS Lab', code='CS306', section_id='3B',
               l=0, t=0, p=2, faculty_ids=['F2'], room_type=RoomType.LAB, lab_batches=['B1', 'B2']),

        # Sem 5 - Section A
        Course(id='CS501_5A', name='Operating Systems', code='CS501', section_id='5A',
               l=3, t=0, p=0, faculty_ids=['F5']),
        Course(id='CS502_5A', name='Software Engg', code='CS502', section_id='5A',
               l=3, t=0, p=0, faculty_ids=['F6']),
        Course(id='CS503_5A', name='Computer Networks', code='CS503', section_id='5A',
               l=3, t=0, p=0, faculty_ids=['F7']),
        Course(id='CS504_5A', name='Theory of Computation', code='CS504', section_id='5A',
               l=3, t=1, p=0, faculty_ids=['F8']),
        Course(id='CS505_5A', name='OS Lab', code='CS505', section_id='5A',
               l=0, t=0, p=2, faculty_ids=['F5'], room_type=RoomType.LAB, lab_batches=['C1', 'C2']),
        Course(id='CS506_5A', name='Networks Lab', code='CS506', section_id='5A',
               l=0, t=0, p=2, faculty_ids=['F7'], room_type=RoomType.LAB, lab_batches=['C1', 'C2']),

        # Sem 5 - Section B
        Course(id='CS501_5B', name='Operating Systems', code='CS501', section_id='5B',
               l=3, t=0, p=0, faculty_ids=['F5']),
        Course(id='CS502_5B', name='Software Engg', code='CS502', section_id='5B',
               l=3, t=0, p=0, faculty_ids=['F6']),
        Course(id='CS503_5B', name='Computer Networks', code='CS503', section_id='5B',
               l=3, t=0, p=0, faculty_ids=['F7']),
        Course(id='CS504_5B', name='Theory of Computation', code='CS504', section_id='5B',
               l=3, t=1, p=0, faculty_ids=['F8']),
        Course(id='CS505_5B', name='OS Lab', code='CS505', section_id='5B',
               l=0, t=0, p=2, faculty_ids=['F5'], room_type=RoomType.LAB, lab_batches=['D1', 'D2']),
        Course(id='CS506_5B', name='Networks Lab', code='CS506', section_id='5B',
               l=0, t=0, p=2, faculty_ids=['F7'], room_type=RoomType.LAB, lab_batches=['D1', 'D2']),
    ]

    return {
        'config': config,
        'rooms': rooms,
        'faculty': faculty,
        'sections': sections,
        'batches': batches,
        'courses': courses
    }
