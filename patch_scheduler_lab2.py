import re

with open('scheduler.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_lab = """                        course_type=CourseType.LAB,
                        section_id=course.section_id,
                        faculty_ids=batch_facs,
                        room_type=course.room_type,
                        required_room_id=sess_req_room,"""

new_lab = """                        course_type=CourseType.LAB,
                        section_id=course.section_id,
                        faculty_ids=batch_facs,
                        room_type='LAB' if not sess_req_room else course.room_type,
                        required_room_id=sess_req_room,"""

code = code.replace(old_lab, new_lab)

with open('scheduler.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched scheduler.py for LAB room_type again")
