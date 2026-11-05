"""
importer.py - Excel and CSV data ingestion engine for AutoSchedule.

Provides:
  - Generation of standardized institutional starter template (XLSX)
  - Multi-sheet parsing for Rooms, Faculty, Sections, Batches, and Courses
  - Comprehensive pre-flight validation (schema check, referential integrity, duplicate detection)
"""

import io
from typing import Dict, List, Tuple, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from models import Room, Faculty, Section, Batch, Course, RoomType, CourseType


HEADER_FILL = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
HEADER_FONT = Font(name="Inter", size=10, bold=True, color="FFFFFF")
SAMPLE_FONT = Font(name="Inter", size=9, italic=True, color="64748B")
CELL_FONT = Font(name="Inter", size=10, color="0F172A")
THIN_BORDER = Border(
    left=Side(style="thin", color="E2E8F0"),
    right=Side(style="thin", color="E2E8F0"),
    top=Side(style="thin", color="E2E8F0"),
    bottom=Side(style="thin", color="E2E8F0"),
)


def generate_import_template() -> io.BytesIO:
    """Generate a formatted institutional starter Excel workbook."""
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    sheets_config = [
        {
            "title": "Rooms",
            "headers": ["Room ID", "Display Name", "Room Type", "Capacity", "Category"],
            "widths": [14, 24, 18, 12, 16],
            "samples": [
                ["R101", "Lecture Hall 101", "THEORY_ROOM", 70, "Main Block"],
                ["L201", "Advanced Computing Lab", "LAB", 40, "CS Wing"],
            ],
            "notes": "Room Type must be THEORY_ROOM or LAB."
        },
        {
            "title": "Faculty",
            "headers": ["Faculty ID", "Full Name"],
            "widths": [14, 28],
            "samples": [
                ["F101", "Dr. Jane Smith"],
                ["F102", "Prof. Alan Turing"],
            ],
            "notes": "Faculty ID must be unique across the institution."
        },
        {
            "title": "Sections",
            "headers": ["Section ID", "Section Name", "Semester", "Division", "Strength"],
            "widths": [14, 24, 12, 12, 12],
            "samples": [
                ["CS_3A", "3rd Sem Section A", 3, "A", 60],
                ["CS_3B", "3rd Sem Section B", 3, "B", 60],
            ],
            "notes": "Semester must be an integer from 1 to 8."
        },
        {
            "title": "Batches",
            "headers": ["Batch ID", "Batch Name", "Section ID", "Strength"],
            "widths": [16, 20, 14, 12],
            "samples": [
                ["CS_3A_B1", "Batch B1", "CS_3A", 30],
                ["CS_3A_B2", "Batch B2", "CS_3A", 30],
            ],
            "notes": "Section ID must match an existing Section ID."
        },
        {
            "title": "Courses",
            "headers": [
                "Course ID", "Course Code", "Course Title", "Section ID",
                "L", "T", "P",
                "Faculty IDs", "Assistant Faculty IDs",
                "Room Type", "Required Room ID", "Lab Batches"
            ],
            "widths": [18, 14, 28, 14, 8, 8, 8, 20, 20, 16, 18, 20],
            "samples": [
                ["CS301_3A", "CS301", "Operating Systems", "CS_3A", 3, 0, 0, "F101", "", "THEORY_ROOM", "", ""],
                ["CS302_3A", "CS302", "Operating Systems Lab", "CS_3A", 0, 0, 2, "F101", "F102", "LAB", "L201", "CS_3A_B1,CS_3A_B2"],
            ],
            "notes": "Multiple Faculty IDs, Assistant Faculty IDs, or Lab Batches must be separated by commas."
        }
    ]

    for cfg in sheets_config:
        ws = wb.create_sheet(title=cfg["title"])
        # Write headers
        ws.append(cfg["headers"])
        for col_idx, col_name in enumerate(cfg["headers"], 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = THIN_BORDER

        # Set row height
        ws.row_dimensions[1].height = 28

        # Write sample rows
        for row in cfg["samples"]:
            ws.append(row)
            row_idx = ws.max_row
            ws.row_dimensions[row_idx].height = 20
            for col_idx in range(1, len(row) + 1):
                c = ws.cell(row=row_idx, column=col_idx)
                c.font = SAMPLE_FONT
                c.border = THIN_BORDER
                c.alignment = Alignment(vertical="center")

        # Set column widths
        for col_idx, width in enumerate(cfg["widths"], 1):
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = width

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def parse_and_validate_excel(file_bytes: bytes) -> Tuple[bool, dict, List[str], dict]:
    """
    Parse and strictly validate an uploaded Excel workbook.
    
    Returns:
      (success: bool, counts: dict, errors: List[str], parsed_entities: dict)
    """
    errors: List[str] = []
    parsed: Dict[str, list] = {
        "rooms": [],
        "faculty": [],
        "sections": [],
        "batches": [],
        "courses": []
    }

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    except Exception as e:
        return False, {}, [f"Invalid or corrupted Excel file: {str(e)}"], {}

    # Check required sheets
    required_sheets = ["Rooms", "Faculty", "Sections", "Batches", "Courses"]
    missing_sheets = [s for s in required_sheets if s not in wb.sheetnames]
    if missing_sheets:
        return False, {}, [f"Workbook is missing required sheet(s): {', '.join(missing_sheets)}"], {}

    # 1. Parse Rooms
    rooms_ws = wb["Rooms"]
    room_ids = set()
    for row_idx, row in enumerate(rooms_ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or all(v is None for v in row):
            continue
        r_id = str(row[0]).strip() if row[0] is not None else ""
        r_name = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
        r_type = str(row[2]).strip().upper() if len(row) > 2 and row[2] is not None else "THEORY_ROOM"
        
        if not r_id:
            errors.append(f"Rooms sheet (Row {row_idx}): Room ID is required.")
            continue
        if r_id in room_ids:
            errors.append(f"Rooms sheet (Row {row_idx}): Duplicate Room ID '{r_id}'.")
            continue
        room_ids.add(r_id)

        if not r_name:
            r_name = r_id

        if r_type not in ["THEORY_ROOM", "LAB"]:
            errors.append(f"Rooms sheet (Row {row_idx}): Room Type '{r_type}' invalid. Must be THEORY_ROOM or LAB.")

        capacity = None
        if len(row) > 3 and row[3] is not None and str(row[3]).strip():
            try:
                capacity = int(float(str(row[3]).strip()))
            except ValueError:
                errors.append(f"Rooms sheet (Row {row_idx}): Capacity must be a number.")

        category = str(row[4]).strip() if len(row) > 4 and row[4] is not None else None

        parsed["rooms"].append(Room(id=r_id, name=r_name, room_type=r_type, capacity=capacity, category=category))

    # 2. Parse Faculty
    faculty_ws = wb["Faculty"]
    faculty_ids = set()
    for row_idx, row in enumerate(faculty_ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or all(v is None for v in row):
            continue
        f_id = str(row[0]).strip() if row[0] is not None else ""
        f_name = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""

        if not f_id:
            errors.append(f"Faculty sheet (Row {row_idx}): Faculty ID is required.")
            continue
        if f_id in faculty_ids:
            errors.append(f"Faculty sheet (Row {row_idx}): Duplicate Faculty ID '{f_id}'.")
            continue
        faculty_ids.add(f_id)

        if not f_name:
            errors.append(f"Faculty sheet (Row {row_idx}): Faculty Full Name is required.")
            continue

        parsed["faculty"].append(Faculty(id=f_id, name=f_name))

    # 3. Parse Sections
    sections_ws = wb["Sections"]
    section_ids = set()
    for row_idx, row in enumerate(sections_ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or all(v is None for v in row):
            continue
        s_id = str(row[0]).strip() if row[0] is not None else ""
        s_name = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
        
        if not s_id:
            errors.append(f"Sections sheet (Row {row_idx}): Section ID is required.")
            continue
        if s_id in section_ids:
            errors.append(f"Sections sheet (Row {row_idx}): Duplicate Section ID '{s_id}'.")
            continue
        section_ids.add(s_id)

        if not s_name:
            s_name = s_id

        semester = 1
        if len(row) > 2 and row[2] is not None and str(row[2]).strip():
            try:
                semester = int(float(str(row[2]).strip()))
            except ValueError:
                errors.append(f"Sections sheet (Row {row_idx}): Semester must be an integer.")

        division = str(row[3]).strip() if len(row) > 3 and row[3] is not None else "A"
        strength = None
        if len(row) > 4 and row[4] is not None and str(row[4]).strip():
            try:
                strength = int(float(str(row[4]).strip()))
            except ValueError:
                errors.append(f"Sections sheet (Row {row_idx}): Strength must be an integer.")

        parsed["sections"].append(Section(id=s_id, name=s_name, semester=semester, division=division, strength=strength))

    # 4. Parse Batches
    batches_ws = wb["Batches"]
    batch_ids = set()
    for row_idx, row in enumerate(batches_ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or all(v is None for v in row):
            continue
        b_id = str(row[0]).strip() if row[0] is not None else ""
        b_name = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
        b_sec = str(row[2]).strip() if len(row) > 2 and row[2] is not None else ""

        if not b_id:
            errors.append(f"Batches sheet (Row {row_idx}): Batch ID is required.")
            continue
        if b_id in batch_ids:
            errors.append(f"Batches sheet (Row {row_idx}): Duplicate Batch ID '{b_id}'.")
            continue
        batch_ids.add(b_id)

        if not b_sec:
            errors.append(f"Batches sheet (Row {row_idx}): Section ID reference is required.")
        elif b_sec not in section_ids:
            errors.append(f"Batches sheet (Row {row_idx}): Referenced Section ID '{b_sec}' does not exist in Sections sheet.")

        if not b_name:
            b_name = b_id

        strength = None
        if len(row) > 3 and row[3] is not None and str(row[3]).strip():
            try:
                strength = int(float(str(row[3]).strip()))
            except ValueError:
                errors.append(f"Batches sheet (Row {row_idx}): Batch Strength must be a number.")

        parsed["batches"].append(Batch(id=b_id, name=b_name, section_id=b_sec, strength=strength))

    # 5. Parse Courses
    courses_ws = wb["Courses"]
    course_ids = set()
    for row_idx, row in enumerate(courses_ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or all(v is None for v in row):
            continue
        c_id = str(row[0]).strip() if row[0] is not None else ""
        c_code = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
        c_name = str(row[2]).strip() if len(row) > 2 and row[2] is not None else ""
        c_sec = str(row[3]).strip() if len(row) > 3 and row[3] is not None else ""

        if not c_id:
            errors.append(f"Courses sheet (Row {row_idx}): Course ID is required.")
            continue
        if c_id in course_ids:
            errors.append(f"Courses sheet (Row {row_idx}): Duplicate Course ID '{c_id}'.")
            continue
        course_ids.add(c_id)

        if not c_code:
            errors.append(f"Courses sheet (Row {row_idx}): Course Code is required.")
        if not c_name:
            c_name = c_code
        if not c_sec:
            errors.append(f"Courses sheet (Row {row_idx}): Section ID reference is required.")
        elif c_sec not in section_ids:
            errors.append(f"Courses sheet (Row {row_idx}): Referenced Section ID '{c_sec}' does not exist in Sections sheet.")

        try:
            l = float(str(row[4]).strip()) if len(row) > 4 and row[4] is not None else 0.0
            t = float(str(row[5]).strip()) if len(row) > 5 and row[5] is not None else 0.0
            p = float(str(row[6]).strip()) if len(row) > 6 and row[6] is not None else 0.0
        except ValueError:
            errors.append(f"Courses sheet (Row {row_idx}): L, T, P must be numeric values.")
            l, t, p = 0.0, 0.0, 0.0

        if (l + t + p) <= 0:
            errors.append(f"Courses sheet (Row {row_idx}): Total course hours (L+T+P) must be greater than zero.")

        # Parse Faculty IDs
        fac_str = str(row[7]).strip() if len(row) > 7 and row[7] is not None else ""
        f_ids = [fid.strip() for fid in fac_str.split(",") if fid.strip()]
        for fid in f_ids:
            if fid not in faculty_ids:
                errors.append(f"Courses sheet (Row {row_idx}): Assigned Faculty ID '{fid}' does not exist in Faculty sheet.")

        # Parse Assistant Faculty IDs
        asst_str = str(row[8]).strip() if len(row) > 8 and row[8] is not None else ""
        asst_ids = [fid.strip() for fid in asst_str.split(",") if fid.strip()]
        for fid in asst_ids:
            if fid not in faculty_ids:
                errors.append(f"Courses sheet (Row {row_idx}): Assigned Assistant Faculty ID '{fid}' does not exist in Faculty sheet.")

        c_room_type = str(row[9]).strip().upper() if len(row) > 9 and row[9] is not None and str(row[9]).strip() else "THEORY_ROOM"
        if c_room_type not in ["THEORY_ROOM", "LAB"]:
            c_room_type = "THEORY_ROOM"

        req_room = str(row[10]).strip() if len(row) > 10 and row[10] is not None and str(row[10]).strip() else None
        if req_room and req_room not in room_ids:
            errors.append(f"Courses sheet (Row {row_idx}): Required Room ID '{req_room}' does not exist in Rooms sheet.")

        # Parse Lab Batches
        lab_str = str(row[11]).strip() if len(row) > 11 and row[11] is not None else ""
        lab_b = [b.strip() for b in lab_str.split(",") if b.strip()]
        for bid in lab_b:
            if bid not in batch_ids:
                errors.append(f"Courses sheet (Row {row_idx}): Assigned Lab Batch '{bid}' does not exist in Batches sheet.")

        parsed["courses"].append(Course(
            id=c_id,
            name=c_name,
            code=c_code,
            section_id=c_sec,
            l=l,
            t=t,
            p=p,
            faculty_ids=f_ids,
            assistant_faculty_ids=asst_ids,
            room_type=c_room_type,
            required_room_id=req_room,
            lab_batches=lab_b
        ))

    counts = {k: len(v) for k, v in parsed.items()}
    success = (len(errors) == 0)

    return success, counts, errors, parsed
