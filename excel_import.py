import openpyxl
from openpyxl.styles import Font, PatternFill
import os
from models import Faculty, Room, Section, Batch, Course

def generate_template(filepath):
    wb = openpyxl.Workbook()
    
    # 1. Faculty
    ws = wb.active
    ws.title = "Faculty"
    ws.append(["faculty_id", "name"])
    ws.append(["F001", "Dr. Alan Turing"])
    ws.append(["F002", "Ada Lovelace"])
    
    # 2. Rooms
    ws = wb.create_sheet("Rooms")
    ws.append(["room_id", "name", "type", "capacity", "category"])
    ws.append(["R101", "Room 101", "THEORY_ROOM", 60, "Main Block"])
    ws.append(["LAB1", "CS Lab 1", "LAB", 30, "CS"])
    
    # 3. Sections
    ws = wb.create_sheet("Sections")
    ws.append(["section_id", "name", "semester", "division", "strength", "home_room_id"])
    ws.append(["3A", "Section 3A", 3, "A", 60, "R101"])
    
    # 4. Batches
    ws = wb.create_sheet("Batches")
    ws.append(["batch_id", "batch_name", "section_id", "strength"])
    ws.append(["B3A1", "A1", "3A", 30])
    ws.append(["B3A2", "A2", "3A", 30])
    
    # 5. Courses
    ws = wb.create_sheet("Courses")
    ws.append(["course_id", "name", "code", "section_id", "L", "T", "P", "faculty_ids", "assistant_faculty_ids", "room_type", "required_room", "lab_batches"])
    ws.append(["CS301_3A", "Data Structures", "CS301", "3A", 3, 0, 2, "F001,F002", "F003,F004", "THEORY_ROOM", "", "B3A1,B3A2"])
    ws.append(["CS302_3A", "Digital Logic", "CS302", "3A", 3, 0, 0, "F002", "", "THEORY_ROOM", "", ""])
    
    # Style headers
    header_font = Font(bold=True)
    fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
    for sheet in wb.sheetnames:
        for cell in wb[sheet][1]:
            cell.font = header_font
            cell.fill = fill
            
    wb.save(filepath)

def parse_excel(filepath):
    """Parse excel and return structured data to replace app_data."""
    wb = openpyxl.load_workbook(filepath, data_only=True)
    
    data = {
        'faculty': [],
        'rooms': [],
        'sections': [],
        'batches': [],
        'courses': [],
    }
    errors = []
    
    # Map common aliases to canonical field names
    HEADER_ALIASES = {
        'asst faculty': 'assistant_faculty_ids',
        'asst_faculty': 'assistant_faculty_ids',
        'assistant faculty': 'assistant_faculty_ids',
        'assistant_faculty': 'assistant_faculty_ids',
        'asst faculty ids': 'assistant_faculty_ids',
        'asst_faculty_ids': 'assistant_faculty_ids',
        'required_room_id': 'required_room',
    }

    def normalize_header(h, sheet_name):
        h_lower = h.strip().lower()
        if sheet_name == 'Courses' and h_lower in ('faculty_id', 'faculty'):
            return 'faculty_ids'
        return HEADER_ALIASES.get(h_lower, h.strip())

    def get_rows(sheet_name):
        if sheet_name not in wb.sheetnames:
            return []
        ws = wb[sheet_name]
        raw_headers = [str(cell.value).strip() if cell.value else "" for cell in ws[1]]
        headers = [normalize_header(h, sheet_name) for h in raw_headers]
        rows = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(row): continue
            rows.append(dict(zip(headers, row)))
        return rows

    # Faculty
    for r in get_rows("Faculty"):
        try:
            data['faculty'].append(Faculty(id=str(r['faculty_id']), name=str(r['name'])))
        except Exception as e:
            errors.append(f"Faculty Error in row {r}: {e}")

    # Rooms
    for r in get_rows("Rooms"):
        try:
            data['rooms'].append(Room(
                id=str(r['room_id']), name=str(r['name']), room_type=str(r['type']),
                capacity=int(r['capacity']) if r.get('capacity') else None,
                category=str(r['category']) if r.get('category') else None
            ))
        except Exception as e:
            errors.append(f"Rooms Error in row {r}: {e}")

    # Sections
    for r in get_rows("Sections"):
        try:
            data['sections'].append(Section(
                id=str(r['section_id']), name=str(r['name']),
                semester=int(r['semester']), division=str(r['division']),
                strength=int(r['strength']) if r.get('strength') else None,
                home_room_id=str(r.get('home_room_id')).strip() if r.get('home_room_id') and str(r.get('home_room_id')).strip() not in ('None', '') else None
            ))
        except Exception as e:
            errors.append(f"Sections Error in row {r}: {e}")

    # Batches
    for r in get_rows("Batches"):
        try:
            data['batches'].append(Batch(
                id=str(r['batch_id']), name=str(r['batch_name']),
                section_id=str(r['section_id']),
                strength=int(r['strength']) if r.get('strength') else None
            ))
        except Exception as e:
            errors.append(f"Batches Error in row {r}: {e}")

    # Courses
    for r in get_rows("Courses"):
        try:
            fac_str = str(r.get('faculty_ids') or '')
            fac_ids = [f.strip() for f in fac_str.split(',')] if fac_str and fac_str.strip() else []
            
            asst_fac_str = str(r.get('assistant_faculty_ids') or '')
            asst_fac_ids = [f.strip() for f in asst_fac_str.split(',')] if asst_fac_str and asst_fac_str.strip() else []
            
            batch_str = str(r.get('lab_batches') or '')
            batches = [b.strip() for b in batch_str.split(',')] if batch_str and batch_str.strip() else []
            
            name_lower = str(r.get('name') or '').lower()
            if 'arithmetical thinking' in name_lower or 'corporate communication' in name_lower:
                continue

            data['courses'].append(Course(
                id=str(r['course_id']),
                name=str(r['name']),
                code=str(r['code']),
                section_id=str(r['section_id']),
                l=float(r.get('L') or 0),
                t=float(r.get('T') or 0),
                p=float(r.get('P') or 0),
                faculty_ids=fac_ids,
                assistant_faculty_ids=asst_fac_ids,
                room_type=str(r.get('room_type') or 'THEORY_ROOM'),
                required_room_id=str(r.get('required_room')) if r.get('required_room') else None,
                lab_batches=batches
            ))
        except Exception as e:
            errors.append(f"Courses Error in row {r}: {e}")

    if errors:
        return {'status': 'error', 'errors': errors}
    return {'status': 'ok', 'data': data}

if __name__ == '__main__':
    generate_template('timetable_import_template.xlsx')
    print("Template generated.")
