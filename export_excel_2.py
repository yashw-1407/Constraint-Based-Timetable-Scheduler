import json
import openpyxl
from openpyxl.styles import Font, PatternFill

with open('database.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

# Hardcode the mappings correctly this time
hr_map = {'S3A': 'R005', 'S3B': 'R006', 'S5A': 'R003', 'S5B': 'R004'}

wb = openpyxl.Workbook()

# 1. Faculty
ws = wb.active
ws.title = "Faculty"
ws.append(["faculty_id", "name"])
for f in db['faculty']:
    ws.append([f['id'], f['name']])

# 2. Rooms
ws = wb.create_sheet("Rooms")
ws.append(["room_id", "name", "type", "capacity", "category"])
for r in db['rooms']:
    ws.append([r['id'], r['name'], r['room_type'], r.get('capacity', ''), r.get('category', '')])

# 3. Sections
ws = wb.create_sheet("Sections")
ws.append(["section_id", "name", "semester", "division", "strength", "home_room_id"])
for s in db['sections']:
    ws.append([s['id'], s['name'], s['semester'], s['division'], s.get('strength', ''), hr_map.get(s['id'], '')])

# 4. Batches
ws = wb.create_sheet("Batches")
ws.append(["batch_id", "batch_name", "section_id", "strength"])
for b in db.get('batches', []):
    ws.append([b['id'], b['name'], b['section_id'], b.get('strength', '')])

# 5. Courses
ws = wb.create_sheet("Courses")
ws.append(["course_id", "name", "code", "section_id", "L", "T", "P", "faculty_ids", "room_type", "required_room", "lab_batches"])
for c in db['courses']:
    req_room = ''
    if 'Mini Project' in c['name'] or 'AI-Assisted' in c['name']:
        req_room = 'R007'
    ws.append([
        c['id'], c['name'], c['code'], c['section_id'],
        c.get('l', 0), c.get('t', 0), c.get('p', 0),
        ','.join(c.get('faculty_ids', [])),
        c.get('room_type', 'THEORY_ROOM'),
        req_room,
        ','.join(c.get('lab_batches', []))
    ])

# Style headers
header_font = Font(bold=True)
fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
for sheet in wb.sheetnames:
    for cell in wb[sheet][1]:
        cell.font = header_font
        cell.fill = fill

wb.save('timetable_import_home_rooms.xlsx')
print("Created timetable_import_home_rooms.xlsx correctly")
