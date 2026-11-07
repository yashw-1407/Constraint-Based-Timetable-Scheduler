"""
scheduler.py - Constraint Satisfaction Problem (CSP) Timetable Engine

Handles:
1. Dynamic time-slot generation based on working hours, lunch, and breaks.
2. Hard constraint validation (faculty, rooms, sections, batches, capacities).
3. Soft constraint evaluation for schedule quality.
4. CSP Backtracking search with MRV (Minimum Remaining Values) heuristic.
5. Grid generation for master, section, faculty, and room views.
"""

import time
import math
from collections import defaultdict
from typing import List, Tuple, Optional, Dict
from models import (WorkingConfig, Course, Room, Faculty, Section, Batch,
                    ScheduleSession, Assignment, CourseType, RoomType, TimeSlot)


# ---------------------------------------------------------------------------
# 1. Dynamic Time-Slot Generator
# ---------------------------------------------------------------------------
def time_to_minutes(time_str: str) -> int:
    """Convert 'HH:MM' string to minutes from midnight."""
    h, m = map(int, time_str.strip().split(':'))
    return h * 60 + m


def minutes_to_time(minutes: int) -> str:
    """Convert minutes from midnight to 'HH:MM' string."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def generate_time_slots(config: WorkingConfig) -> List[TimeSlot]:
    """Generate time slots excluding lunch and break intervals."""
    start = time_to_minutes(config.start_time)
    end = time_to_minutes(config.end_time)
    duration = config.slot_duration_minutes

    blocked = []
    if config.lunch_start and config.lunch_end:
        blocked.append((time_to_minutes(config.lunch_start), time_to_minutes(config.lunch_end)))
    for b in (config.breaks or []):
        b_start = b.get('start_time', b.get('start', ''))
        b_end = b.get('end_time', b.get('end', ''))
        if b_start and b_end:
            blocked.append((time_to_minutes(b_start), time_to_minutes(b_end)))
    blocked.sort()

    slots: List[TimeSlot] = []
    cursor = start

    while cursor + duration <= end:
        slot_end = cursor + duration
        overlap = False
        skip_to = cursor

        for (b_start, b_end) in blocked:
            if cursor < b_end and slot_end > b_start:
                overlap = True
                skip_to = max(skip_to, b_end)

        if overlap:
            cursor = skip_to
            continue

        slots.append(TimeSlot(
            index=len(slots),
            start_time=minutes_to_time(cursor),
            end_time=minutes_to_time(slot_end)
        ))
        cursor = slot_end

    return slots


# ---------------------------------------------------------------------------
# 2. Hard Constraint Checks
# ---------------------------------------------------------------------------
def check_section_conflict(section_id: str, day: str, slot_indices: List[int],
                           section_schedule: dict) -> bool:
    day_sched = section_schedule.get(section_id, {}).get(day, {})
    return not any(slot in day_sched for slot in slot_indices)


def check_batch_conflict(batch_id: Optional[str], day: str, slot_indices: List[int],
                         batch_schedule: dict) -> bool:
    if not batch_id:
        return True
    day_sched = batch_schedule.get(batch_id, {}).get(day, {})
    return not any(slot in day_sched for slot in slot_indices)


def check_faculty_conflict(faculty_ids: List[str], day: str, slot_indices: List[int],
                           faculty_schedule: dict) -> bool:
    for fid in faculty_ids:
        day_sched = faculty_schedule.get(fid, {}).get(day, {})
        if any(slot in day_sched for slot in slot_indices):
            return False
    return True


def check_room_conflict(room_id: str, day: str, slot_indices: List[int],
                        room_schedule: dict) -> bool:
    day_sched = room_schedule.get(room_id, {}).get(day, {})
    return not any(slot in day_sched for slot in slot_indices)


def check_room_suitability(session: ScheduleSession, room: Room) -> bool:
    if session.required_room_id:
        return room.id == session.required_room_id
    return room.room_type == session.room_type


def check_room_capacity_by_strength(room: Room, strength: Optional[int]) -> bool:
    if strength is None or room.capacity is None:
        return True
    return room.capacity >= strength


def check_consecutive_slots(slot_indices: List[int], time_slots: List[TimeSlot]) -> bool:
    if len(slot_indices) <= 1:
        return True
    ts_map = {ts.index: ts for ts in time_slots}
    for i in range(len(slot_indices) - 1):
        curr_idx = slot_indices[i]
        next_idx = slot_indices[i + 1]
        if next_idx != curr_idx + 1:
            return False
        curr_ts = ts_map.get(curr_idx)
        next_ts = ts_map.get(next_idx)
        if not curr_ts or not next_ts:
            return False
        gap = time_to_minutes(next_ts.start_time) - time_to_minutes(curr_ts.end_time)
        # Allow contiguous slots or slots separated by a short tea break (<= 20m), but never lunch
        if gap < 0 or gap > 20:
            return False
    return True


def validate_timetable(assignments: List[Assignment], sessions_by_id: dict,
                       sections_by_id: dict, faculty_by_id: dict, rooms_by_id: dict,
                       config: WorkingConfig, time_slots: List[TimeSlot],
                       batches_by_id: dict = None) -> dict:
    conflicts = []
    section_occupancy = defaultdict(lambda: defaultdict(list))
    batch_occupancy = defaultdict(lambda: defaultdict(list))
    faculty_occupancy = defaultdict(lambda: defaultdict(list))
    room_occupancy = defaultdict(lambda: defaultdict(list))

    for assign in assignments:
        sess = sessions_by_id.get(assign.session_id)
        if not sess:
            continue
        slots = list(range(assign.start_slot_index, assign.start_slot_index + sess.duration_slots))

        # Check suitability & capacity
        room = rooms_by_id.get(assign.room_id)
        if room:
            if not check_room_suitability(sess, room):
                conflicts.append(f"Room type mismatch for session {sess.id} in room {room.id}")
            strength = None
            if sess.batch_id and batches_by_id and sess.batch_id in batches_by_id:
                strength = batches_by_id[sess.batch_id].strength
            elif sess.section_id in sections_by_id:
                strength = sections_by_id[sess.section_id].strength
            if not check_room_capacity_by_strength(room, strength):
                conflicts.append(f"Room {room.id} capacity ({room.capacity}) < required strength ({strength}) for {sess.id}")

        if not check_consecutive_slots(slots, time_slots):
            conflicts.append(f"Session {sess.id} does not occupy consecutive slots on {assign.day}")

        for s in slots:
            # Section & Batch conflicts
            if sess.batch_id:
                batch_occupancy[(sess.batch_id, assign.day)][s].append(sess.id)
            else:
                section_occupancy[(sess.section_id, assign.day)][s].append(sess.id)

            # Faculty conflicts
            for fid in sess.faculty_ids:
                faculty_occupancy[(fid, assign.day)][s].append(sess.id)

            # Room conflicts
            room_occupancy[(assign.room_id, assign.day)][s].append(sess.id)

    for (sec, day), slots in section_occupancy.items():
        for s, sids in slots.items():
            if len(sids) > 1:
                conflicts.append(f"Section {sec} has {len(sids)} overlapping sessions on {day} slot {s}: {sids}")

    for (bat, day), slots in batch_occupancy.items():
        for s, sids in slots.items():
            if len(sids) > 1:
                conflicts.append(f"Batch {bat} has {len(sids)} overlapping sessions on {day} slot {s}: {sids}")

    for (fac, day), slots in faculty_occupancy.items():
        for s, sids in slots.items():
            if len(sids) > 1:
                conflicts.append(f"Faculty {fac} double-booked on {day} slot {s}: {sids}")

    for (rm, day), slots in room_occupancy.items():
        for s, sids in slots.items():
            if len(sids) > 1:
                conflicts.append(f"Room {rm} double-booked on {day} slot {s}: {sids}")

    return {
        'is_valid': len(conflicts) == 0,
        'conflicts': conflicts
    }


# ---------------------------------------------------------------------------
# 3. Soft Constraints Scoring
# ---------------------------------------------------------------------------
def compute_soft_score(assignments: List[Assignment], sessions: List[ScheduleSession],
                       config: WorkingConfig, time_slots: List[TimeSlot]) -> dict:
    sessions_by_id = {s.id: s for s in sessions}

    section_subject_day_counts = defaultdict(int)
    section_day_slots = defaultdict(list)
    faculty_total_hours = defaultdict(int)
    faculty_day_slots = defaultdict(list)
    room_usage = defaultdict(int)

    for assign in assignments:
        sess = sessions_by_id.get(assign.session_id)
        if not sess:
            continue
        day = assign.day
        start = assign.start_slot_index

        if sess.course_type == CourseType.THEORY:
            section_subject_day_counts[(sess.section_id, sess.course_code, day)] += 1

        for offset in range(sess.duration_slots):
            slot_idx = start + offset
            section_day_slots[(sess.section_id, day)].append(slot_idx)
            for fid in sess.faculty_ids:
                faculty_total_hours[fid] += 1
                faculty_day_slots[(fid, day)].append(slot_idx)
            room_usage[assign.room_id] += 1

    # 1. Subject distribution across days
    same_day_violations = sum(count - 1 for count in section_subject_day_counts.values() if count > 1)
    dist_score = max(0, 20 - same_day_violations * 4)

    # 2. No same subject twice same day
    same_subj_score = max(0, 15 - same_day_violations * 3)

    # 3. Minimize student gap periods
    gap_penalty = 0
    for (_, _), indices in section_day_slots.items():
        indices.sort()
        for i in range(len(indices) - 1):
            gap = indices[i + 1] - indices[i] - 1
            if gap > 0:
                gap_penalty += gap
    gaps_score = max(0, 15 - gap_penalty * 2)

    # 4. Faculty workload target (~20 hours)
    workload_penalty = 0
    if faculty_total_hours:
        for count in faculty_total_hours.values():
            workload_penalty += abs(count - 20)
        workload_penalty /= len(faculty_total_hours)
    wl_score = max(0, 15 - int(workload_penalty))

    # 5. Faculty daily balance
    bal_penalty = 0
    if config.working_days and faculty_day_slots:
        for fid in set(k[0] for k in faculty_day_slots.keys()):
            daily_counts = [len(faculty_day_slots.get((fid, d), [])) for d in config.working_days]
            mean = sum(daily_counts) / len(daily_counts)
            var = sum((c - mean) ** 2 for c in daily_counts) / len(daily_counts)
            bal_penalty += math.sqrt(var)
        if faculty_total_hours:
            bal_penalty /= len(faculty_total_hours)
    bal_score = max(0, 10 - int(bal_penalty * 2))

    # 6. Consecutive faculty limit (avoid >3 consecutive)
    cons_penalty = 0
    for (_, _), indices in faculty_day_slots.items():
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

    # 7. Room utilization balance
    room_score = 10
    if room_usage:
        vals = list(room_usage.values())
        avg = sum(vals) / len(vals)
        if avg > 0:
            var = sum((v - avg) ** 2 for v in vals) / len(vals)
            cv = math.sqrt(var) / avg
            room_score = max(0, 10 - int(cv * 10))

    total = dist_score + same_subj_score + gaps_score + wl_score + bal_score + cons_score + room_score
    max_possible = 100

    return {
        'total_score': total,
        'max_possible': max_possible,
        'percentage': round((total / max_possible) * 100, 1),
        'details': {
            'subject_distribution': {
                'score': dist_score, 'max': 20,
                'description': 'Distributes subjects across the week'
            },
            'no_same_subject_same_day': {
                'score': same_subj_score, 'max': 15,
                'description': 'Avoids multiple theory lectures of same course per day'
            },
            'minimize_student_gaps': {
                'score': gaps_score, 'max': 15,
                'description': 'Minimizes idle student gaps between classes'
            },
            'faculty_workload': {
                'score': wl_score, 'max': 15,
                'description': 'Maintains reasonable weekly faculty workload'
            },
            'faculty_daily_balance': {
                'score': bal_score, 'max': 10,
                'description': 'Balances daily faculty teaching load'
            },
            'consecutive_faculty_limit': {
                'score': cons_score, 'max': 15,
                'description': 'Avoids more than 3 consecutive teaching hours'
            },
            'room_utilization': {
                'score': room_score, 'max': 10,
                'description': 'Even distribution of room utilization'
            }
        }
    }


# ---------------------------------------------------------------------------
# 4. Scheduling Engine (CSP Backtracking Solver)
# ---------------------------------------------------------------------------
class SchedulingEngine:
    MAX_BACKTRACKS = 50000
    MAX_TIME_SECONDS = 30

    def __init__(self, config: WorkingConfig, courses: List[Course],
                 rooms: List[Room], faculty_list: List[Faculty],
                 sections: List[Section], batches: List[Batch] = None):
        self.config = config
        self.time_slots = generate_time_slots(config)
        self.rooms = rooms
        self.rooms_by_id = {r.id: r for r in rooms}
        self.sections_by_id = {s.id: s for s in sections}
        self.faculty_by_id = {f.id: f for f in faculty_list}
        self.courses_by_id = {c.id: c for c in courses}
        self.batches = batches or []
        self.batches_by_id = {b.id: b for b in self.batches}

        self.section_batches = {}
        for b in self.batches:
            self.section_batches.setdefault(b.section_id, []).append(b.id)

        self.sessions_by_id = {}
        self.sessions = self._create_sessions(courses)

        self.assignments = {}
        self.section_schedule = {}
        self.batch_schedule = {}
        self.faculty_schedule = {}
        self.room_schedule = {}

        self.backtrack_count = 0
        self.start_time = 0.0

    def _create_sessions(self, courses: List[Course]) -> List[ScheduleSession]:
        sessions = []
        multiplier = 60.0 / self.config.slot_duration_minutes

        for course in courses:
            req_room = self.rooms_by_id.get(course.required_room_id) if course.required_room_id else None

            # Theory sessions
            theory_hours = course.l + course.t
            if theory_hours > 0:
                hours_list = []
                rem = theory_hours
                while rem >= 1.0:
                    hours_list.append(1.0)
                    rem -= 1.0
                if rem > 0:
                    hours_list.append(rem)

                for i, hrs in enumerate(hours_list):
                    d_slots = max(1, int(round(hrs * multiplier)))
                    fac = course.faculty_ids[i % len(course.faculty_ids)] if course.faculty_ids else None
                    sess_req_room = course.required_room_id if (req_room and req_room.room_type == RoomType.THEORY_ROOM) or (not req_room and course.required_room_id) else None
                    sess = ScheduleSession(
                        id=f"{course.id}_T{i}",
                        course_id=course.id,
                        course_name=course.name,
                        course_code=course.code,
                        course_type=CourseType.THEORY,
                        section_id=course.section_id,
                        faculty_ids=[fac] if fac else [],
                        room_type=RoomType.THEORY_ROOM,
                        required_room_id=sess_req_room,
                        session_index=i,
                        duration_slots=d_slots,
                        batch_id=None
                    )
                    sessions.append(sess)
                    self.sessions_by_id[sess.id] = sess

            # Lab sessions
            if course.p > 0:
                batches = course.lab_batches if course.lab_batches else [None]
                d_slots = max(1, int(round(course.p * multiplier)))

                for b_idx, batch_id in enumerate(batches):
                    batch_facs = list(getattr(course, "assistant_faculty_ids", []))
                    if course.faculty_ids:
                        fac = course.faculty_ids[b_idx % len(course.faculty_ids)]
                        batch_facs = [fac] + batch_facs

                    sess_req_room = course.required_room_id if (req_room and req_room.room_type == RoomType.LAB) or (not req_room and course.required_room_id) else None
                    sess = ScheduleSession(
                        id=f"{course.id}_L{b_idx}",
                        course_id=course.id,
                        course_name=course.name,
                        course_code=course.code,
                        course_type=CourseType.LAB,
                        section_id=course.section_id,
                        faculty_ids=batch_facs,
                        room_type=RoomType.LAB,
                        required_room_id=sess_req_room,
                        session_index=0,
                        duration_slots=d_slots,
                        batch_id=batch_id
                    )
                    sessions.append(sess)
                    self.sessions_by_id[sess.id] = sess

        return sessions

    def _get_scheduling_strength(self, session: ScheduleSession) -> Optional[int]:
        if session.batch_id:
            batch = self.batches_by_id.get(session.batch_id)
            if batch and batch.strength is not None:
                return batch.strength
        section = self.sections_by_id.get(session.section_id)
        return section.strength if section else None

    def _get_suitable_rooms(self, session: ScheduleSession) -> List[Room]:
        suitable = []
        strength = self._get_scheduling_strength(session)

        home_room_id = None
        if not session.required_room_id and session.course_type == CourseType.THEORY:
            section = self.sections_by_id.get(session.section_id)
            if section and getattr(section, 'home_room_id', None):
                home_room_id = section.home_room_id

        for r in self.rooms:
            if home_room_id and r.id != home_room_id:
                continue
            if not check_room_suitability(session, r):
                continue
            if not check_room_capacity_by_strength(r, strength):
                continue
            suitable.append(r)

        return suitable

    def _get_domain(self, session: ScheduleSession) -> List[Tuple[str, int, str]]:
        domain = []
        suitable_rooms = self._get_suitable_rooms(session)
        max_slots = len(self.time_slots)

        for day in self.config.working_days:
            for start_idx in range(max_slots):
                end_idx = start_idx + session.duration_slots
                if end_idx > max_slots:
                    break
                if session.duration_slots > 1:
                    slot_indices = list(range(start_idx, end_idx))
                    if not check_consecutive_slots(slot_indices, self.time_slots):
                        continue
                for r in suitable_rooms:
                    domain.append((day, start_idx, r.id))

        return domain

    def _check_hard_constraints(self, session: ScheduleSession, day: str,
                                slot_indices: List[int], room_id: str) -> bool:
        if session.batch_id:
            if not check_batch_conflict(session.batch_id, day, slot_indices, self.batch_schedule):
                return False
            if not check_section_conflict(session.section_id, day, slot_indices, self.section_schedule):
                return False
        else:
            if not check_section_conflict(session.section_id, day, slot_indices, self.section_schedule):
                return False
            for bid in self.section_batches.get(session.section_id, []):
                if not check_batch_conflict(bid, day, slot_indices, self.batch_schedule):
                    return False

        if not check_faculty_conflict(session.faculty_ids, day, slot_indices, self.faculty_schedule):
            return False
        if not check_room_conflict(room_id, day, slot_indices, self.room_schedule):
            return False

        return True

    def _score_candidate(self, session: ScheduleSession, day: str,
                         start_slot_idx: int, room_id: str) -> float:
        score = 0.0

        # Penalize same subject twice in a day for same section
        sec_day = self.section_schedule.get(session.section_id, {}).get(day, {})
        for existing_sess_id in sec_day.values():
            existing = self.sessions_by_id.get(existing_sess_id)
            if existing and existing.course_code == session.course_code:
                score -= 10
                break

        # Preference for earlier slots
        score -= start_slot_idx * 0.1

        # Penalize faculty overload on same day
        for fid in session.faculty_ids:
            fac_day = self.faculty_schedule.get(fid, {}).get(day, {})
            if len(fac_day) >= 3:
                score -= 5

        # Distribute classes evenly across days
        sec_sched = self.section_schedule.get(session.section_id, {})
        score -= len(sec_sched.get(day, {})) * 0.5

        return score

    def _assign(self, session: ScheduleSession, day: str,
                start_slot_idx: int, room_id: str):
        self.assignments[session.id] = Assignment(
            session_id=session.id,
            day=day,
            start_slot_index=start_slot_idx,
            room_id=room_id
        )
        for slot in range(start_slot_idx, start_slot_idx + session.duration_slots):
            if session.batch_id:
                self.batch_schedule.setdefault(session.batch_id, {}).setdefault(day, {})[slot] = session.id
            else:
                self.section_schedule.setdefault(session.section_id, {}).setdefault(day, {})[slot] = session.id
            for fid in session.faculty_ids:
                self.faculty_schedule.setdefault(fid, {}).setdefault(day, {})[slot] = session.id
            self.room_schedule.setdefault(room_id, {}).setdefault(day, {})[slot] = session.id

    def _unassign(self, session: ScheduleSession):
        assign = self.assignments.pop(session.id)
        for slot in range(assign.start_slot_index, assign.start_slot_index + session.duration_slots):
            if session.batch_id:
                del self.batch_schedule[session.batch_id][assign.day][slot]
            else:
                del self.section_schedule[session.section_id][assign.day][slot]
            for fid in session.faculty_ids:
                del self.faculty_schedule[fid][assign.day][slot]
            del self.room_schedule[assign.room_id][assign.day][slot]

    def _backtrack(self, idx: int) -> bool:
        if idx == len(self.sessions):
            return True

        if self.backtrack_count >= self.MAX_BACKTRACKS:
            return False
        if (time.time() - self.start_time) >= self.MAX_TIME_SECONDS:
            return False

        session = self.sessions[idx]
        domain = self._get_domain(session)

        viable = []
        for (day, start_idx, room_id) in domain:
            slot_indices = list(range(start_idx, start_idx + session.duration_slots))
            if not self._check_hard_constraints(session, day, slot_indices, room_id):
                continue
            score = self._score_candidate(session, day, start_idx, room_id)
            viable.append((score, day, start_idx, room_id))

        viable.sort(key=lambda x: -x[0])

        for (score, day, slot_idx, room_id) in viable:
            slot_indices = list(range(slot_idx, slot_idx + session.duration_slots))
            if not self._check_hard_constraints(session, day, slot_indices, room_id):
                continue

            self._assign(session, day, slot_idx, room_id)
            if self._backtrack(idx + 1):
                return True
            self._unassign(session)
            self.backtrack_count += 1

        return False

    def solve(self) -> dict:
        domain_sizes = {s.id: len(self._get_domain(s)) for s in self.sessions}
        # Prioritize multi-slot practical sessions first, then MRV
        self.sessions.sort(key=lambda s: (-s.duration_slots, domain_sizes[s.id]))

        self.assignments.clear()
        self.section_schedule.clear()
        self.batch_schedule.clear()
        self.faculty_schedule.clear()
        self.room_schedule.clear()
        self.backtrack_count = 0
        self.start_time = time.time()

        if self._backtrack(0):
            assignments_list = list(self.assignments.values())
            soft_score = compute_soft_score(
                assignments_list, self.sessions, self.config, self.time_slots
            )
            elapsed_ms = int((time.time() - self.start_time) * 1000)
            return {
                'status': 'success',
                'assignments': self._format_assignments(),
                'assignments_data': [a.to_dict() for a in assignments_list],
                'soft_score': soft_score,
                'stats': {
                    'total_sessions': len(self.sessions),
                    'backtracks': self.backtrack_count,
                    'time_ms': elapsed_ms,
                }
            }
        else:
            return {
                'status': 'infeasible',
                'message': 'No feasible conflict-free timetable found with the current constraints.',
                'diagnostics': self._diagnose()
            }

    def _diagnose(self) -> str:
        generic_theory_demand = 0
        generic_lab_demand = 0
        total_slots_per_room = len(self.time_slots) * len(self.config.working_days)

        for s in self.sessions:
            if s.course_type == CourseType.THEORY:
                generic_theory_demand += s.duration_slots
            else:
                generic_lab_demand += s.duration_slots

        theory_rooms = [r for r in self.rooms if r.room_type == RoomType.THEORY_ROOM]
        lab_rooms = [r for r in self.rooms if r.room_type == RoomType.LAB]
        theory_slots_avail = total_slots_per_room * len(theory_rooms)
        lab_slots_avail = total_slots_per_room * len(lab_rooms)

        warnings = []
        if generic_theory_demand > theory_slots_avail:
            warnings.append(f"Capacity shortfall: Theory demand ({generic_theory_demand} slots) exceeds available ({theory_slots_avail} slots).")
        if generic_lab_demand > lab_slots_avail:
            warnings.append(f"Capacity shortfall: Lab demand ({generic_lab_demand} slots) exceeds available ({lab_slots_avail} slots).")

        lines = [
            f"Theory demand: {generic_theory_demand} slots (Available: {theory_slots_avail})",
            f"Lab demand: {generic_lab_demand} slots (Available: {lab_slots_avail})",
        ]
        if warnings:
            lines.append("")
            lines.extend(warnings)

        return "\n".join(lines)

        return "\n".join(lines)

    def _format_assignments(self) -> List[dict]:
        result = []
        for assign in self.assignments.values():
            sess = self.sessions_by_id[assign.session_id]
            sec = self.sections_by_id.get(sess.section_id)
            fac_names = [self.faculty_by_id[fid].name for fid in sess.faculty_ids if fid in self.faculty_by_id]
            room = self.rooms_by_id.get(assign.room_id)
            start_ts = self.time_slots[assign.start_slot_index]
            end_ts = self.time_slots[assign.start_slot_index + sess.duration_slots - 1]
            batch = self.batches_by_id.get(sess.batch_id) if sess.batch_id else None

            result.append({
                'session_id': sess.id,
                'day': assign.day,
                'time_start': start_ts.start_time,
                'time_end': end_ts.end_time,
                'section_id': sess.section_id,
                'section_name': sec.name if sec else sess.section_id,
                'batch_id': sess.batch_id or '',
                'batch_name': batch.name if batch else 'ALL',
                'course_name': sess.course_name,
                'course_code': sess.course_code,
                'course_type': sess.course_type,
                'faculty_ids': sess.faculty_ids,
                'faculty_name': ", ".join(fac_names),
                'room_id': assign.room_id,
                'room_name': room.name if room else assign.room_id,
                'duration_slots': sess.duration_slots,
            })

        day_order = {d: i for i, d in enumerate(self.config.working_days)}
        result.sort(key=lambda x: (day_order.get(x['day'], 99), x['time_start'],
                                   x['section_name'], x['batch_name']))
        return result

    def get_section_view(self, section_id: str) -> dict:
        days = self.config.working_days
        slots = [{'index': s.index, 'start_time': s.start_time, 'end_time': s.end_time} for s in self.time_slots]
        grid = {day: {} for day in days}

        # Theory (section-level)
        sec_sched = self.section_schedule.get(section_id, {})
        for day in days:
            for slot_idx, sess_id in sec_sched.get(day, {}).items():
                sess = self.sessions_by_id.get(sess_id)
                assign = self.assignments.get(sess_id)
                if not sess or not assign:
                    continue
                fac_names = [self.faculty_by_id[fid].name for fid in sess.faculty_ids if fid in self.faculty_by_id]
                room = self.rooms_by_id.get(assign.room_id)
                grid[day][str(slot_idx)] = {
                    'subject': sess.course_name,
                    'code': sess.course_code,
                    'type': sess.course_type,
                    'batch': 'ALL',
                    'faculty': ", ".join(fac_names),
                    'room': room.name if room else assign.room_id,
                }

        # Labs (batch-level)
        for bid in self.section_batches.get(section_id, []):
            batch_sched = self.batch_schedule.get(bid, {})
            batch = self.batches_by_id.get(bid)
            for day in days:
                for slot_idx, sess_id in batch_sched.get(day, {}).items():
                    sess = self.sessions_by_id.get(sess_id)
                    assign = self.assignments.get(sess_id)
                    if not sess or not assign:
                        continue
                    fac_names = [self.faculty_by_id[fid].name for fid in sess.faculty_ids if fid in self.faculty_by_id]
                    room = self.rooms_by_id.get(assign.room_id)
                    key = str(slot_idx)
                    entry = {
                        'subject': sess.course_name,
                        'code': sess.course_code,
                        'type': sess.course_type,
                        'batch': batch.name if batch else bid,
                        'faculty': ", ".join(fac_names),
                        'room': room.name if room else assign.room_id,
                    }
                    if key in grid[day]:
                        existing = grid[day][key]
                        if isinstance(existing, list):
                            existing.append(entry)
                        else:
                            grid[day][key] = [existing, entry]
                    else:
                        grid[day][key] = entry

        return {'days': days, 'slots': slots, 'grid': grid}

    def get_faculty_view(self, faculty_id: str) -> dict:
        return self._build_simple_view(self.faculty_schedule.get(faculty_id, {}), 'faculty')

    def get_room_view(self, room_id: str) -> dict:
        return self._build_simple_view(self.room_schedule.get(room_id, {}), 'room')

    def _build_simple_view(self, entity_sched: dict, view_type: str) -> dict:
        days = self.config.working_days
        slots = [{'index': s.index, 'start_time': s.start_time, 'end_time': s.end_time} for s in self.time_slots]
        grid = {day: {} for day in days}

        for day in days:
            for slot_idx, sess_id in entity_sched.get(day, {}).items():
                sess = self.sessions_by_id.get(sess_id)
                assign = self.assignments.get(sess_id)
                if not sess or not assign:
                    continue
                batch = self.batches_by_id.get(sess.batch_id) if sess.batch_id else None
                sec = self.sections_by_id.get(sess.section_id)
                room = self.rooms_by_id.get(assign.room_id)
                fac_names = [self.faculty_by_id[fid].name for fid in sess.faculty_ids if fid in self.faculty_by_id]

                info = {
                    'subject': sess.course_name,
                    'code': sess.course_code,
                    'type': sess.course_type,
                    'batch': batch.name if batch else 'ALL',
                    'section': sec.name if sec else sess.section_id,
                }
                if view_type == 'faculty':
                    info['room'] = room.name if room else assign.room_id
                elif view_type == 'room':
                    info['faculty'] = ", ".join(fac_names)

                grid[day][str(slot_idx)] = info

        return {'days': days, 'slots': slots, 'grid': grid}
