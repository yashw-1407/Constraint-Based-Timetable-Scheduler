"""iCalendar (RFC 5545) Feed Generator for AutoSchedule.

Generates standard compliant iCalendar (.ics) subscription feeds
for faculty members and student cohorts. Compatible with Google Calendar,
Microsoft Outlook, and Apple Calendar.
"""

from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Optional, Any
from time_slots import generate_time_slots

DAY_NAME_TO_WEEKDAY = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}

DAY_TO_RRULE_BYDAY = {
    "Monday": "MO",
    "Tuesday": "TU",
    "Wednesday": "WE",
    "Thursday": "TH",
    "Friday": "FR",
    "Saturday": "SA",
    "Sunday": "SU"
}

def get_next_weekday_date(target_weekday_idx: int, base_date: Optional[date] = None) -> date:
    """Find the next date matching the target weekday index (0=Monday, 6=Sunday)."""
    current = base_date or date.today()
    days_ahead = target_weekday_idx - current.weekday()
    if days_ahead < 0:
        days_ahead += 7
    return current + timedelta(days=days_ahead)

def generate_faculty_ical(
    faculty: Any,
    assignments: List[Dict[str, Any]],
    courses_by_id: Dict[str, Any],
    rooms_by_id: Dict[str, Any],
    sections_by_id: Dict[str, Any],
    config: Any,
    term_name: str = "Academic Term"
) -> str:
    """Generate an RFC 5545 VCALENDAR stream for a faculty member's teaching schedule."""
    slots = generate_time_slots(config)
    slots_by_index = {s.index: s for s in slots}

    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    term_end_date = (date.today() + timedelta(days=120)).strftime("%Y%m%dT235959Z")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AutoSchedule//Academic Timetable Engine//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Faculty Schedule - {faculty.name}",
        f"X-WR-CALDESC:Teaching timetable for {faculty.name} ({term_name})",
        "X-WR-TIMEZONE:Asia/Kolkata",
    ]

    for a in assignments:
        day = a.get("day", "Monday")
        slot_idx = a.get("start_slot_index", 0)
        duration = a.get("duration_slots", 1)
        sess_id = a.get("session_id", "session")

        start_slot = slots_by_index.get(slot_idx)
        end_slot = slots_by_index.get(slot_idx + duration - 1) or start_slot
        if not start_slot or not end_slot:
            continue

        weekday_idx = DAY_NAME_TO_WEEKDAY.get(day, 0)
        event_date = get_next_weekday_date(weekday_idx)

        # Parse start and end times (format HH:MM)
        start_h, start_m = map(int, start_slot.start_time.split(":"))
        end_h, end_m = map(int, end_slot.end_time.split(":"))

        dtstart_str = f"{event_date.strftime('%Y%m%d')}T{start_h:02d}{start_m:02d}00"
        dtend_str = f"{event_date.strftime('%Y%m%d')}T{end_h:02d}{end_m:02d}00"

        # Resolve metadata
        course = None
        c_id = a.get("course_id")
        if c_id and c_id in courses_by_id:
            course = courses_by_id[c_id]
        else:
            # Fallback search by session prefix
            for cid, c in courses_by_id.items():
                if sess_id.startswith(cid):
                    course = c
                    break

        course_code = course.code if course else sess_id
        course_name = course.name if course else "Scheduled Lecture"
        course_type = getattr(course, "room_type", "THEORY")

        room = rooms_by_id.get(a.get("room_id"))
        room_name = room.name if room else (a.get("room_id") or "Unassigned Room")
        room_category = room.category if room and room.category else "Academic Room"

        sec = sections_by_id.get(a.get("section_id"))
        section_name = sec.name if sec else (a.get("section_id") or "Section")

        uid = f"{sess_id}-{day}-slot{slot_idx}-{faculty.id}@autoschedule.edu"
        summary = f"{course_code}: {course_name} ({section_name})"
        location = f"{room_name} ({room_category})"
        description = (
            f"Course: {course_name} ({course_code})\\n"
            f"Cohort: Section {section_name}\\n"
            f"Room: {room_name}\\n"
            f"Type: {course_type}\\n"
            f"Term: {term_name}"
        )
        rrule_day = DAY_TO_RRULE_BYDAY.get(day, "MO")

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            f"DTSTART:{dtstart_str}",
            f"DTEND:{dtend_str}",
            f"RRULE:FREQ=WEEKLY;BYDAY={rrule_day};UNTIL={term_end_date}",
            f"SUMMARY:{summary}",
            f"LOCATION:{location}",
            f"DESCRIPTION:{description}",
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "END:VEVENT"
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"

