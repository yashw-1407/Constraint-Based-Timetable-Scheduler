"""
soft_constraints.py - Soft constraint scoring for the scheduling engine.

Soft constraints are preferences that improve timetable quality but do NOT
prevent generation. The scheduler still produces a feasible timetable even
if some soft preferences cannot be satisfied.

Implemented soft constraints:
  1. Subject distribution: Distribute subjects across the week.
  2. No same subject same day: Avoid scheduling the same subject twice on
     the same day for the same section.
  3. Minimize student gaps: Reduce free periods between classes for students.
  4. Faculty workload target: Keep faculty weekly hours close to ~20h.
  5. Faculty daily balance: Balance daily workload across the week.
  6. Consecutive faculty limit: Avoid >3 consecutive classes for faculty.
  7. Room utilization: Even utilization across available rooms.

Each individual score is a sub-component. The total is a percentage out of 100.
"""

import math
from collections import defaultdict
from typing import List
from models import Assignment, ScheduleSession, WorkingConfig, TimeSlot


def compute_total_soft_score(assignments: List[Assignment],
                             sessions: List[ScheduleSession],
                             config: WorkingConfig,
                             time_slots: List[TimeSlot]) -> dict:
    """Compute all soft constraint scores and return a summary.

    Args:
        assignments: List of Assignment objects from the scheduler.
        sessions: List of all ScheduleSession objects.
        config: The WorkingConfig used for scheduling.
        time_slots: The generated time slots.

    Returns:
        Dictionary with 'total_score', 'max_possible', 'percentage',
        and 'details' containing per-constraint breakdowns.
    """
    sessions_by_id = {s.id: s for s in sessions}

    # --- Aggregate data ---
    section_subject_day_counts = defaultdict(int)  # (section, code, day) -> count
    section_day_slots = defaultdict(list)           # (section, day) -> [slot_indices]
    faculty_total_hours = defaultdict(int)          # faculty -> total slots
    faculty_day_slots = defaultdict(list)           # (faculty, day) -> [slot_indices]
    room_usage = defaultdict(int)                   # room_id -> total slots

    for assign in assignments:
        sess = sessions_by_id.get(assign.session_id)
        if not sess:
            continue

        day = assign.day
        start = assign.start_slot_index

        # Only count theory for same-subject-same-day (labs are expected to be long)
        if sess.course_type == 'THEORY':
            section_subject_day_counts[(sess.section_id, sess.course_code, day)] += 1

        for offset in range(sess.duration_slots):
            slot_idx = start + offset
            section_day_slots[(sess.section_id, day)].append(slot_idx)
            for fid in sess.faculty_ids:
                faculty_total_hours[fid] += 1
                faculty_day_slots[(fid, day)].append(slot_idx)
            room_usage[assign.room_id] += 1

    max_possible = 100

    # --- 1. Subject distribution (max 20) ---
    # Penalize theory sessions of the same subject scheduled on the same day
    same_day_violations = sum(
        count - 1
        for count in section_subject_day_counts.values()
        if count > 1
    )
    dist_score = max(0, 20 - same_day_violations * 4)

    # --- 2. Same subject same day (max 15) ---
    same_subj_score = max(0, 15 - same_day_violations * 3)

    # --- 3. Minimize student gaps (max 15) ---
    gap_penalty = 0
    for (sec, day), indices in section_day_slots.items():
        indices.sort()
        for i in range(len(indices) - 1):
            gap = indices[i + 1] - indices[i] - 1
            if gap > 0:
                gap_penalty += gap
    gaps_score = max(0, 15 - gap_penalty * 2)

    # --- 4. Faculty workload target ~20h (max 15) ---
    workload_penalty = 0
    if faculty_total_hours:
        for f_id, count in faculty_total_hours.items():
            workload_penalty += abs(count - 20)
        workload_penalty /= len(faculty_total_hours)
    wl_score = max(0, 15 - int(workload_penalty))

    # --- 5. Faculty daily balance (max 10) ---
    # Low variance in daily hours across the week is better
    bal_penalty = 0
    num_days = len(config.working_days)
    if num_days > 0:
        for f_id in set(k[0] for k in faculty_day_slots.keys()):
            daily_counts = []
            for day in config.working_days:
                daily_counts.append(len(faculty_day_slots.get((f_id, day), [])))
            if daily_counts:
                mean = sum(daily_counts) / len(daily_counts)
                variance = sum((c - mean) ** 2 for c in daily_counts) / len(daily_counts)
                bal_penalty += math.sqrt(variance)
        if faculty_total_hours:
            bal_penalty /= len(faculty_total_hours)
    bal_score = max(0, 10 - int(bal_penalty * 2))

    # --- 6. Consecutive faculty limit (max 15) ---
    # Penalize faculty teaching more than 3 consecutive slots
    cons_penalty = 0
    for (fac, day), indices in faculty_day_slots.items():
        indices.sort()
        streak = 1
        for i in range(len(indices) - 1):
            if indices[i + 1] == indices[i] + 1:
                streak += 1
            else:
                if streak > 3:
                    cons_penalty += (streak - 3)
                streak = 1
        if streak > 3:
            cons_penalty += (streak - 3)
    cons_score = max(0, 15 - cons_penalty * 3)

    # --- 7. Room utilization balance (max 10) ---
    room_score = 10
    if room_usage:
        values = list(room_usage.values())
        avg = sum(values) / len(values)
        if avg > 0:
            variance = sum((v - avg) ** 2 for v in values) / len(values)
            cv = math.sqrt(variance) / avg
            room_score = max(0, 10 - int(cv * 10))

    total = dist_score + same_subj_score + gaps_score + wl_score + bal_score + cons_score + room_score

    return {
        'total_score': total,
        'max_possible': max_possible,
        'percentage': round((total / max_possible) * 100, 1),
        'details': {
            'subject_distribution': {
                'score': dist_score, 'max': 20,
                'description': 'Distributes subjects evenly across days'
            },
            'no_same_subject_same_day': {
                'score': same_subj_score, 'max': 15,
                'description': 'Avoids same subject multiple times per day'
            },
            'minimize_student_gaps': {
                'score': gaps_score, 'max': 15,
                'description': 'Reduces free periods between classes'
            },
            'faculty_workload_target': {
                'score': wl_score, 'max': 15,
                'description': 'Faculty weekly hours close to 20h target'
            },
            'faculty_daily_balance': {
                'score': bal_score, 'max': 10,
                'description': 'Balanced daily workload for faculty'
            },
            'consecutive_faculty_limit': {
                'score': cons_score, 'max': 15,
                'description': 'Limits consecutive classes for faculty to 3'
            },
            'room_utilization': {
                'score': room_score, 'max': 10,
                'description': 'Even utilization across rooms'
            },
        }
    }
