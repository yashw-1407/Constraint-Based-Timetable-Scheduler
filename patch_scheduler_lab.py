import re

with open('scheduler.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_lab = """                    sess = ScheduleSession(
                        id=f"{course.id}_L{b_idx}",
                        course_id=course.id,
                        course_name=course.name,
                        course_code=course.code,
                        course_type=CourseType.LAB,
                        section_id=course.section_id,
                        faculty_ids=batch_facs,
                        room_type=course.room_type,
                        required_room_id=course.required_room_id,"""

new_lab = """                    sess = ScheduleSession(
                        id=f"{course.id}_L{b_idx}",
                        course_id=course.id,
                        course_name=course.name,
                        course_code=course.code,
                        course_type=CourseType.LAB,
                        section_id=course.section_id,
                        faculty_ids=batch_facs,
                        room_type='LAB' if not course.required_room_id else course.room_type,
                        required_room_id=course.required_room_id,"""

code = code.replace(old_lab, new_lab)

with open('scheduler.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched scheduler.py for LAB room_type")
