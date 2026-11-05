with open('scheduler.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'course_type=CourseType.LAB' in line:
        print(''.join(lines[i-2:i+8]))
        break
