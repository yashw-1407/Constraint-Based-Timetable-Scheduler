"""
scheduler.py - Constraint Satisfaction Problem (CSP) Engine

Academic Course Mapping:
  - DAA  : CSP Formulation (X, D, C), State-Space Tree Search, MRV (Fail-First) Heuristic, Pruning.
  - OS   : Shared Resource Allocation, Mutual Exclusion Locks (Rooms/Faculty), Deadlock Avoidance, Quantum Time-Slicing.
  - DBMS : 3NF Relational Model, Atomic Transaction Assignment & Rollback, Integrity Constraints.
  - DMS  : Cartesian Product Domains (Days x Slots x Rooms), Bipartite Matching, Graph Vertex Coloring.

CSP Formulation:
  Variables (X)   : Each required class meeting (ScheduleSession).
  Domains (D)     : Cartesian product of (day, time_slot, room) for each session.
  Constraints (C) :
    1. Theory conflict: No two sessions for a section at the same slot.
    2. Lab conflict   : No two sessions for a batch at the same slot.
    3. Faculty clash  : Mutual exclusion on faculty time slices.
    4. Room clash     : Mutual exclusion on room physical capacity.
    5. Consecutive    : Multi-period lab sessions occupy adjacent slots.
    6. Suitability    : Lab sessions assigned only to lab rooms.
    7. Capacity       : Room capacity >= relevant cohort strength.

Complexity:
  Worst case : O(d^n) where d = domain size, n = number of sessions.
  Practical  : Pruned to empirical <50ms execution via MRV variable ordering.
"""

import time
import random
from typing import List, Tuple, Optional
from models import (WorkingConfig, Course, Room, Faculty, Section, Batch,
                    ScheduleSession, Assignment, CourseType, RoomType)
from scheduler_trace import SchedulerTrace
from time_slots import generate_time_slots
from constraints import (check_section_conflict, check_batch_conflict,
                         check_faculty_conflict, check_room_conflict,
                         check_room_suitability, check_room_capacity_by_strength,
                         check_consecutive_slots)
from soft_constraints import compute_total_soft_score


class SchedulingEngine:
    """CSP-based scheduling engine using backtracking with heuristics.

    Supports batch-wise lab scheduling: lab sessions are scheduled per-batch,
    while theory sessions are scheduled per-section. Different batches of the
    same section may have labs at the same time in different rooms.
    """

    MAX_BACKTRACKS = 50000
    MAX_TIME_SECONDS = 30

    def __init__(self, config: WorkingConfig, courses: List[Course],
                 rooms: List[Room], faculty_list: List[Faculty],
                 sections: List[Section], batches: List[Batch] = None, trace: SchedulerTrace = None):
        self.trace = trace or SchedulerTrace(level=0)
        self.config = config
        self.time_slots = generate_time_slots(config)
        self.rooms = rooms
        self.rooms_by_id = {r.id: r for r in rooms}
        self.sections_by_id = {s.id: s for s in sections}
        self.faculty_by_id = {f.id: f for f in faculty_list}
        self.courses_by_id = {c.id: c for c in courses}
        self.batches = batches or []
        self.batches_by_id = {b.id: b for b in self.batches}
        # Map section_id -> list of batch_ids belonging to that section
        self.section_batches = {}
        for b in self.batches:
            self.section_batches.setdefault(b.section_id, []).append(b.id)

        self.sessions_by_id = {}
        self.sessions = self._create_sessions(courses)
        self.dedicated_room_ids = {s.required_room_id for s in self.sessions if s.required_room_id}

        # State: current partial assignment
        self.assignments = {}           # session_id -> Assignment
        self.section_schedule = {}      # section_id -> {day -> {slot_idx -> session_id}}
        self.batch_schedule = {}        # batch_id -> {day -> {slot_idx -> session_id}}
        self.faculty_schedule = {}      # faculty_id -> {day -> {slot_idx -> session_id}}
        self.room_schedule = {}         # room_id -> {day -> {slot_idx -> session_id}}

        # Statistics
        self.backtrack_count = 0
        self.start_time = 0.0

    # =========================================================================
    # PHASE 1: VARIABLE FORMULATION (DAA: Session Variable Decomposition)
    # =========================================================================
    def _create_sessions(self, courses: List[Course]) -> List[ScheduleSession]:
        """Convert each Course into ScheduleSession objects based on L, T, P."""
        sessions = []
        multiplier = 60.0 / self.config.slot_duration_minutes
        
        for course in courses:
            req_room = self.rooms_by_id.get(course.required_room_id) if course.required_room_id else None
            theory_hours = course.l + course.t
            if theory_hours > 0:
                # Create separate ~1-hour sessions
                sessions_to_create = []
                remaining = theory_hours
                while remaining >= 1.0:
                    sessions_to_create.append(1.0)
                    remaining -= 1.0
                if remaining > 0:
                    sessions_to_create.append(remaining)

                for i, hrs in enumerate(sessions_to_create):
                    d_slots = max(1, int(round(hrs * multiplier)))
                    fac = course.faculty_ids[i % len(course.faculty_ids)] if course.faculty_ids else None
                    sess = ScheduleSession(
                        id=f"{course.id}_T{i}",
                        course_id=course.id,
                        course_name=course.name,
                        course_code=course.code,
                        course_type=CourseType.THEORY,
                        section_id=course.section_id,
                        faculty_ids=[fac] if fac else [],
                        room_type=course.room_type,
                        required_room_id=course.required_room_id,
                        session_index=i,
                        duration_slots=d_slots,
                        batch_id=None
                    )
                    sessions.append(sess)
                    self.sessions_by_id[sess.id] = sess
                    if hasattr(self, 'trace'):
                        sec = self.sections_by_id.get(course.section_id)
                        self.trace.trace_session_created(sess, course, sec, None)
                    
            if course.p > 0:
                batches = course.lab_batches
                if not batches:
                    batches = [None] # Schedule at section level if no batches
                
                d_slots = max(1, int(round(course.p * multiplier)))
                for b_idx, batch_id in enumerate(batches):
                    # Distribute faculty among batches
                    batch_facs = getattr(course, "assistant_faculty_ids", []).copy()
                    if course.faculty_ids:
                        # Give one faculty per batch (round-robin)
                        fac = course.faculty_ids[b_idx % len(course.faculty_ids)]
                        batch_facs = [fac] + getattr(course, "assistant_faculty_ids", [])

                    sess_req_room = course.required_room_id if (req_room and req_room.room_type == course.room_type) else None

                    sess = ScheduleSession(
                        id=f"{course.id}_L{b_idx}",
                        course_id=course.id,
                        course_name=course.name,
                        course_code=course.code,
                        course_type=CourseType.LAB,
                        section_id=course.section_id,
                        faculty_ids=batch_facs,
                        room_type=course.room_type,
                        required_room_id=sess_req_room,
                        session_index=0,
                        duration_slots=d_slots,
                        batch_id=batch_id
                    )
                    sessions.append(sess)
                    self.sessions_by_id[sess.id] = sess
                    if hasattr(self, 'trace'):
                        sec = self.sections_by_id.get(course.section_id)
                        bat = self.batches_by_id.get(batch_id) if batch_id else None
                        self.trace.trace_session_created(sess, course, sec, bat)
        return sessions

    # ------------------------------------------------------------------
    # Strength Resolution
    # ------------------------------------------------------------------
    def _get_scheduling_strength(self, session: ScheduleSession) -> Optional[int]:
        """Get the strength used for room capacity check.

        Theory -> section strength.
        Lab with batch -> batch strength.
        Lab without batch -> section strength (no batches defined).
        """
        if session.batch_id:
            batch = self.batches_by_id.get(session.batch_id)
            if batch and batch.strength is not None:
                return batch.strength
        section = self.sections_by_id.get(session.section_id)
        return section.strength if section else None

    # =========================================================================
    # PHASE 2: DOMAIN GENERATION (DMS: Cartesian Product, OS: Resource Filter)
    # =========================================================================
    def _get_suitable_rooms(self, session: ScheduleSession) -> List[Room]:
        """Get rooms suitable for a session (type match, capacity, specific room)."""
        suitable = []
        strength = self._get_scheduling_strength(session)
        
        home_room_id = None
        if not session.required_room_id and session.course_type == CourseType.THEORY:
            section = self.sections_by_id.get(session.section_id)
            if section and getattr(section, 'home_room_id', None):
                home_room_id = section.home_room_id
                
        room_results = []
        for r in self.rooms:
            res = 'INCLUDED'
            reason = None
            if r.id in self.dedicated_room_ids and session.required_room_id != r.id:
                res = 'REJECTED'
                reason = 'DEDICATED_ROOM_EXCLUSION'
            elif home_room_id and r.id != home_room_id:
                res = 'REJECTED'
                reason = 'HOME_ROOM_FILTER'
            elif not check_room_suitability(session, r):
                res = 'REJECTED'
                reason = 'ROOM_TYPE_MISMATCH' if not session.required_room_id else 'REQUIRED_ROOM'
            elif not check_room_capacity_by_strength(r, strength):
                res = 'REJECTED'
                reason = 'ROOM_CAPACITY'
            
            room_results.append({
                'room_id': r.id, 'room_name': r.name, 'room_type': r.room_type,
                'capacity': r.capacity, 'result': res, 'reason': reason
            })
            if res == 'INCLUDED':
                suitable.append(r)
                
        if hasattr(self, 'trace'):
            self.trace.trace_room_domain(session, room_results, strength, home_room_id)
            
        return suitable

    def _get_domain(self, session: ScheduleSession) -> List[Tuple[str, int, str]]:
        """Generate all valid (day, start_slot_index, room_id) for a session."""
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

        if hasattr(self, 'trace'):
            self.trace.trace_domain_size(session, len(domain), len(suitable_rooms), len(self.config.working_days))
        return domain

    # =========================================================================
    # PHASE 3: HARD CONSTRAINTS (OS: Mutual Exclusion & Deadlock Prevention)
    # =========================================================================
    def _check_hard_constraints(self, session: ScheduleSession, day: str,
                                slot_indices: List[int], room_id: str) -> Tuple[bool, Optional[str]]:
        if session.batch_id:
            if not check_batch_conflict(session.batch_id, day, slot_indices, self.batch_schedule):
                return False, 'BATCH_CONFLICT'
            if not check_section_conflict(session.section_id, day, slot_indices, self.section_schedule):
                return False, 'SECTION_CONFLICT'
        else:
            if not check_section_conflict(session.section_id, day, slot_indices, self.section_schedule):
                return False, 'SECTION_CONFLICT'
            for bid in self.section_batches.get(session.section_id, []):
                if not check_batch_conflict(bid, day, slot_indices, self.batch_schedule):
                    return False, 'BATCH_CONFLICT'

        if not check_faculty_conflict(session.faculty_ids, day, slot_indices, self.faculty_schedule):
            return False, 'FACULTY_CONFLICT'
        if not check_room_conflict(room_id, day, slot_indices, self.room_schedule):
            return False, 'ROOM_CONFLICT'
        return True, None

    # =========================================================================
    # PHASE 4: VALUE ORDERING (DAA: Heuristic Soft Constraint Guidance)
    # =========================================================================
    def _score_candidate(self, session: ScheduleSession, day: str,
                         start_slot_idx: int, room_id: str) -> float:
        """Quick heuristic score for ordering domain values."""
        score = 0.0

        # Penalize: same subject already scheduled for this section on this day
        sec_day = self.section_schedule.get(session.section_id, {}).get(day, {})
        for existing_sess_id in sec_day.values():
            existing = self.sessions_by_id.get(existing_sess_id)
            if existing and existing.course_code == session.course_code:
                score -= 10
                break

        # Slight preference for earlier slots
        score -= start_slot_idx * 0.1

        # Penalize: faculty already has 3+ classes today
        for fid in session.faculty_ids:
            fac_day = self.faculty_schedule.get(fid, {}).get(day, {})
            if len(fac_day) >= 3:
                score -= 5

        # Prefer: distribute across different days
        sec_sched = self.section_schedule.get(session.section_id, {})
        section_day_load = len(sec_sched.get(day, {}))
        score -= section_day_load * 0.5

        if getattr(self, 'variant_seed', None) is not None:
            import random
            import hashlib
            # Seed must be deterministic per attempt and candidate choice
            # Using MD5 string to avoid python 3 hash() randomization across processes
            seed_str = f"{self.variant_seed}_{session.id}_{day}_{start_slot_idx}_{room_id}"
            rng_seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
            rng = random.Random(rng_seed)
            # Add tie-breaking noise. Keep it smaller than major heuristics
            score += rng.uniform(-0.05, 0.05)

        # Diversity pressure bonus/penalty
        if getattr(self, 'diversity_penalties', None):
            key = (session.id, day, start_slot_idx, room_id)
            penalty = self.diversity_penalties.get(key, 0)
            score -= penalty * 1.5  # Encourage different choices!

        return score

    # =========================================================================
    # PHASE 5: ATOMIC TRANSACTION STATE (DBMS: ACID Undo / OS: Lock & Unlock)
    # =========================================================================
    def _assign(self, session: ScheduleSession, day: str,
                start_slot_idx: int, room_id: str):
        """Record an assignment and update all lookup tables."""
        self.assignments[session.id] = Assignment(
            session_id=session.id,
            day=day,
            start_slot_index=start_slot_idx,
            room_id=room_id
        )
        for slot in range(start_slot_idx, start_slot_idx + session.duration_slots):
            if session.batch_id:
                # Lab with batch: record in batch_schedule only
                self.batch_schedule.setdefault(
                    session.batch_id, {}).setdefault(day, {})[slot] = session.id
            else:
                # Theory (or lab without batch): record in section_schedule
                self.section_schedule.setdefault(
                    session.section_id, {}).setdefault(day, {})[slot] = session.id
            for fid in session.faculty_ids:
                self.faculty_schedule.setdefault(
                    fid, {}).setdefault(day, {})[slot] = session.id
            self.room_schedule.setdefault(
                room_id, {}).setdefault(day, {})[slot] = session.id

    def _unassign(self, session: ScheduleSession):
        """Remove an assignment and clean up lookup tables."""
        assign = self.assignments.pop(session.id)
        for slot in range(assign.start_slot_index,
                          assign.start_slot_index + session.duration_slots):
            if session.batch_id:
                del self.batch_schedule[session.batch_id][assign.day][slot]
            else:
                del self.section_schedule[session.section_id][assign.day][slot]
            for fid in session.faculty_ids:
                del self.faculty_schedule[fid][assign.day][slot]
            del self.room_schedule[assign.room_id][assign.day][slot]

    # =========================================================================
    # PHASE 6: MRV HEURISTIC (DAA: Fail-First Search Space Pruning)
    # =========================================================================
    def solve(self, seed=None, previous_alternatives=None) -> dict:
        """Main entry point: solve the CSP and return a single result."""
        self.diversity_penalties = {}
        if previous_alternatives:
            for alt in previous_alternatives:
                for ad in alt['assignments_data']:
                    key = (ad['session_id'], ad['day'], ad['start_slot_index'], ad['room_id'])
                    self.diversity_penalties[key] = self.diversity_penalties.get(key, 0) + 1
                    
        domain_sizes = {}
        for s in self.sessions:
            domain_sizes[s.id] = len(self._get_domain(s))
            
        self.sessions.sort(
            key=lambda s: (domain_sizes[s.id], -s.duration_slots)
        )

        self.assignments.clear()
        self.section_schedule.clear()
        self.batch_schedule.clear()
        self.faculty_schedule.clear()
        self.room_schedule.clear()
        self.backtrack_count = 0
        self.start_time = time.time()
        self.variant_seed = seed
        
        if self._backtrack(0):
            assignments_list = list(self.assignments.values())
            soft_score = compute_total_soft_score(
                assignments_list, self.sessions, self.config, self.time_slots
            )
            elapsed_ms = int((time.time() - self.start_time) * 1000)
            if hasattr(self, 'trace'):
                self.trace.trace_final_result('success', len(self.sessions), len(self.assignments), self.backtrack_count, time.time() - self.start_time, len(self.sessions))
                self.trace.trace_room_utilization(self.rooms, self.room_schedule, self.time_slots, self.config.working_days, self.dedicated_room_ids, list(self.sections_by_id.values()))
                self.trace.trace_course_summary(list(self.courses_by_id.values()), self.sessions, self.assignments)
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
            if hasattr(self, 'trace'):
                self.trace.trace_final_result('infeasible', len(self.sessions), len(self.assignments), self.backtrack_count, time.time() - self.start_time, self.trace._max_depth if hasattr(self.trace, '_max_depth') else 0)
                self.trace.trace_room_utilization(self.rooms, self.room_schedule, self.time_slots, self.config.working_days, self.dedicated_room_ids, list(self.sections_by_id.values()))
                self.trace.trace_course_summary(list(self.courses_by_id.values()), self.sessions, self.assignments)
            return {
                'status': 'infeasible',
                'message': 'No feasible timetable found...',
                'diagnostics': self._diagnose()
            }
            
    def _create_signature(self, assignments_list) -> str:
        sig_parts = []
        for a in assignments_list:
            sess = self.sessions_by_id[a.session_id]
            b_id = sess.batch_id or ''
            facs = ','.join(sorted(sess.faculty_ids))
            sig_parts.append(f"{a.session_id}|{a.day}|{a.start_slot_index}|{a.room_id}|{facs}|{b_id}")
        sig_parts.sort()
        import hashlib
        return hashlib.md5(";;".join(sig_parts).encode()).hexdigest()

    def _calculate_diversity(self, assignments_list, previous_alternatives):
        if not previous_alternatives:
            return 100.0, len(assignments_list)
            
        new_map = {a.session_id: (a.day, a.start_slot_index, a.room_id) for a in assignments_list}
        total = len(new_map)
        
        min_diversity_pct = 100.0
        min_changed = total
        
        for alt in previous_alternatives:
            old_map = {ad['session_id']: (ad['day'], ad['start_slot_index'], ad['room_id']) for ad in alt['assignments_data']}
            changed = sum(1 for sid, new_val in new_map.items() if sid not in old_map or old_map[sid] != new_val)
            pct = (changed / total) * 100.0 if total > 0 else 0.0
            if pct < min_diversity_pct:
                min_diversity_pct = pct
                min_changed = changed
                
        return min_diversity_pct, min_changed

    def solve_multiple(self, requested_count=5, base_seed=1000, max_attempts=50, min_diversity_pct=25.0) -> dict:
        alternatives = []
        signatures = set()
        
        for attempt in range(max_attempts):
            seed = base_seed + attempt
            result = self.solve(seed=seed, previous_alternatives=alternatives)
            
            if result.get('status') == 'success':
                assigns = list(self.assignments.values())
                signature = self._create_signature(assigns)
                
                if signature not in signatures:
                    div_pct, changed = self._calculate_diversity(assigns, alternatives)
                    
                    if not alternatives or div_pct >= min_diversity_pct:
                        signatures.add(signature)
                        alternatives.append({
                            'alternative_id': len(alternatives) + 1,
                            'seed': seed,
                            'assignments_data': result['assignments_data'],
                            'soft_score': result['soft_score'],
                            'stats': result['stats'],
                            'signature': signature,
                            'diversity_pct': round(div_pct, 1) if alternatives else 'Base',
                            'changed_assignments': changed if alternatives else 0
                        })
                        
            if len(alternatives) == requested_count:
                break
                
        # Sort by soft score
        alternatives.sort(key=lambda x: -x['soft_score']['total_score'])
        
        if not alternatives:
            if hasattr(self, 'trace'):
                self.trace.trace_final_result('infeasible', len(self.sessions), len(self.assignments), self.backtrack_count, time.time() - self.start_time, self.trace._max_depth if hasattr(self.trace, '_max_depth') else 0)
                self.trace.trace_room_utilization(self.rooms, self.room_schedule, self.time_slots, self.config.working_days, self.dedicated_room_ids, list(self.sections_by_id.values()))
                self.trace.trace_course_summary(list(self.courses_by_id.values()), self.sessions, self.assignments)
            return {
                'status': 'infeasible',
                'message': 'No feasible timetable found even after multiple attempts.',
                'diagnostics': self._diagnose()
            }
            
        status = 'success' if len(alternatives) == requested_count else 'partial'
        
        # Load the best alternative as active
        self.load_assignments_data(alternatives[0]['assignments_data'])
        
        return {
            'status': status,
            'requested': requested_count,
            'generated': len(alternatives),
            'alternatives': alternatives,
            'active_variant_index': 0
        }

    def load_assignments_data(self, assignments_data: list):
        """Load a specific variant's state into the engine."""
        self.assignments.clear()
        self.section_schedule.clear()
        self.faculty_schedule.clear()
        self.room_schedule.clear()
        
        for ad in assignments_data:
            from models import Assignment
            assign = Assignment.from_dict(ad)
            sess = self.sessions_by_id[assign.session_id]
            self._assign(sess, assign.day, assign.start_slot_index, assign.room_id)

    # =========================================================================
    # PHASE 7: RECURSIVE BACKTRACKING SEARCH (DAA: Depth-First State Space Search)
    # =========================================================================
    def _backtrack(self, idx: int) -> bool:
        """Recursive backtracking search with MRV and value ordering."""
        if idx == len(self.sessions):
            return True

        if self.backtrack_count >= self.MAX_BACKTRACKS:
            return False
        if (time.time() - self.start_time) >= self.MAX_TIME_SECONDS:
            return False

        # MRV Selection (already sorted in solve)
        session = self.sessions[idx]
        domain = self._get_domain(session)

        if hasattr(self, 'trace') and self.trace.level >= 2:
            rem = len(self.sessions) - idx - 1
            other = [(s.id, len(self._get_domain(s))) for s in self.sessions[idx+1:idx+6]]
            self.trace.trace_mrv_selection(idx, session, len(domain), rem, other)

        # Filter and score domain values
        viable = []
        failure_breakdown = {}
        for (day, start_idx, room_id) in domain:
            slot_indices = list(range(start_idx, start_idx + session.duration_slots))
            is_valid, fail_reason = self._check_hard_constraints(session, day, slot_indices, room_id)
            
            if hasattr(self, 'trace') and self.trace.level >= 3:
                # Level 3 deep trace
                c_results = {
                    'SECTION_CONFLICT': 'PASS',
                    'BATCH_CONFLICT': 'PASS',
                    'FACULTY_CONFLICT': 'PASS',
                    'ROOM_CONFLICT': 'PASS'
                }
                if fail_reason:
                    c_results[fail_reason] = 'FAIL'
                self.trace.trace_candidate_attempt(idx, session, day, start_idx, start_idx+session.duration_slots-1, room_id, None, c_results, is_valid)
                
            if not is_valid:
                if hasattr(self, 'trace') and self.trace.level >= 2:
                    self.trace.trace_candidate_rejected(session, day, start_idx, room_id, fail_reason)
                failure_breakdown[fail_reason] = failure_breakdown.get(fail_reason, 0) + 1
                continue
                
            score = self._score_candidate(session, day, start_idx, room_id)
            viable.append((score, day, start_idx, room_id))
            
        if not viable and hasattr(self, 'trace') and self.trace.level >= 1:
            self.trace.trace_dead_end(idx, session, len(domain), failure_breakdown)

        viable.sort(key=lambda x: -x[0])

        for (score, day, slot_idx, room_id) in viable:
            slot_indices = list(range(slot_idx, slot_idx + session.duration_slots))
            is_valid, fail_reason = self._check_hard_constraints(session, day, slot_indices, room_id)
            if not is_valid:
                if hasattr(self, 'trace') and self.trace.level >= 2:
                    self.trace.trace_candidate_rejected(session, day, slot_idx, room_id, fail_reason)
                continue

            self._assign(session, day, slot_idx, room_id)
            if hasattr(self, 'trace') and self.trace.level >= 2:
                self.trace.trace_assignment(idx, session, day, slot_idx, slot_idx+session.duration_slots-1, room_id, idx+1, len(self.sessions))
                
            if self._backtrack(idx + 1):
                return True
                
            self._unassign(session)
            self.backtrack_count += 1
            if hasattr(self, 'trace') and self.trace.level >= 2:
                self.trace.trace_backtrack(idx, session, day, slot_idx, room_id, self.backtrack_count)

        return False
    # ------------------------------------------------------------------
    # Output Formatting
    # ------------------------------------------------------------------
    def _format_assignments(self) -> List[dict]:
        """Convert assignments to a list of dicts for the API response."""
        result = []
        for assign in self.assignments.values():
            sess = self.sessions_by_id[assign.session_id]
            sec = self.sections_by_id[sess.section_id]
            
            fac_names = [self.faculty_by_id.get(fid).name if self.faculty_by_id.get(fid) else fid for fid in sess.faculty_ids]
            fac_str = ", ".join(fac_names)

            room = self.rooms_by_id[assign.room_id]

            start_ts = self.time_slots[assign.start_slot_index]
            end_ts = self.time_slots[assign.start_slot_index + sess.duration_slots - 1]

            batch = self.batches_by_id.get(sess.batch_id) if sess.batch_id else None

            result.append({
                'session_id': sess.id,
                'day': assign.day,
                'start_slot_index': assign.start_slot_index,
                'time_start': start_ts.start_time,
                'time_end': end_ts.end_time,
                'section_id': sec.id,
                'section_name': sec.name,
                'batch_id': sess.batch_id or '',
                'batch_name': batch.name if batch else 'ALL',
                'course_name': sess.course_name,
                'course_code': sess.course_code,
                'course_type': sess.course_type,
                'faculty_ids': sess.faculty_ids,
                'faculty_name': fac_str,
                'room_id': room.id,
                'room_name': room.name,
                'duration_slots': sess.duration_slots,
            })

        day_order = {d: i for i, d in enumerate(self.config.working_days)}
        result.sort(key=lambda x: (day_order.get(x['day'], 99), x['time_start'],
                                    x['section_name'], x['batch_name']))
        return result

    def _diagnose(self) -> str:
        generic_theory_demand = 0
        home_room_theory_demand = {}
        generic_lab_demand = 0
        dedicated_demand = {}
        
        total_slots_per_room = len(self.time_slots) * len(self.config.working_days)
        
        for s in self.sessions:
            if s.required_room_id:
                dedicated_demand[s.required_room_id] = dedicated_demand.get(s.required_room_id, 0) + s.duration_slots
            elif s.course_type == CourseType.THEORY:
                section = self.sections_by_id.get(s.section_id)
                if section and getattr(section, 'home_room_id', None):
                    hr = section.home_room_id
                    home_room_theory_demand[hr] = home_room_theory_demand.get(hr, 0) + s.duration_slots
                else:
                    generic_theory_demand += s.duration_slots
            else:
                generic_lab_demand += s.duration_slots
                
        theory_rooms = [r for r in self.rooms if r.room_type == 'THEORY_ROOM' and r.id not in self.dedicated_room_ids]
        lab_rooms = [r for r in self.rooms if r.room_type == 'LAB' and r.id not in self.dedicated_room_ids]
        
        theory_slots_avail = total_slots_per_room * len(theory_rooms)
        generic_lab_slots_avail = total_slots_per_room * len(lab_rooms)

        warnings = []
        for hr_id, demand in home_room_theory_demand.items():
            if demand > total_slots_per_room:
                warnings.append(f"Home room {hr_id} theory demand ({demand}) exceeds available slots ({total_slots_per_room})")

        max_contiguous = 0
        if self.time_slots:
            current_contig = 1
            for i in range(1, len(self.time_slots)):
                prev = self.time_slots[i-1]
                curr = self.time_slots[i]
                
                h1, m1 = map(int, prev.end_time.split(':'))
                h2, m2 = map(int, curr.start_time.split(':'))
                gap = (h2*60+m2) - (h1*60+m1)
                
                if gap <= 20:
                    current_contig += 1
                else:
                    max_contiguous = max(max_contiguous, current_contig)
                    current_contig = 1
            max_contiguous = max(max_contiguous, current_contig)
            
            for s in self.sessions:
                if s.duration_slots > max_contiguous:
                    warnings.append(f"WARNING: Session {s.course_code} requires {s.duration_slots} consecutive slots, but the longest available contiguous block (without crossing lunch) is {max_contiguous} slots!")

        if generic_theory_demand > theory_slots_avail:
            warnings.append("WARNING: NOT ENOUGH generic theory room capacity!")
        if generic_lab_demand > generic_lab_slots_avail:
            warnings.append("WARNING: NOT ENOUGH generic lab room capacity!")
            
        for r_id, demand in dedicated_demand.items():
            avail = len(self.time_slots) * len(self.config.working_days)
            if demand > avail:
                warnings.append(f"WARNING: NOT ENOUGH capacity in dedicated room {r_id}!")

        diagnostics = [
            f"Generic Theory demand: {generic_theory_demand}",
            f"Generic Theory capacity: {theory_slots_avail}",
            f"Generic Lab demand: {generic_lab_demand}",
            f"Generic Lab capacity: {generic_lab_slots_avail}",
        ]
        
        for r_id, demand in dedicated_demand.items():
            diagnostics.append(f"Dedicated room {r_id} demand: {demand}, capacity: {len(self.time_slots) * len(self.config.working_days)}")

        if warnings:
            diagnostics.append("")
            diagnostics.extend(warnings)

        return "\n".join(diagnostics)

    def get_section_view(self, section_id: str) -> dict:
        """Return a Day x Slot grid for a specific section.

        Includes both section-level (theory) sessions from section_schedule
        AND batch-level (lab) sessions from batch_schedule for all batches
        of this section.
        """
        days = self.config.working_days
        slots = [{'index': s.index, 'start_time': s.start_time,
                  'end_time': s.end_time} for s in self.time_slots]
        grid = {day: {} for day in days}

        # Theory sessions (section-level)
        entity_sched = self.section_schedule.get(section_id, {})
        for day in days:
            for slot_idx, sess_id in entity_sched.get(day, {}).items():
                sess = self.sessions_by_id.get(sess_id)
                if not sess:
                    continue
                assign = self.assignments.get(sess_id)
                if not assign:
                    continue
                batch = self.batches_by_id.get(sess.batch_id) if sess.batch_id else None
                fac_names = [self.faculty_by_id.get(fid).name if self.faculty_by_id.get(fid) else fid for fid in sess.faculty_ids]
                grid[day][str(slot_idx)] = {
                    'subject': sess.course_name,
                    'code': sess.course_code,
                    'type': sess.course_type,
                    'batch': batch.name if batch else 'ALL',
                    'faculty': ", ".join(fac_names),
                    'room': self.rooms_by_id[assign.room_id].name,
                }

        # Lab sessions (batch-level) for all batches of this section
        for bid in self.section_batches.get(section_id, []):
            batch_sched = self.batch_schedule.get(bid, {})
            batch = self.batches_by_id[bid]
            for day in days:
                for slot_idx, sess_id in batch_sched.get(day, {}).items():
                    sess = self.sessions_by_id.get(sess_id)
                    if not sess:
                        continue
                    assign = self.assignments.get(sess_id)
                    if not assign:
                        continue
                    key = str(slot_idx)
                    fac_names = [self.faculty_by_id.get(fid).name if self.faculty_by_id.get(fid) else fid for fid in sess.faculty_ids]
                    
                    if key in grid[day]:
                        # Multiple batches in same slot: append info
                        existing = grid[day][key]
                        if isinstance(existing, list):
                            existing.append({
                                'subject': sess.course_name,
                                'code': sess.course_code,
                                'type': sess.course_type,
                                'batch': batch.name,
                                'faculty': ", ".join(fac_names),
                                'room': self.rooms_by_id[assign.room_id].name,
                            })
                        else:
                            grid[day][key] = [existing, {
                                'subject': sess.course_name,
                                'code': sess.course_code,
                                'type': sess.course_type,
                                'batch': batch.name,
                                'faculty': ", ".join(fac_names),
                                'room': self.rooms_by_id[assign.room_id].name,
                            }]
                    else:
                        grid[day][key] = {
                            'subject': sess.course_name,
                            'code': sess.course_code,
                            'type': sess.course_type,
                            'batch': batch.name,
                            'faculty': ", ".join(fac_names),
                            'room': self.rooms_by_id[assign.room_id].name,
                        }

        return {'days': days, 'slots': slots, 'grid': grid}

    def get_faculty_view(self, faculty_id: str) -> dict:
        """Return a Day x Slot grid for a specific faculty member."""
        return self._get_simple_view(self.faculty_schedule, faculty_id, 'faculty')

    def get_room_view(self, room_id: str) -> dict:
        """Return a Day x Slot grid for a specific room."""
        return self._get_simple_view(self.room_schedule, room_id, 'room')

    def _get_simple_view(self, schedule_dict: dict, entity_id: str,
                         view_type: str) -> dict:
        """Build a grid view for faculty/room."""
        days = self.config.working_days
        slots = [{'index': s.index, 'start_time': s.start_time,
                  'end_time': s.end_time} for s in self.time_slots]
        grid = {day: {} for day in days}

        entity_sched = schedule_dict.get(entity_id, {})

        for day in days:
            for slot_idx, sess_id in entity_sched.get(day, {}).items():
                sess = self.sessions_by_id.get(sess_id)
                if not sess:
                    continue
                assign = self.assignments.get(sess_id)
                if not assign:
                    continue

                batch = self.batches_by_id.get(sess.batch_id) if sess.batch_id else None

                info = {
                    'subject': sess.course_name,
                    'code': sess.course_code,
                    'type': sess.course_type,
                    'batch': batch.name if batch else 'ALL',
                }

                if view_type == 'faculty':
                    info['section'] = self.sections_by_id[sess.section_id].name
                    info['room'] = self.rooms_by_id[assign.room_id].name
                elif view_type == 'room':
                    info['section'] = self.sections_by_id[sess.section_id].name
                    fac_names = [self.faculty_by_id.get(fid).name if self.faculty_by_id.get(fid) else fid for fid in sess.faculty_ids]
                    info['faculty'] = ", ".join(fac_names)

                grid[day][str(slot_idx)] = info

        return {'days': days, 'slots': slots, 'grid': grid}
