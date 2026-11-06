"""
exporter.py - Multi-tab formatted Excel timetable exporter for AutoSchedule.

Generates an institutional spreadsheet containing:
  - Master Schedule (Cross-section institutional grid)
  - Faculty Schedules (Individual teaching commitments)
  - Room Schedules (Classroom & lab utilization)
  - Section Schedules (Class cohort timetables)
"""

import io
from typing import Dict, List, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from time_slots import generate_time_slots


# Institutional Style Tokens
NAVY_FILL = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
HEADER_FONT = Font(name="Inter", size=10, bold=True, color="FFFFFF")
DAY_FONT = Font(name="Inter", size=10, bold=True, color="0F172A")
SUBJ_FONT = Font(name="Inter", size=9, bold=True, color="0F172A")
META_FONT = Font(name="Inter", size=8, color="475569")

THEORY_FILL = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
LAB_FILL = PatternFill(start_color="F0FDF4", end_color="F0FDF4", fill_type="solid")
BREAK_FILL = PatternFill(start_color="FFF7ED", end_color="FFF7ED", fill_type="solid")
EMPTY_FILL = PatternFill(start_color="FAFAFA", end_color="FAFAFA", fill_type="solid")

THIN_BORDER = Border(
    left=Side(style="thin", color="CBD5E1"),
    right=Side(style="thin", color="CBD5E1"),
    top=Side(style="thin", color="CBD5E1"),
    bottom=Side(style="thin", color="CBD5E1"),
)
BREAK_BORDER = Border(
    left=Side(style="dashed", color="FED7AA"),
    right=Side(style="dashed", color="FED7AA"),
    top=Side(style="thin", color="E2E8F0"),
    bottom=Side(style="thin", color="E2E8F0"),
)


def generate_timetable_excel(app_data: Dict[str, Any]) -> io.BytesIO:
    """Generate a multi-tab institutional Excel workbook of the current timetable."""
    engine = app_data.get("engine")
    config = app_data.get("config")
    if not engine or not config or not engine.assignments:
        raise ValueError("No generated timetable available to export.")

    time_slots = generate_time_slots(config)
    assignments = app_data.get("result", {}).get("assignments")
    if not assignments and hasattr(engine, "_format_assignments"):
        assignments = engine._format_assignments()
    if not assignments:
        raise ValueError("No assignments found in timetable result.")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default sheet

    # 1. Sheet: Master Schedule
    ws_master = wb.create_sheet(title="Master Schedule")
    _build_master_sheet(ws_master, config, time_slots, assignments, app_data.get("sections", []))

    # 2. Sheet: Section Schedules
    ws_sections = wb.create_sheet(title="Section Schedules")
    _build_entity_sheet(ws_sections, config, time_slots, assignments, "section", app_data.get("sections", []))

    # 3. Sheet: Faculty Schedules
    ws_faculty = wb.create_sheet(title="Faculty Schedules")
    _build_entity_sheet(ws_faculty, config, time_slots, assignments, "faculty", app_data.get("faculty", []))

    # 4. Sheet: Room Schedules
    ws_rooms = wb.create_sheet(title="Room Schedules")
    _build_entity_sheet(ws_rooms, config, time_slots, assignments, "room", app_data.get("rooms", []))

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _build_master_sheet(ws, config, time_slots, assignments, sections):
    # Prepare ordered timeline columns
    timeline = _build_timeline(config, time_slots)

    # Headers
    headers = ["Day", "Section"] + [f"{b['start_time']} - {b['end_time']}" for b in timeline]
    ws.append(headers)

    ws.row_dimensions[1].height = 28
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = NAVY_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER

    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 16
    for idx, _ in enumerate(timeline, start=3):
        ws.column_dimensions[get_column_letter(idx)].width = 20

    # Index assignments by (day, section_id, start_time)
    assign_map = {}
    for a in assignments:
        k = (a["day"], a["section_id"], a["time_start"])
        if k not in assign_map:
            assign_map[k] = []
        assign_map[k].append(a)

    current_row = 2
    for day in config.working_days:
        day_start_row = current_row
        for sec in sections:
            row_vals = [day, sec.name]
            ws.append(row_vals)
            ws.row_dimensions[current_row].height = 36

            c_day = ws.cell(row=current_row, column=1)
            c_day.font = DAY_FONT
            c_day.alignment = Alignment(horizontal="center", vertical="center")
            c_day.border = THIN_BORDER

            c_sec = ws.cell(row=current_row, column=2)
            c_sec.font = DAY_FONT
            c_sec.alignment = Alignment(horizontal="center", vertical="center")
            c_sec.border = THIN_BORDER

            # Fill slot columns
            for col_idx, col_block in enumerate(timeline, start=3):
                cell = ws.cell(row=current_row, column=col_idx)
                cell.border = THIN_BORDER

                if col_block["type"] == "break":
                    cell.fill = BREAK_FILL
                    cell.value = "LUNCH" if col_block.get("is_lunch") else "BREAK"
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    cell.font = Font(name="Inter", size=9, bold=True, color="C2410C")
                    cell.border = BREAK_BORDER
                    continue

                # Slot matching
                k = (day, sec.id, col_block["start_time"])
                slot_assigns = assign_map.get(k, [])

                if slot_assigns:
                    is_lab = any(s["course_type"] == "LAB" for s in slot_assigns)
                    cell.fill = LAB_FILL if is_lab else THEORY_FILL

                    lines = []
                    for item in slot_assigns:
                        b_tag = f" [{item['batch_name']}]" if item["batch_name"] and item["batch_name"] != "ALL" else ""
                        lines.append(f"{item['course_code']}{b_tag}\n{item['faculty_name']} ({item['room_name']})")

                    cell.value = "\n".join(lines)
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                    cell.font = SUBJ_FONT
                else:
                    cell.fill = EMPTY_FILL

            current_row += 1

        # Merge day cells vertically across sections
        if sections and (current_row - 1) >= day_start_row:
            ws.merge_cells(start_row=day_start_row, start_column=1, end_row=current_row - 1, end_column=1)


def _build_entity_sheet(ws, config, time_slots, assignments, entity_type, entities):
    timeline = _build_timeline(config, time_slots)
    headers = ["Entity", "Day"] + [f"{b['start_time']} - {b['end_time']}" for b in timeline]
    ws.append(headers)

    ws.row_dimensions[1].height = 26
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = NAVY_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 14
    for idx, _ in enumerate(timeline, start=3):
        ws.column_dimensions[get_column_letter(idx)].width = 20

    current_row = 2
    for entity in entities:
        ent_start_row = current_row
        ent_id = entity.id
        ent_name = entity.name

        # Filter assignments for this entity
        if entity_type == "section":
            ent_assigns = [a for a in assignments if a["section_id"] == ent_id]
        elif entity_type == "faculty":
            ent_assigns = [a for a in assignments if (a.get("faculty_ids") and ent_id in a["faculty_ids"]) or a.get("faculty_id") == ent_id]
        elif entity_type == "room":
            ent_assigns = [a for a in assignments if a["room_id"] == ent_id]
        else:
            ent_assigns = []

        assign_map = {}
        for a in ent_assigns:
            k = (a["day"], a["time_start"])
            if k not in assign_map:
                assign_map[k] = []
            assign_map[k].append(a)

        for day in config.working_days:
            ws.append([ent_name, day])
            ws.row_dimensions[current_row].height = 32

            c_ent = ws.cell(row=current_row, column=1)
            c_ent.font = DAY_FONT
            c_ent.alignment = Alignment(horizontal="center", vertical="center")
            c_ent.border = THIN_BORDER

            c_day = ws.cell(row=current_row, column=2)
            c_day.font = DAY_FONT
            c_day.alignment = Alignment(horizontal="center", vertical="center")
            c_day.border = THIN_BORDER

            for col_idx, col_block in enumerate(timeline, start=3):
                cell = ws.cell(row=current_row, column=col_idx)
                cell.border = THIN_BORDER

                if col_block["type"] == "break":
                    cell.fill = BREAK_FILL
                    cell.value = "LUNCH" if col_block.get("is_lunch") else "BREAK"
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    cell.font = Font(name="Inter", size=9, bold=True, color="C2410C")
                    cell.border = BREAK_BORDER
                    continue

                slot_assigns = assign_map.get((day, col_block["start_time"]), [])
                if slot_assigns:
                    is_lab = any(s["course_type"] == "LAB" for s in slot_assigns)
                    cell.fill = LAB_FILL if is_lab else THEORY_FILL

                    lines = []
                    for item in slot_assigns:
                        if entity_type == "section":
                            lines.append(f"{item['course_code']} ({item['faculty_name']}) - {item['room_name']}")
                        elif entity_type == "faculty":
                            lines.append(f"{item['course_code']} ({item['section_name']}) - {item['room_name']}")
                        elif entity_type == "room":
                            lines.append(f"{item['course_code']} ({item['section_name']}) - {item['faculty_name']}")

                    cell.value = "\n".join(lines)
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                    cell.font = SUBJ_FONT
                else:
                    cell.fill = EMPTY_FILL

            current_row += 1

        if (current_row - 1) >= ent_start_row:
            ws.merge_cells(start_row=ent_start_row, start_column=1, end_row=current_row - 1, end_column=1)


def _build_timeline(config, time_slots):
    blocks = []
    for s in time_slots:
        blocks.append({"type": "slot", "start_time": s.start_time, "end_time": s.end_time})

    if config.lunch_start and config.lunch_end:
        blocks.append({"type": "break", "is_lunch": True, "start_time": config.lunch_start, "end_time": config.lunch_end})

    for b in (config.breaks or []):
        blocks.append({"type": "break", "is_lunch": False, "start_time": b["start_time"], "end_time": b["end_time"]})

    blocks.sort(key=lambda x: x["start_time"])
    return blocks
