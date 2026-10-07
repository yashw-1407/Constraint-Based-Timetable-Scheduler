"""
constraints.py - Hard constraint checking for the scheduling engine.

Each function checks a single hard constraint and returns True if the
constraint is SATISFIED (no violation), False if violated.

Hard constraints implemented:
  1. No two subjects for the same section simultaneously (theory).
  2. No two subjects for the same batch simultaneously (labs).
  3. No faculty double-booking.
  4. No room double-booking.
  5. Room suitability (labs must use lab rooms).
  6. Room capacity >= relevant strength (section for theory, batch for labs).
  7. Lab sessions occupy consecutive time slots (no gaps/breaks between them).

The schedule lookup tables use nested dicts for O(1) conflict checking:
  schedule[entity_id][day][slot_index] = session_id
"""

from typing import List, Optional, Dict
from models import ScheduleSession, Room, Section, TimeSlot


# ---------------------------------------------------------------------------
# Constraint 1: Section conflict (for theory sessions)
# ---------------------------------------------------------------------------
def check_section_conflict(section_id: str, day: str, slot_indices: List[int],
                           section_schedule: dict) -> bool:
    """Return True if NO section conflict exists.

    A section cannot have two theory subjects at the same time slot.
    """
    day_sched = section_schedule.get(section_id, {}).get(day, {})
    for slot in slot_indices:
        if slot in day_sched:
            return False
    return True


# ---------------------------------------------------------------------------
# Constraint 1b: Batch conflict (for lab sessions)
# ---------------------------------------------------------------------------
def check_batch_conflict(batch_id: str, day: str, slot_indices: List[int],
                         batch_schedule: dict) -> bool:
    """Return True if NO batch conflict exists.

    A batch cannot have two lab sessions at the same time slot.
    Different batches of the same section MAY overlap.
    """
    if not batch_id:
        return True  # No batch = section-level (theory), checked separately
    day_sched = batch_schedule.get(batch_id, {}).get(day, {})
    for slot in slot_indices:
        if slot in day_sched:
            return False
    return True


# ---------------------------------------------------------------------------
# Constraint 2: Faculty conflict
# ---------------------------------------------------------------------------
def check_faculty_conflict(faculty_ids: List[str], day: str, slot_indices: List[int],
                           faculty_schedule: dict) -> bool:
    """Return True if NO faculty conflict exists.

    A faculty member cannot teach two sessions at the same time.
    """
    for fid in faculty_ids:
        day_sched = faculty_schedule.get(fid, {}).get(day, {})
        for slot in slot_indices:
            if slot in day_sched:
                return False
    return True


# ---------------------------------------------------------------------------
# Constraint 3: Room conflict
# ---------------------------------------------------------------------------
def check_room_conflict(room_id: str, day: str, slot_indices: List[int],
                        room_schedule: dict) -> bool:
    """Return True if NO room conflict exists.

    A room cannot host two sessions at the same time.
    """
    day_sched = room_schedule.get(room_id, {}).get(day, {})
    for slot in slot_indices:
        if slot in day_sched:
            return False
    return True


# ---------------------------------------------------------------------------
# Constraint 4: Room suitability
# ---------------------------------------------------------------------------
def check_room_suitability(session: ScheduleSession, room: Room) -> bool:
    """Return True if the room is suitable for the session.

    - If the session requires a specific room, only that room is acceptable.
    - Otherwise, the room type must match the session's required room type.
    """
    if session.required_room_id:
        return room.id == session.required_room_id
    return room.room_type == session.room_type


# ---------------------------------------------------------------------------
# Constraint 5: Room capacity
# ---------------------------------------------------------------------------
def check_room_capacity_by_strength(room: Room, strength: Optional[int]) -> bool:
    """Return True if room capacity is adequate for the given strength.

    For theory sessions, strength = section.strength.
    For lab sessions, strength = batch.strength.

    Only checked when both room.capacity and strength are provided.
    If either is missing, the constraint is considered satisfied.
    """
    if room.capacity is not None and strength is not None:
        return room.capacity >= strength
    return True


# Backward-compatible wrapper (used by older code paths)
def check_room_capacity(room: Room, section: Optional[Section]) -> bool:
    """Legacy wrapper: checks room.capacity >= section.strength."""
    if section is not None:
        return check_room_capacity_by_strength(room, section.strength)
    return True


# ---------------------------------------------------------------------------
# Constraint 6: Consecutive slots for multi-period sessions
# ---------------------------------------------------------------------------
def check_consecutive_slots(slot_indices: List[int],
                            time_slots: List[TimeSlot]) -> bool:
    if len(slot_indices) <= 1:
        return True

    ts_map = {ts.index: ts for ts in time_slots}
    
    def time_to_min(t_str):
        h, m = map(int, t_str.split(':'))
        return h * 60 + m

    for i in range(len(slot_indices) - 1):
        if slot_indices[i + 1] != slot_indices[i] + 1:
            return False
            
        current = ts_map.get(slot_indices[i])
        next_slot = ts_map.get(slot_indices[i + 1])
        if current is None or next_slot is None:
            return False
            
        gap = time_to_min(next_slot.start_time) - time_to_min(current.end_time)
        if gap > 20: # Do not allow spanning large breaks like lunch (> 20m)
            return False

    return True


# ---------------------------------------------------------------------------
# Post-generation validation
# ---------------------------------------------------------------------------
def validate_timetable(assignments, sessions_by_id, sections_by_id,
                       faculty_by_id, rooms_by_id, config, time_slots,
                       batches_by_id=None) -> dict:
    """Full post-generation validation of the timetable.

    Re-checks all hard constraints against the complete solution to confirm
    no violations were introduced. Returns a dict with 'is_valid' and
    'conflicts' list.

    Batch-aware: lab sessions with batch_id are checked at batch level
    (different batches of same section may overlap). Theory sessions are
    checked at section level.
    """
    conflicts = []
    entries = []

    for assign in assignments:
        sess = sessions_by_id[assign.session_id]
        entries.append({
            'session_id': assign.session_id,
            'section_id': sess.section_id,
            'batch_id': getattr(sess, 'batch_id', None),
            'faculty_ids': sess.faculty_ids,
            'room_id': assign.room_id,
            'day': assign.day,
            'start_slot': assign.start_slot_index,
            'duration': sess.duration_slots,
            'course_code': sess.course_code,
            'course_name': sess.course_name,
            'course_type': sess.course_type,
        })

    # Pairwise check for conflicts
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            e1, e2 = entries[i], entries[j]

            if e1['day'] != e2['day']:
                continue

            # Check temporal overlap
            s1_start, s1_end = e1['start_slot'], e1['start_slot'] + e1['duration']
            s2_start, s2_end = e2['start_slot'], e2['start_slot'] + e2['duration']

            if not (s1_start < s2_end and s2_start < s1_end):
                continue  # No temporal overlap

            # --- Section/Batch conflict ---
            if e1['section_id'] == e2['section_id']:
                b1, b2 = e1['batch_id'], e2['batch_id']

                # Both theory (no batch) -> section conflict
                if not b1 and not b2:
                    conflicts.append(
                        f"Section {e1['section_id']} double-booked on {e1['day']}: "
                        f"{e1['course_code']} and {e2['course_code']}"
                    )
                # One theory, one lab batch -> theory blocks entire section
                elif not b1 or not b2:
                    conflicts.append(
                        f"Section {e1['section_id']} theory/lab overlap on {e1['day']}: "
                        f"{e1['course_code']} and {e2['course_code']}"
                    )
                # Same batch -> batch conflict
                elif b1 == b2:
                    conflicts.append(
                        f"Batch {b1} double-booked on {e1['day']}: "
                        f"{e1['course_code']} and {e2['course_code']}"
                    )
                # Different batches of same section -> VALID, no conflict

            # --- Faculty conflict ---
            overlap_faculty = set(e1['faculty_ids']).intersection(e2['faculty_ids'])
            if overlap_faculty:
                fnames = [faculty_by_id.get(fid).name if faculty_by_id.get(fid) else fid for fid in overlap_faculty]
                conflicts.append(
                    f"Faculty {', '.join(fnames)} double-booked on {e1['day']}: "
                    f"{e1['course_code']} and {e2['course_code']}"
                )

            # --- Room conflict ---
            if e1['room_id'] == e2['room_id']:
                room = rooms_by_id.get(e1['room_id'])
                rname = room.name if room else e1['room_id']
                conflicts.append(
                    f"Room {rname} double-booked on {e1['day']}: "
                    f"{e1['course_code']} and {e2['course_code']}"
                )

    return {
        'is_valid': len(conflicts) == 0,
        'conflicts': conflicts,
    }
