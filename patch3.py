import re

with open('scheduler.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_theory = '''
                    sess = ScheduleSession(
                        id=f"{course.id}_T{i}",
                        course_id=course.id,
                        course_name=course.name,
                        course_code=course.code,
                        course_type=CourseType.THEORY,
                        section_id=course.section_id,
                        faculty_ids=course.faculty_ids,
'''

new_theory = '''
                    fac = course.faculty_ids[i % len(course.faculty_ids)] if course.faculty_ids else None
                    sess = ScheduleSession(
                        id=f"{course.id}_T{i}",
                        course_id=course.id,
                        course_name=course.name,
                        course_code=course.code,
                        course_type=CourseType.THEORY,
                        section_id=course.section_id,
                        faculty_ids=[fac] if fac else [],
'''
code = code.replace(old_theory, new_theory)

with open('scheduler.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Patched theory faculty distribution.')
