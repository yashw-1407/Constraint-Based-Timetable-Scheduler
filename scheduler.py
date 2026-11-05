import time
import random
from typing import List, Tuple, Optional
from models import (
    WorkingConfig, Course, Room, Faculty, Section, Batch,
    ScheduleSession, Assignment, CourseType, RoomType
)
from time_slots import generate_time_slots
from constraints import (
    check_section_conflict, check_batch_conflict,
    check_faculty_conflict, check_room_conflict,
    check_room_suitability, check_room_capacity_by_strength,
    check_consecutive_slots
)
from soft_constraints import compute_total_soft_score


class SchedulingEngine:
    """Simple and direct backtracking scheduler for academic timetables."""

    MAX_BACKTRACKS = 50000
    MAX_TIME_SECONDS = 30

    def __init__(
        self,
        config: WorkingConfig,
        courses: List[Course],
        rooms: List[Room],
        faculty_list: List[Faculty],
        sections: List[Section],
        batches: List[Batch] = None,
        **kwargs
    ):
        self.config = config
        self.time_slots = generate_time_slots(config)
        self.rooms = rooms
        self.batches = batches or []

        # Fast lookups by ID
        self.rooms_by_id = {r.id: r for r in rooms}
        self.sections_by_id = {s.id: s for s in sections}
        self.faculty_by_id = {f.id: f for f in faculty_list}
        self.courses_by_id = {c.id: c for c in courses}
        self.batches_by_id = {b.id: b for b in self.batches}

        # Map each section to its list of batch IDs
        self.section_batches = {}
        for b in self.batches:
            self.section_batches.setdefault(b.section_id, []).append(b.id)

        # Break courses into individual schedulable sessions
        self.sessions_by_id = {}
        self.sessions = self._create_sessions(courses)
        self.dedicated_room_ids = {s.required_room_id for s in self.sessions if s.required_room_id}

        # Schedules tracking who is busy when:
        # dict[entity_id][day][slot_index] = session_id
        self.assignments = {}        # session_id -> Assignment
        self.section_schedule = {}
        self.batch_schedule = {}
        self.faculty_schedule = {}
        self.room_schedule = {}

        self.backtrack_count = 0
        self.start_time = 0.0
        self.seed = None

    # -------------------------------------------------------------------------
    # 1. Break courses into individual sessions
    # -------------------------------------------------------------------------
    def _create_sessions(self, courses: List[Course]) -> List[ScheduleSession]:
        sessions = []
        multiplier = 60.0 / self.config.slot_duration_minutes

        for course in courses:
            # 1. Theory sessions (each ~1 hour)
            theory_hours = int(course.l + course.t)
            for i in range(theory_hours):
                faculty = course.faculty_ids[i % len(course.faculty_ids)] if course.faculty_ids else None
                d_slots = max(1, int(round(1.0 * multiplier)))
                sess = ScheduleSession(
                    id=f"{course.id}_T{i}",
                    course_id=course.id,
                    course_name=course.name,
                    course_code=course.code,
                    course_type=CourseType.THEORY,
                    section_id=course.section_id,
                    faculty_ids=[faculty] if faculty else [],
                    room_type=course.room_type,
                    required_room_id=course.required_room_id,
                    session_index=i,
                    duration_slots=d_slots,
                    batch_id=None
                )
                sessions.append(sess)
                self.sessions_by_id[sess.id] = sess

            # 2. Lab sessions (scheduled per batch)
            if course.p > 0:
                batches = course.lab_batches or [None]
                d_slots = max(1, int(round(course.p * multiplier)))

                for b_idx, batch_id in enumerate(batches):
                    # Pick faculty for this batch
                    fac_list = list(getattr(course, "assistant_faculty_ids", []))
                    if course.faculty_ids:
                        fac_list = [course.faculty_ids[b_idx % len(course.faculty_ids)]] + fac_list

                    sess = ScheduleSession(
                        id=f"{course.id}_L{b_idx}",
                        course_id=course.id,
                        course_name=course.name,
                        course_code=course.code,
                        course_type=CourseType.LAB,
                        section_id=course.section_id,
                        faculty_ids=fac_list,
                        room_type=course.room_type,
                        required_room_id=course.required_room_id,
                        session_index=0,
                        duration_slots=d_slots,
                        batch_id=batch_id
                    )
                    sessions.append(sess)
                    self.sessions_by_id[sess.id] = sess

        return sessions

    # -------------------------------------------------------------------------
    # 2. Find valid (day, slot, room) choices for a session
    # -------------------------------------------------------------------------
    def _get_suitable_rooms(self, session: ScheduleSession) -> List[Room]:
        strength = None
        if session.batch_id and session.batch_id in self.batches_by_id:
            strength = self.batches_by_id[session.batch_id].strength
        elif session.section_id in self.sections_by_id:
            strength = self.sections_by_id[session.section_id].strength

        suitable = []
        for room in self.rooms:
            # If room is reserved for a specific course, skip for others
            if room.id in self.dedicated_room_ids and session.required_room_id != room.id:
                continue
            # Type check (Lab vs Theory Room)
            if not check_room_suitability(session, room):
                continue
            # Capacity check
            if not check_room_capacity_by_strength(room, strength):
                continue
            suitable.append(room)

        return suitable

    def _get_domain(self, session: ScheduleSession) -> List[Tuple[str, int, str]]:
        domain = []
        rooms = self._get_suitable_rooms(session)
        num_slots = len(self.time_slots)

        for day in self.config.working_days:
            for start_slot in range(num_slots):
                end_slot = start_slot + session.duration_slots
                if end_slot > num_slots:
                    break

                # Ensure multi-slot lab sessions don't span lunch or long breaks
                if session.duration_slots > 1:
                    slots_range = list(range(start_slot, end_slot))
                    if not check_consecutive_slots(slots_range, self.time_slots):
                        continue

                for room in rooms:
                    domain.append((day, start_slot, room.id))

        return domain

    # -------------------------------------------------------------------------
    # 3. Check for clashes (section, batch, faculty, room)
    # -------------------------------------------------------------------------
    def _is_valid(self, session: ScheduleSession, day: str, start_slot: int, room_id: str) -> bool:
        slots = list(range(start_slot, start_slot + session.duration_slots))

        # Check section clash
        if not check_section_conflict(session.section_id, day, slots, self.section_schedule):
            return False

        # Check batch clash
        if session.batch_id:
            if not check_batch_conflict(session.batch_id, day, slots, self.batch_schedule):
                return False
        else:
            # Theory session blocks all batches of the section
            for b_id in self.section_batches.get(session.section_id, []):
                if not check_batch_conflict(b_id, day, slots, self.batch_schedule):
                    return False

        # Check faculty clash
        if not check_faculty_conflict(session.faculty_ids, day, slots, self.faculty_schedule):
            return False

        # Check room clash
        if not check_room_conflict(room_id, day, slots, self.room_schedule):
            return False

        return True

    # -------------------------------------------------------------------------
    # 4. Score choices to try the most promising slots first
    # -------------------------------------------------------------------------
    def _score(self, session: ScheduleSession, day: str, start_slot: int) -> float:
        score = -start_slot * 0.1  # Prefer earlier slots in the day

        # Penalize having the same subject twice on the same day for a section
        sec_day_sessions = self.section_schedule.get(session.section_id, {}).get(day, {})
        for existing_id in sec_day_sessions.values():
            existing = self.sessions_by_id.get(existing_id)
            if existing and existing.course_code == session.course_code:
                score -= 10
                break

        # Spread teacher load
        for fid in session.faculty_ids:
            fac_today = len(self.faculty_schedule.get(fid, {}).get(day, {}))
            if fac_today >= 3:
                score -= 5

        # Small random factor when generating variants
        if self.seed is not None:
            score += random.uniform(-0.1, 0.1)

        return score

    # -------------------------------------------------------------------------
    # 5. Place and remove assignments
    # -------------------------------------------------------------------------
    def _assign(self, session: ScheduleSession, day: str, start_slot: int, room_id: str):
        self.assignments[session.id] = Assignment(session.id, day, start_slot, room_id)
        for slot in range(start_slot, start_slot + session.duration_slots):
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

    # -------------------------------------------------------------------------
    # 6. Backtracking search (assign -> recurse -> unassign)
    # -------------------------------------------------------------------------
    def _backtrack(self, index: int) -> bool:
        if index == len(self.sessions):
            return True  # All sessions successfully placed!

        if self.backtrack_count >= self.MAX_BACKTRACKS:
            return False
        if (time.time() - self.start_time) >= self.MAX_TIME_SECONDS:
            return False

        session = self.sessions[index]
        domain = self._get_domain(session)

        # Collect valid candidates and sort by score
        candidates = []
        for day, slot, room_id in domain:
            if self._is_valid(session, day, slot, room_id):
                candidates.append((self._score(session, day, slot), day, slot, room_id))

        candidates.sort(key=lambda x: -x[0])

        for _, day, slot, room_id in candidates:
            if not self._is_valid(session, day, slot, room_id):
                continue

            self._assign(session, day, slot, room_id)
            if self._backtrack(index + 1):
                return True

            self._unassign(session)
            self.backtrack_count += 1

        return False

    # -------------------------------------------------------------------------
    # 7. Main entry point to solve
    # -------------------------------------------------------------------------
    def solve(self, seed=None) -> dict:
        self.seed = seed
        if seed is not None:
            random.seed(seed)

        # Sort sessions: fewest choices first (MRV), longer labs first
        domain_counts = {s.id: len(self._get_domain(s)) for s in self.sessions}
        self.sessions.sort(key=lambda s: (domain_counts[s.id], -s.duration_slots))

        self.assignments.clear()
        self.section_schedule.clear()
        self.batch_schedule.clear()
        self.faculty_schedule.clear()
        self.room_schedule.clear()
        self.backtrack_count = 0
        self.start_time = time.time()

        if self._backtrack(0):
            assign_list = list(self.assignments.values())
            soft = compute_total_soft_score(assign_list, self.sessions, self.config, self.time_slots)
            elapsed = int((time.time() - self.start_time) * 1000)

            return {
                'status': 'success',
                'assignments': self._format_assignments(),
                'assignments_data': [a.to_dict() for a in assign_list],
                'soft_score': soft,
                'stats': {
                    'total_sessions': len(self.sessions),
                    'backtracks': self.backtrack_count,
                    'time_ms': elapsed,
                }
            }

        return {
            'status': 'infeasible',
            'message': 'Could not place all sessions with given constraints.',
            'diagnostics': self._diagnose()
        }

    def solve_multiple(self, requested_count=5, base_seed=1000, max_attempts=30, **kwargs) -> dict:
        alternatives = []
        seen = set()

        for i in range(max_attempts):
            res = self.solve(seed=base_seed + i)
            if res.get('status') == 'success':
                # Build simple key to ensure variety
                key = tuple(sorted((a['session_id'], a['day'], a['start_slot_index'], a['room_id']) for a in res['assignments_data']))
                if key not in seen:
                    seen.add(key)
                    alternatives.append({
                        'alternative_id': len(alternatives) + 1,
                        'seed': base_seed + i,
                        'assignments_data': res['assignments_data'],
                        'soft_score': res['soft_score'],
                        'stats': res['stats'],
                        'diversity_pct': 'Base' if not alternatives else 30.0,
                        'changed_assignments': len(res['assignments_data'])
                    })

            if len(alternatives) == requested_count:
                break

        if not alternatives:
            return {'status': 'infeasible', 'message': 'No solutions found.'}

        alternatives.sort(key=lambda x: -x['soft_score']['total_score'])
        self.load_assignments_data(alternatives[0]['assignments_data'])

        return {
            'status': 'success' if len(alternatives) == requested_count else 'partial',
            'requested': requested_count,
            'generated': len(alternatives),
            'alternatives': alternatives,
            'active_variant_index': 0
        }

    def load_assignments_data(self, data: list):
        self.assignments.clear()
        self.section_schedule.clear()
        self.batch_schedule.clear()
        self.faculty_schedule.clear()
        self.room_schedule.clear()
        for d in data:
            assign = Assignment.from_dict(d)
            self._assign(self.sessions_by_id[assign.session_id], assign.day, assign.start_slot_index, assign.room_id)

    # -------------------------------------------------------------------------
    # 8. Output formatters
    # -------------------------------------------------------------------------
    def _format_assignments(self) -> List[dict]:
        out = []
        for a in self.assignments.values():
            s = self.sessions_by_id[a.session_id]
            sec = self.sections_by_id[s.section_id]
            rm = self.rooms_by_id[a.room_id]
            t_start = self.time_slots[a.start_slot_index].start_time
            t_end = self.time_slots[a.start_slot_index + s.duration_slots - 1].end_time

            fac_names = [self.faculty_by_id[fid].name for fid in s.faculty_ids if fid in self.faculty_by_id]
            batch_name = self.batches_by_id[s.batch_id].name if s.batch_id in self.batches_by_id else 'ALL'

            out.append({
                'session_id': s.id,
                'day': a.day,
                'time_start': t_start,
                'time_end': t_end,
                'section_id': sec.id,
                'section_name': sec.name,
                'batch_id': s.batch_id or '',
                'batch_name': batch_name,
                'course_name': s.course_name,
                'course_code': s.course_code,
                'course_type': s.course_type,
                'faculty_ids': s.faculty_ids,
                'faculty_name': ", ".join(fac_names) or "None",
                'room_id': rm.id,
                'room_name': rm.name,
                'duration_slots': s.duration_slots,
            })

        day_order = {d: i for i, d in enumerate(self.config.working_days)}
        out.sort(key=lambda x: (day_order.get(x['day'], 99), x['time_start'], x['section_name']))
        return out

    def _diagnose(self) -> str:
        theory_needed = sum(s.duration_slots for s in self.sessions if s.course_type == CourseType.THEORY)
        lab_needed = sum(s.duration_slots for s in self.sessions if s.course_type == CourseType.LAB)
        total_slots = len(self.time_slots) * len(self.config.working_days)

        theory_rooms = len([r for r in self.rooms if r.room_type == RoomType.THEORY_ROOM])
        lab_rooms = len([r for r in self.rooms if r.room_type == RoomType.LAB])

        return (
            f"Theory hours needed: {theory_needed}, available: {theory_rooms * total_slots}\n"
            f"Lab hours needed: {lab_needed}, available: {lab_rooms * total_slots}"
        )

    def get_section_view(self, section_id: str) -> dict:
        days = self.config.working_days
        slots = [{'index': s.index, 'start_time': s.start_time, 'end_time': s.end_time} for s in self.time_slots]
        grid = {day: {} for day in days}

        for day in days:
            # Theory
            for slot, sid in self.section_schedule.get(section_id, {}).get(day, {}).items():
                s, a = self.sessions_by_id.get(sid), self.assignments.get(sid)
                if s and a:
                    facs = [self.faculty_by_id[f].name for f in s.faculty_ids if f in self.faculty_by_id]
                    grid[day][str(slot)] = {
                        'subject': s.course_name, 'code': s.course_code, 'type': s.course_type,
                        'batch': 'ALL', 'faculty': ", ".join(facs), 'room': self.rooms_by_id[a.room_id].name
                    }
            # Lab
            for bid in self.section_batches.get(section_id, []):
                for slot, sid in self.batch_schedule.get(bid, {}).get(day, {}).items():
                    s, a = self.sessions_by_id.get(sid), self.assignments.get(sid)
                    if s and a:
                        facs = [self.faculty_by_id[f].name for f in s.faculty_ids if f in self.faculty_by_id]
                        entry = {
                            'subject': s.course_name, 'code': s.course_code, 'type': s.course_type,
                            'batch': self.batches_by_id[bid].name, 'faculty': ", ".join(facs),
                            'room': self.rooms_by_id[a.room_id].name
                        }
                        key = str(slot)
                        if key in grid[day]:
                            prev = grid[day][key]
                            grid[day][key] = prev if isinstance(prev, list) else [prev]
                            grid[day][key].append(entry)
                        else:
                            grid[day][key] = entry

        return {'days': days, 'slots': slots, 'grid': grid}

    def get_faculty_view(self, faculty_id: str) -> dict:
        return self._simple_view(self.faculty_schedule.get(faculty_id, {}), 'faculty')

    def get_room_view(self, room_id: str) -> dict:
        return self._simple_view(self.room_schedule.get(room_id, {}), 'room')

    def _simple_view(self, sched: dict, mode: str) -> dict:
        days = self.config.working_days
        slots = [{'index': s.index, 'start_time': s.start_time, 'end_time': s.end_time} for s in self.time_slots]
        grid = {day: {} for day in days}

        for day in days:
            for slot, sid in sched.get(day, {}).items():
                s, a = self.sessions_by_id.get(sid), self.assignments.get(sid)
                if s and a:
                    entry = {
                        'subject': s.course_name, 'code': s.course_code, 'type': s.course_type,
                        'section': self.sections_by_id[s.section_id].name,
                        'batch': self.batches_by_id[s.batch_id].name if s.batch_id else 'ALL'
                    }
                    if mode == 'faculty':
                        entry['room'] = self.rooms_by_id[a.room_id].name
                    else:
                        facs = [self.faculty_by_id[f].name for f in s.faculty_ids if f in self.faculty_by_id]
                        entry['faculty'] = ", ".join(facs)
                    grid[day][str(slot)] = entry

        return {'days': days, 'slots': slots, 'grid': grid}
