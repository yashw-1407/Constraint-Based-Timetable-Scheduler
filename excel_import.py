"""
excel_import.py - Excel workbook parser and template generator.

Handles:
- Robust parsing of sheets: Faculty, Rooms, Sections, Batches, Courses.
- Normalizes column names (handles casing, spaces, underscores, aliases).
- Extracts all fields: home rooms, assistant faculty, required rooms, etc.
- Exports starter template timetable_import_template.xlsx.
"""

import os
from typing import Dict, Any, List
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from models import Faculty, Room, Section, Batch, Course, RoomType


def normalize_key(k: str, sheet: str) -> str:
    """Normalize Excel column headers across variations."""
    k = str(k).strip().lower()
    sheet = sheet.lower()

    if sheet == 'courses':
        if k in ('faculty_id', 'faculty', 'faculty_ids', 'faculty id', 'fac_id'):
            return 'faculty_ids'
        if k in ('asst faculty', 'asst_faculty', 'assistant faculty', 'assistant_faculty',
                 'assistant_faculty_ids', 'asst faculty ids', 'asst_faculty_ids', 'asst'):
            return 'assistant_faculty_ids'
        if k in ('required_room', 'required room', 'required_room_id', 'req_room', 'req room', 'req_room_id'):
            return 'required_room_id'
        if k in ('batches', 'lab batches', 'lab_batches', 'lab batch', 'lab_batch', 'batch_ids'):
            return 'lab_batches'
        if k in ('course_id', 'id'):
            return 'id'
        if k in ('course_name', 'name'):
            return 'name'
        if k in ('course_code', 'code'):
            return 'code'
        if k in ('type', 'room type', 'room_type'):
            return 'room_type'

    elif sheet == 'batches':
        if k in ('batch_id', 'id'):
            return 'id'
        if k in ('batch_name', 'name'):
            return 'name'
        if k in ('home_room', 'home room', 'home_room_id', 'homeroom', 'homeroom_id'):
            return 'home_room_id'

    elif sheet == 'sections':
        if k in ('section_id', 'id'):
            return 'id'
        if k in ('section_name', 'name'):
            return 'name'
        if k in ('home_room', 'home room', 'home_room_id', 'homeroom', 'homeroom_id'):
            return 'home_room_id'

    elif sheet == 'rooms':
        if k in ('room_id', 'id'):
            return 'id'
        if k in ('room_name', 'name'):
            return 'name'
        if k in ('type', 'room type', 'room_type'):
            return 'room_type'

    elif sheet == 'faculty':
        if k in ('faculty_id', 'id', 'fac_id', 'fid'):
            return 'id'
        if k in ('faculty_name', 'name'):
            return 'name'

    return k


def parse_excel(filepath: str) -> Dict[str, Any]:
    """Parse an .xlsx workbook into structured domain models."""
    wb = openpyxl.load_workbook(filepath, data_only=True)
    sheet_names_lower = {s.lower(): s for s in wb.sheetnames}

    data = {
        'faculty': [],
        'rooms': [],
        'sections': [],
        'batches': [],
        'courses': []
    }
    errors: List[str] = []

    def get_rows(sheet_key: str):
        actual_name = sheet_names_lower.get(sheet_key.lower())
        if not actual_name:
            return None
        sheet = wb[actual_name]
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [normalize_key(cell, sheet_key) if cell is not None else '' for cell in rows[0]]
        dict_rows = []
        for r in rows[1:]:
            if all(v is None or str(v).strip() == '' for v in r):
                continue
            row_dict = {}
            for h, v in zip(headers, r):
                if h:
                    row_dict[h] = str(v).strip() if v is not None else ''
            dict_rows.append(row_dict)
        return dict_rows

    # 1. Faculty
    f_rows = get_rows('faculty')
    if f_rows is None:
        errors.append("Missing required worksheet: 'Faculty'")
    else:
        for idx, r in enumerate(f_rows, start=2):
            fid = r.get('id')
            name = r.get('name')
            if not fid or not name:
                errors.append(f"Faculty sheet row {idx}: 'id' and 'name' are required.")
            else:
                data['faculty'].append(Faculty(id=fid, name=name))

    # 2. Rooms
    r_rows = get_rows('rooms')
    if r_rows is None:
        errors.append("Missing required worksheet: 'Rooms'")
    else:
        for idx, r in enumerate(r_rows, start=2):
            rid = r.get('id')
            name = r.get('name')
            raw_type = (r.get('room_type') or 'THEORY_ROOM').upper()
            rtype = RoomType.LAB if 'LAB' in raw_type else RoomType.THEORY_ROOM
            cap_val = r.get('capacity', '')
            try:
                cap = int(float(cap_val)) if cap_val else None
            except ValueError:
                cap = None
            cat = r.get('category') or None
            if not rid or not name:
                errors.append(f"Rooms sheet row {idx}: 'id' and 'name' are required.")
            else:
                data['rooms'].append(Room(id=rid, name=name, room_type=rtype, capacity=cap, category=cat))

    # 3. Sections
    s_rows = get_rows('sections')
    if s_rows is None:
        errors.append("Missing required worksheet: 'Sections'")
    else:
        for idx, r in enumerate(s_rows, start=2):
            sid = r.get('id')
            name = r.get('name')
            try:
                sem = int(float(r.get('semester', 1)))
            except ValueError:
                sem = 1
            div = r.get('division') or 'A'
            try:
                strn = int(float(r.get('strength', ''))) if r.get('strength') else None
            except ValueError:
                strn = None
            hr = r.get('home_room_id') or None
            if not sid or not name:
                errors.append(f"Sections sheet row {idx}: 'id' and 'name' are required.")
            else:
                data['sections'].append(Section(id=sid, name=name, semester=sem, division=div, strength=strn, home_room_id=hr))

    # 4. Batches
    b_rows = get_rows('batches')
    if b_rows is not None:
        for idx, r in enumerate(b_rows, start=2):
            bid = r.get('id')
            name = r.get('name')
            sid = r.get('section_id')
            try:
                strn = int(float(r.get('strength', ''))) if r.get('strength') else None
            except ValueError:
                strn = None
            hr = r.get('home_room_id') or None
            if not bid or not name or not sid:
                errors.append(f"Batches sheet row {idx}: 'id', 'name', and 'section_id' are required.")
            else:
                data['batches'].append(Batch(id=bid, name=name, section_id=sid, strength=strn, home_room_id=hr))

    # 5. Courses
    c_rows = get_rows('courses')
    if c_rows is None:
        errors.append("Missing required worksheet: 'Courses'")
    else:
        for idx, r in enumerate(c_rows, start=2):
            cid = r.get('id')
            name = r.get('name')
            code = r.get('code')
            sid = r.get('section_id')
            try:
                l = float(r.get('l', 0) or 0)
                t = float(r.get('t', 0) or 0)
                p = float(r.get('p', 0) or 0)
            except ValueError:
                l, t, p = 0.0, 0.0, 0.0

            fac_str = r.get('faculty_ids') or ''
            fac_ids = [f.strip() for f in fac_str.replace(';', ',').split(',') if f.strip()]

            asst_str = r.get('assistant_faculty_ids') or ''
            asst_ids = [f.strip() for f in asst_str.replace(';', ',').split(',') if f.strip()]

            raw_type = (r.get('room_type') or 'THEORY_ROOM').upper()
            rtype = RoomType.LAB if 'LAB' in raw_type else RoomType.THEORY_ROOM
            req_room = r.get('required_room_id') or None

            batch_str = r.get('lab_batches') or ''
            lab_batches = [b.strip() for b in batch_str.replace(';', ',').split(',') if b.strip()]

            if not cid or not name or not code or not sid:
                errors.append(f"Courses sheet row {idx}: 'id', 'name', 'code', and 'section_id' are required.")
            else:
                data['courses'].append(Course(
                    id=cid, name=name, code=code, section_id=sid,
                    l=l, t=t, p=p, faculty_ids=fac_ids,
                    assistant_faculty_ids=asst_ids,
                    room_type=rtype, required_room_id=req_room,
                    lab_batches=lab_batches
                ))

    if errors:
        return {'status': 'error', 'errors': errors}

    return {'status': 'ok', 'data': data}


def generate_template(filepath: str, prefill_user_data: bool = True) -> None:
    """Generate Excel starter workbook."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1E3A8A', end_color='1E3A8A', fill_type='solid')

    def style_sheet(ws, headers, rows):
        ws.append(headers)
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')

        for row in rows:
            ws.append(row)

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Faculty
    ws_fac = wb.create_sheet('Faculty')
    fac_data = [
        ['F1', 'Dr. Sharma'],
        ['F2', 'Prof. Patel'],
        ['F3', 'Dr. Gupta'],
        ['F4', 'Prof. Singh'],
    ] if prefill_user_data else []
    style_sheet(ws_fac, ['faculty_id', 'name'], fac_data)

    # Rooms
    ws_rooms = wb.create_sheet('Rooms')
    room_data = [
        ['R101', 'Room 101', 'THEORY_ROOM', 70, 'Classroom'],
        ['R102', 'Room 102', 'THEORY_ROOM', 70, 'Classroom'],
        ['LAB1', 'CS Lab 1', 'LAB', 35, 'CS'],
    ] if prefill_user_data else []
    style_sheet(ws_rooms, ['room_id', 'name', 'type', 'capacity', 'category'], room_data)

    # Sections
    ws_sec = wb.create_sheet('Sections')
    sec_data = [
        ['3A', '3A', 3, 'A', 60, 'R101'],
        ['3B', '3B', 3, 'B', 60, 'R102'],
    ] if prefill_user_data else []
    style_sheet(ws_sec, ['section_id', 'name', 'semester', 'division', 'strength', 'home_room_id'], sec_data)

    # Batches
    ws_batch = wb.create_sheet('Batches')
    batch_data = [
        ['A1', 'A1', '3A', 30],
        ['A2', 'A2', '3A', 30],
        ['B1', 'B1', '3B', 30],
        ['B2', 'B2', '3B', 30],
    ] if prefill_user_data else []
    style_sheet(ws_batch, ['batch_id', 'batch_name', 'section_id', 'strength'], batch_data)

    # Courses
    ws_courses = wb.create_sheet('Courses')
    course_data = [
        ['CS301_3A', 'Data Structures', 'CS301', '3A', 3, 0, 0, 'F1', '', 'THEORY_ROOM', '', ''],
        ['CS302_3A', 'DBMS', 'CS302', '3A', 3, 0, 0, 'F2', '', 'THEORY_ROOM', '', ''],
        ['CS305_3A', 'DS Lab', 'CS305', '3A', 0, 0, 2, 'F1', 'F3', 'LAB', '', 'A1, A2'],
    ] if prefill_user_data else []
    style_sheet(ws_courses, ['course_id', 'name', 'code', 'section_id', 'L', 'T', 'P', 'faculty_ids', 'Asst faculty', 'room_type', 'required_room', 'lab_batches'], course_data)

    wb.save(filepath)
