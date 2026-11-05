"""adjuster.py - Interactive Timetable Schedule Adjustment & Move Validation.

Implements real-time hard-constraint validation and atomic reassignment
for individual schedule sessions and pairwise session swaps.
Follows DBMS ACID rollback principles to guarantee zero constraint corruptions.
"""

from typing import Tuple, Dict, Any, Optional, List
from models import ScheduleSession, Room, CourseType, Assignment
from constraints import (
    check_consecutive_slots,
    check_room_suitability,
    check_section_conflict,
    check_batch_conflict,
    check_faculty_conflict,
    check_room_conflict
)
from soft_constraints import compute_total_soft_score


def validate_move(
    engine,
    session_id: str,
    target_day: str,
    target_start_slot: int,
    target_room_id: str
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate whether moving a session to a target day, slot, and room is conflict-free."""
    if not engine:
        return False, "No active scheduling engine initialized.", {"code": "NO_ENGINE"}

    session = engine.sessions_by_id.get(session_id)
    if not session:
        return False, f"Session '{session_id}' not found.", {"code": "SESSION_NOT_FOUND"}

    # 1. Day boundary check
    if target_day not in engine.config.working_days:
        return False, (
            f"Day '{target_day}' is not an institutional working day "
            f"({', '.join(engine.config.working_days)})."
        ), {"code": "INVALID_DAY"}

    # 2. Slot bounds check
    duration = session.duration_slots
    end_slot = target_start_slot + duration
    if target_start_slot < 0 or end_slot > len(engine.time_slots):
        return False, (
            f"Target slot span [{target_start_slot}:{end_slot}] exceeds "
            f"operating hours (max {len(engine.time_slots)} slots)."
        ), {"code": "SLOT_OUT_OF_BOUNDS"}

    slot_indices = list(range(target_start_slot, end_slot))

    # 3. Lunch break and consecutive slots check
    if not check_consecutive_slots(slot_indices, engine.time_slots):
        return False, (
            "Target time slot overlaps the institutional lunch break "
            "or spans non-contiguous periods."
        ), {"code": "LUNCH_OR_BREAK_OVERLAP"}

    # 4. Target room existence and suitability
    target_room = next((r for r in engine.rooms if r.id == target_room_id), None)
    if not target_room:
        return False, f"Target room '{target_room_id}' does not exist.", {"code": "ROOM_NOT_FOUND"}

    if target_room.id in getattr(engine, 'dedicated_room_ids', set()) and session.required_room_id != target_room.id:
        return False, f"Room '{target_room.name}' is dedicated to another course.", {"code": "DEDICATED_ROOM_CONFLICT"}

    home_room_id = None
    if not session.required_room_id and session.course_type == CourseType.THEORY:
        section = engine.sections_by_id.get(session.section_id)
        if section and getattr(section, 'home_room_id', None):
            home_room_id = section.home_room_id
    if home_room_id and target_room.id != home_room_id:
        home_r = next((r for r in engine.rooms if r.id == home_room_id), None)
        return False, f"Section {session.section_id} is locked to home room {home_r.name if home_r else home_room_id}.", {"code": "HOME_ROOM_MISMATCH"}

    if not check_room_suitability(session, target_room):
        return False, (
            f"Room '{target_room.name}' ({target_room.room_type.value}) is not suitable "
            f"for {session.course_code} ({session.course_type.value})."
        ), {"code": "ROOM_SUITABILITY_MISMATCH"}

    strength = engine._get_scheduling_strength(session)
    if strength and target_room.capacity < strength:
        return False, (
            f"Room '{target_room.name}' capacity ({target_room.capacity}) is smaller "
            f"than cohort strength ({strength})."
        ), {"code": "CAPACITY_EXCEEDED"}

    # 5. Check hard constraints with atomic unassign & restore
    curr_assign = engine.assignments.get(session.id)
    if curr_assign:
        engine._unassign(session)

    try:
        is_valid, fail_reason = engine._check_hard_constraints(session, target_day, slot_indices, target_room_id)
        if not is_valid:
            msg = _diagnose_move_conflict(engine, session, target_day, slot_indices, target_room_id, fail_reason)
            return False, msg, {"code": fail_reason}
    finally:
        # Restore current assignment to preserve solver invariants
        if curr_assign:
            engine._assign(session, curr_assign.day, curr_assign.start_slot_index, curr_assign.room_id)

    return True, "Target slot is valid and satisfies all 6 hard constraints.", {
        "code": "VALID",
        "day": target_day,
        "slot_indices": slot_indices,
        "room_id": target_room_id
    }


def execute_move(
    engine,
    session_id: str,
    target_day: str,
    target_start_slot: int,
    target_room_id: str,
    app_data: Dict[str, Any]
) -> Tuple[bool, str, Dict[str, Any]]:
    """Commit a move if conflict-free, recalculate soft scores, and persist changes."""
    valid, msg, meta = validate_move(engine, session_id, target_day, target_start_slot, target_room_id)
    if not valid:
        return False, msg, meta

    session = engine.sessions_by_id[session_id]

    # Perform atomic unassign
    if session.id in engine.assignments:
        engine._unassign(session)

    # Perform new assignment
    engine._assign(session, target_day, target_start_slot, target_room_id)

    # Recompute total soft score
    new_soft_score = compute_total_soft_score(
        list(engine.assignments.values()),
        engine.sessions,
        engine.config,
        engine.time_slots
    )

    # Synchronize app_data
    if 'result' in app_data and app_data['result']:
        app_data['result']['assignments'] = engine._format_assignments()
        app_data['result']['assignments_data'] = [a.to_dict() for a in engine.assignments.values()]
        app_data['result']['soft_score'] = new_soft_score

        # If schedule was published, mark as modified/draft
        if app_data.get('publishing'):
            app_data['publishing']['status'] = 'DRAFT'
            app_data['publishing']['modified_after_publish'] = True

    from database import save_data
    save_data(app_data)

    return True, "Session relocated successfully.", {
        "code": "SUCCESS",
        "assignment": engine.assignments[session.id].to_dict(),
        "soft_score": new_soft_score
    }


def execute_swap(
    engine,
    session_a_id: str,
    session_b_id: str,
    app_data: Dict[str, Any]
) -> Tuple[bool, str, Dict[str, Any]]:
    """Atomically swap the time/room assignments of two sessions if mutually conflict-free."""
    if not engine:
        return False, "No active scheduling engine initialized.", {"code": "NO_ENGINE"}

    session_a = engine.sessions_by_id.get(session_a_id)
    session_b = engine.sessions_by_id.get(session_b_id)
    if not session_a or not session_b:
        return False, "One or both sessions not found.", {"code": "SESSION_NOT_FOUND"}

    assign_a = engine.assignments.get(session_a_id)
    assign_b = engine.assignments.get(session_b_id)
    if not assign_a or not assign_b:
        return False, "Both sessions must have active assignments to perform a swap.", {"code": "UNASSIGNED_SESSION"}

    # Validate duration match
    if session_a.duration_slots != session_b.duration_slots:
        return False, (
            f"Cannot swap sessions of unequal durations ({session_a.duration_slots} vs {session_b.duration_slots} slots)."
        ), {"code": "DURATION_MISMATCH"}

    # Unassign both
    engine._unassign(session_a)
    engine._unassign(session_b)

    slots_b = list(range(assign_b.start_slot_index, assign_b.start_slot_index + session_a.duration_slots))
    slots_a = list(range(assign_a.start_slot_index, assign_a.start_slot_index + session_b.duration_slots))

    # Check session_a at position B
    valid_a, reason_a = engine._check_hard_constraints(session_a, assign_b.day, slots_b, assign_b.room_id)
    if valid_a:
        engine._assign(session_a, assign_b.day, assign_b.start_slot_index, assign_b.room_id)
        valid_b, reason_b = engine._check_hard_constraints(session_b, assign_a.day, slots_a, assign_a.room_id)
        if valid_b:
            # Assign B to position A
            engine._assign(session_b, assign_a.day, assign_a.start_slot_index, assign_a.room_id)

            new_soft = compute_total_soft_score(
                list(engine.assignments.values()),
                engine.sessions,
                engine.config,
                engine.time_slots
            )
            if 'result' in app_data and app_data['result']:
                app_data['result']['assignments'] = engine._format_assignments()
                app_data['result']['assignments_data'] = [a.to_dict() for a in engine.assignments.values()]
                app_data['result']['soft_score'] = new_soft
                if app_data.get('publishing'):
                    app_data['publishing']['status'] = 'DRAFT'

            from database import save_data
            save_data(app_data)
            return True, "Sessions swapped successfully.", {
                "code": "SUCCESS",
                "soft_score": new_soft
            }
        else:
            # Rollback session_a from B
            engine._unassign(session_a)

    # Rollback both to original positions
    engine._assign(session_a, assign_a.day, assign_a.start_slot_index, assign_a.room_id)
    engine._assign(session_b, assign_b.day, assign_b.start_slot_index, assign_b.room_id)

    fail_msg = reason_a if not valid_a else reason_b
    return False, f"Swap rejected due to hard constraint collision: {fail_msg}.", {"code": fail_msg}


def _diagnose_move_conflict(
    engine,
    session: ScheduleSession,
    target_day: str,
    slot_indices: List[int],
    target_room_id: str,
    fail_reason: str
) -> str:
    """Produce clear, human-readable explanations of specific scheduling collisions."""
    times = f"{engine.time_slots[slot_indices[0]].start_time} - {engine.time_slots[slot_indices[-1]].end_time}"

    if fail_reason == 'FACULTY_CONFLICT':
        for fid in session.faculty_ids:
            fac_sched = engine.faculty_schedule.get(fid, {}).get(target_day, {})
            for slot in slot_indices:
                if slot in fac_sched:
                    conflicting_sess_id = fac_sched[slot]
                    conflicting_sess = engine.sessions_by_id.get(conflicting_sess_id)
                    fac = next((f for f in engine.faculty if f.id == fid), None)
                    fac_name = fac.name if fac else fid
                    subj = conflicting_sess.course_code if conflicting_sess else conflicting_sess_id
                    return f"Faculty conflict: {fac_name} is already teaching {subj} during {target_day} ({times})."
        return f"Faculty conflict: One or more instructors are already engaged during {target_day} ({times})."

    elif fail_reason == 'ROOM_CONFLICT':
        room_sched = engine.room_schedule.get(target_room_id, {}).get(target_day, {})
        room = next((r for r in engine.rooms if r.id == target_room_id), None)
        room_name = room.name if room else target_room_id
        for slot in slot_indices:
            if slot in room_sched:
                conflicting_sess_id = room_sched[slot]
                conflicting_sess = engine.sessions_by_id.get(conflicting_sess_id)
                subj = conflicting_sess.course_code if conflicting_sess else conflicting_sess_id
                return f"Room collision: {room_name} is already occupied by {subj} during {target_day} ({times})."
        return f"Room collision: {room_name} is occupied during {target_day} ({times})."

    elif fail_reason in ('SECTION_CONFLICT', 'BATCH_CONFLICT'):
        sec = engine.sections_by_id.get(session.section_id)
        sec_name = sec.name if sec else session.section_id
        sec_sched = engine.section_schedule.get(session.section_id, {}).get(target_day, {})
        for slot in slot_indices:
            if slot in sec_sched:
                conflicting_sess_id = sec_sched[slot]
                conflicting_sess = engine.sessions_by_id.get(conflicting_sess_id)
                subj = conflicting_sess.course_code if conflicting_sess else conflicting_sess_id
                return f"Cohort collision: Section {sec_name} already has {subj} scheduled during {target_day} ({times})."
        return f"Cohort collision: Section/Batch is engaged in another class during {target_day} ({times})."

    return f"Hard constraint violation ({fail_reason}) on {target_day} ({times})."

