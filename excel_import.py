"""
excel_import.py - Excel workbook parser and template generator.

Supports importing Faculty, Rooms, Sections, Batches, and Courses
from an .xlsx file with normalized sheet structures and robust header aliasing.
"""

import os
from typing import Dict, Any, List
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from models import Faculty, Room, Section, Batch, Course, RoomType


HEADER_ALIASES = {
    'asst faculty': 'assistant_faculty_ids',
    'asst_faculty': 'assistant_faculty_ids',
    'assistant faculty': 'assistant_faculty_ids',
    'assistant_faculty': 'assistant_faculty_ids',
    'asst faculty ids': 'assistant_faculty_ids',
    'asst_faculty_ids': 'assistant_faculty_ids',
    'required_room': 'required_room_id',
    'required_room_id': 'required_room_id',
    'required room': 'required_room_id',
    'room_type': 'room_type',
    'type': 'room_type',
    'l': 'l',
    't': 't',
    'p': 'p',
    'batch_name': 'name',
}


def normalize_header(h: str, sheet_name: str) -> str:
    h_clean = str(h).strip().lower()
    if sheet_name.lower() == 'courses' and h_clean in ('faculty_id', 'faculty'):
        return 'faculty_ids'
    return HEADER_ALIASES.get(h_clean, str(h).strip())


def parse_excel(filepath: str) -> Dict[str, Any]:
    """Parse an .xlsx workbook into structured domain models."""
    wb = openpyxl.load_workbook(filepath, data_only=True)
    sheet_names_lower = {s.lower(): s for s in wb.sheetnames}

    data = {
        'faculty': [],
        'rooms': [],
        'sections': [],
        'batches': [],
        'courses': [],
    }
    errors = []

    def get_sheet_rows(expected_name: str) -> List[Dict[str, Any]]:
        actual_name = sheet_names_lower.get(expected_name.lower())
        if not actual_name:
            return []
        ws = wb[actual_name]
        raw_headers = [str(cell.value).strip() if cell.value is not None else "" for cell in ws[1]]
        headers = [normalize_header(h, expected_name) for h in raw_headers]
        rows = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(row):
                continue
            row_dict = {}
            for h, val in zip(headers, row):
                if h:
                    row_dict[h] = val
            rows.append(row_dict)
        return rows

    # 1. Faculty
    for r in get_sheet_rows("Faculty"):
        try:
            fid = str(r.get('faculty_id') or r.get('id') or '').strip()
            name = str(r.get('name') or '').strip()
            if fid and name:
                data['faculty'].append(Faculty(id=fid, name=name))
        except Exception as e:
            errors.append(f"Faculty error in row {r}: {e}")

    # 2. Rooms
    for r in get_sheet_rows("Rooms"):
        try:
            rid = str(r.get('room_id') or r.get('id') or '').strip()
            name = str(r.get('name') or '').strip()
            rtype = str(r.get('room_type') or RoomType.THEORY_ROOM).strip().upper()
            if rtype not in ('LAB', 'THEORY_ROOM'):
                rtype = 'LAB' if 'LAB' in rtype else 'THEORY_ROOM'
            cap = int(r.get('capacity')) if r.get('capacity') not in (None, '') else None
            cat = str(r.get('category')).strip() if r.get('category') else None
            if rid and name:
                data['rooms'].append(Room(id=rid, name=name, room_type=rtype, capacity=cap, category=cat))
        except Exception as e:
            errors.append(f"Rooms error in row {r}: {e}")

    # 3. Sections
    for r in get_sheet_rows("Sections"):
        try:
            sid = str(r.get('section_id') or r.get('id') or '').strip()
            name = str(r.get('name') or sid).strip()
            sem = int(r.get('semester') or 1)
            div = str(r.get('division') or '').strip()
            strength = int(r.get('strength')) if r.get('strength') not in (None, '') else None
            hr = str(r.get('home_room_id')).strip() if r.get('home_room_id') not in (None, '', 'None') else None
            if sid:
                data['sections'].append(Section(id=sid, name=name, semester=sem, division=div, strength=strength, home_room_id=hr))
        except Exception as e:
            errors.append(f"Sections error in row {r}: {e}")

    # 4. Batches
    for r in get_sheet_rows("Batches"):
        try:
            bid = str(r.get('batch_id') or r.get('id') or '').strip()
            name = str(r.get('name') or r.get('batch_name') or bid).strip()
            sid = str(r.get('section_id') or '').strip()
            strength = int(r.get('strength')) if r.get('strength') not in (None, '') else None
            if bid and sid:
                data['batches'].append(Batch(id=bid, name=name, section_id=sid, strength=strength))
        except Exception as e:
            errors.append(f"Batches error in row {r}: {e}")

    # 5. Courses
    for r in get_sheet_rows("Courses"):
        try:
            cid = str(r.get('course_id') or r.get('id') or '').strip()
            name = str(r.get('name') or '').strip()
            code = str(r.get('code') or cid).strip()
            sid = str(r.get('section_id') or '').strip()

            fac_str = str(r.get('faculty_ids') or '')
            fac_ids = [f.strip().strip('"').strip("'") for f in fac_str.split(',') if f.strip().strip('"').strip("'")]

            asst_str = str(r.get('assistant_faculty_ids') or '')
            asst_ids = [f.strip().strip('"').strip("'") for f in asst_str.split(',') if f.strip().strip('"').strip("'")]

            b_str = str(r.get('lab_batches') or '')
            batches = [b.strip().strip('"').strip("'") for b in b_str.split(',') if b.strip().strip('"').strip("'")]

            rtype = str(r.get('room_type') or RoomType.THEORY_ROOM).strip().upper()
            if rtype not in ('LAB', 'THEORY_ROOM'):
                rtype = 'LAB' if 'LAB' in rtype else 'THEORY_ROOM'

            req_room = str(r.get('required_room_id')).strip() if r.get('required_room_id') not in (None, '', 'None') else None

            l_val = float(r.get('l') or r.get('L') or 0)
            t_val = float(r.get('t') or r.get('T') or 0)
            p_val = float(r.get('p') or r.get('P') or 0)

            if cid and sid:
                data['courses'].append(Course(
                    id=cid,
                    name=name,
                    code=code,
                    section_id=sid,
                    l=l_val,
                    t=t_val,
                    p=p_val,
                    faculty_ids=fac_ids,
                    assistant_faculty_ids=asst_ids,
                    room_type=rtype,
                    required_room_id=req_room,
                    lab_batches=batches
                ))
        except Exception as e:
            errors.append(f"Courses error in row {r}: {e}")

    if errors:
        return {'status': 'error', 'errors': errors}
    return {'status': 'ok', 'data': data}


def generate_template(filepath: str, prefill_user_data: bool = True) -> str:
    """Generate a clean Excel workbook matching the exact academic structure."""
    wb = openpyxl.Workbook()

    # 1. Faculty
    ws_fac = wb.active
    ws_fac.title = "Faculty"
    ws_fac.append(["faculty_id", "name"])

    # 2. Rooms
    ws_rooms = wb.create_sheet("Rooms")
    ws_rooms.append(["room_id", "name", "type", "capacity", "category"])

    # 3. Sections
    ws_sec = wb.create_sheet("Sections")
    ws_sec.append(["section_id", "name", "semester", "division", "strength", "home_room_id"])

    # 4. Batches
    ws_bat = wb.create_sheet("Batches")
    ws_bat.append(["batch_id", "batch_name", "section_id", "strength"])

    # 5. Courses
    ws_crs = wb.create_sheet("Courses")
    ws_crs.append(["course_id", "name", "code", "section_id", "L", "T", "P", "faculty_ids", "Asst faculty", "room_type", "required_room", "lab_batches"])

    if prefill_user_data:
        faculty_rows = [
            ("F001", "Nagaratna K"), ("F002", "Veena H"), ("F003", "Jyoti Patil"),
            ("F004", "Maheshgouda Patil"), ("F005", "Arundati A"), ("F006", "Megha Javoor"),
            ("F007", "Amit K"), ("F008", "Soumya Patil"), ("F009", "Mallikarjun Akki"),
            ("F010", "Pavan G"), ("F011", "Pavan"), ("F012", "Aishwarya N"),
            ("F013", "Sadaf S"), ("F014", "Shrushti N"), ("F015", "Sneha V"),
            ("F016", "Dheeraj K"), ("F017", "Shrishti G"), ("F018", "Pooja S"),
            ("F019", "Umadevi"), ("F020", "Narayan D G")
        ]
        for row in faculty_rows:
            ws_fac.append(list(row))

        room_rows = [
            ("R001", "LHC201", "LAB", 35, ""),
            ("R002", "LAB6", "LAB", 35, ""),
            ("R003", "LHC306", "THEORY_ROOM", 70, ""),
            ("R004", "LHC307", "THEORY_ROOM", 70, ""),
            ("R005", "LHC301", "THEORY_ROOM", 70, ""),
            ("R006", "LHC202", "THEORY_ROOM", 70, ""),
            ("R007", "CLH310", "LAB", 70, ""),
            ("R008", "CLH309", "LAB", 35, ""),
        ]
        for row in room_rows:
            ws_rooms.append(list(row))

        section_rows = [
            ("S3A", "3A", 3, "A", 70, "R005"),
            ("S3B", "3B", 3, "B", 68, "R006"),
            ("S5A", "5A", 5, "A", 70, "R003"),
            ("S5B", "5B", 5, "B", 65, "R004"),
        ]
        for row in section_rows:
            ws_sec.append(list(row))

        batch_rows = [
            ("B3A1", "A1", "S3A", 35),
            ("B3A2", "A2", "S3A", 35),
            ("B3B1", "B1", "S3B", 35),
            ("B3B2", "B2", "S3B", 33),
            ("B5A1", "A1", "S5A", 35),
            ("B5A2", "A2", "S5A", 35),
            ("B5B1", "B1", "S5B", 35),
            ("B5B2", "B2", "S5B", 30),
        ]
        for row in batch_rows:
            ws_bat.append(list(row))

        course_rows = [
            ("C3A01", "Discrete Mathematical Structures", "26EMAB229", "S3A", 3, 0, 2, "F001", "", "THEORY_ROOM", "", "B3A1,B3A2"),
            ("C3A02", "Database Management System", "26ECAC201", "S3A", 3, 0, 0, "F003", "", "THEORY_ROOM", "", ""),
            ("C3A03", "Design and Analysis of Algorithms", "26ECAC202", "S3A", 3, 0, 0, "F004", "", "THEORY_ROOM", "", ""),
            ("C3A04", "Operating System Principles and Programming", "26ECAC203", "S3A", 3, 0, 2, "F005", "", "THEORY_ROOM", "", "B3A1,B3A2"),
            ("C3A05", "Software Engineering", "26ECAC204", "S3A", 3, 0, 0, "F007", "", "THEORY_ROOM", "", ""),
            ("C3A06", "Algorithms Lab", "26ECAP201", "S3A", 0, 0, 3, "F004", "F010", "LAB", "", "B3A1,B3A2"),
            ("C3A07", "Database Applications Lab", "26ECAP202", "S3A", 0, 0, 3, "F003", "F012", "LAB", "", "B3A1,B3A2"),
            ("C3A08", "Web Technologies Lab", "26ECAP203", "S3A", 0, 0, 3, "F013", "F012", "LAB", "R008", "B3A1,B3A2"),
            ("C3B01", "Discrete Mathematical Structures", "26EMAB229", "S3B", 3, 0, 2, "F001", "", "THEORY_ROOM", "", "B3B1,B3B2"),
            ("C3B02", "Database Management System", "26ECAC201", "S3B", 3, 0, 0, "F003", "", "THEORY_ROOM", "", ""),
            ("C3B03", "Design and Analysis of Algorithms", "26ECAC202", "S3B", 3, 0, 0, "F010", "", "THEORY_ROOM", "", ""),
            ("C3B04", "Operating System Principles and Programming", "26ECAC203", "S3B", 3, 0, 2, "F005", "", "THEORY_ROOM", "", "B3B1,B3B2"),
            ("C3B05", "Software Engineering", "26ECAC204", "S3B", 3, 0, 0, "F007", "", "THEORY_ROOM", "", ""),
            ("C3B06", "Algorithms Lab", "26ECAP201", "S3B", 0, 0, 3, "F010", "F004", "LAB", "", "B3B1,B3B2"),
            ("C3B07", "Database Applications Lab", "26ECAP202", "S3B", 0, 0, 3, "F003", "F012", "LAB", "", "B3B1,B3B2"),
            ("C3B08", "Web Technologies Lab", "26ECAP203", "S3B", 0, 0, 3, "F009", "F012", "LAB", "R008", "B3B1,B3B2"),
            ("C5A01", "Deep Learning", "26ECAC302", "S5A", 4, 0, 0, "F015", "", "THEORY_ROOM", "", ""),
            ("C5A02", "Cloud Computing", "26ECAC301", "S5A", 3, 0, 2, "F016", "", "THEORY_ROOM", "", "B5A1,B5A2"),
            ("C5A03", "Parallel and GPU Computing", "26ECAC304", "S5A", 3, 0, 2, "F017", "", "THEORY_ROOM", "", "B5A1,B5A2"),
            ("C5A04", "Cryptography and Network Security", "26ECAC305", "S5A", 3, 0, 2, "F018", "", "THEORY_ROOM", "", "B5A1,B5A2"),
            ("C5A05", "Deep Learning Lab", "26ECAP301", "S5A", 0, 0, 3, "F015", "F002", "LAB", "", "B5A1,B5A2"),
            ("C5A06", "Mini Project", "22ECAW301", "S5A", 0, 0, 3, "F018", "F015, F019, F001", "LAB", "R007", ""),
            ("C5A08", "AI-Assisted Software Development", "26ECSE346", "S5A", 1, 0, 3, "F020", "F007, F008", "LAB", "R007", ""),
            ("C5B01", "Deep Learning", "26ECAC302", "S5B", 4, 0, 0, "F019", "", "THEORY_ROOM", "", ""),
            ("C5B02", "Cloud Computing", "26ECAC301", "S5B", 3, 0, 2, "F016", "", "THEORY_ROOM", "", "B5B1,B5B2"),
            ("C5B03", "Parallel and GPU Computing", "26ECAC304", "S5B", 3, 0, 2, "F017", "", "THEORY_ROOM", "", "B5B1,B5B2"),
            ("C5B04", "Cryptography and Network Security", "26ECAC305", "S5B", 3, 0, 2, "F018", "", "THEORY_ROOM", "", "B5B1,B5B2"),
            ("C5B05", "Deep Learning Lab", "26ECAP301", "S5B", 0, 0, 3, "F019", "F002", "LAB", "", "B5B1,B5B2"),
            ("C5B06", "Mini Project", "22ECAW301", "S5B", 0, 0, 3, "F019", "F015, F018, F001", "LAB", "R007", ""),
            ("C5B08", "AI-Assisted Software Development", "26ECSE346", "S5B", 1, 0, 3, "F008", "F007, F009", "LAB", "R007", ""),
        ]
        for row in course_rows:
            ws_crs.append(list(row))

    # Styling headers
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    align_center = Alignment(horizontal="center", vertical="center")

    for sheet in wb.sheetnames:
        ws = wb[sheet]
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = align_center
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    wb.save(filepath)
    return filepath


if __name__ == '__main__':
    generate_template('timetable_import_template.xlsx', prefill_user_data=True)
    print("Template generated successfully.")
