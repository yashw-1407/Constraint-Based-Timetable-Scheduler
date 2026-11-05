import re

def patch_scheduler():
    with open('scheduler.py', 'r', encoding='utf-8') as f:
        code = f.read()

    # 1. Init patch
    if 'self.trace = kwargs.get' not in code and 'self.trace = trace' not in code:
        code = code.replace(
            'def __init__(self, config: WorkingConfig, courses: List[Course],',
            'def __init__(self, config: WorkingConfig, courses: List[Course],'
        )
        # Already done partially by previous prompt, let's fix it safely:
        init_decl = 'def __init__(self, config: WorkingConfig, courses: List[Course],\n                 rooms: List[Room], faculty_list: List[Faculty],\n                 sections: List[Section], batches: List[Batch] = None, trace: SchedulerTrace = None):'
        if init_decl not in code:
            code = re.sub(
                r'def __init__\(self, config: WorkingConfig, courses: List\[Course\],\s*rooms: List\[Room\], faculty_list: List\[Faculty\],\s*sections: List\[Section\], batches: List\[Batch\] = None\):',
                'def __init__(self, config: WorkingConfig, courses: List[Course],\n                 rooms: List[Room], faculty_list: List[Faculty],\n                 sections: List[Section], batches: List[Batch] = None, trace=None):',
                code
            )
            code = code.replace(
                'self.config = config',
                'self.trace = trace or SchedulerTrace(level=0)\n        self.config = config'
            )

    # 2. _create_sessions trace
    sess_create_t = """                    self.sessions_by_id[sess.id] = sess
                    if hasattr(self, 'trace'):
                        sec = self.sections_by_id.get(course.section_id)
                        self.trace.trace_session_created(sess, course, sec, None)"""
    code = code.replace("                    self.sessions_by_id[sess.id] = sess", sess_create_t, 1)

    sess_create_l = """                    self.sessions_by_id[sess.id] = sess
                    if hasattr(self, 'trace'):
                        sec = self.sections_by_id.get(course.section_id)
                        bat = self.batches_by_id.get(batch_id) if batch_id else None
                        self.trace.trace_session_created(sess, course, sec, bat)"""
    # Second occurrence (in lab)
    code = code.replace("                    self.sessions_by_id[sess.id] = sess", sess_create_l)
    code = code.replace(sess_create_t.replace("                    self.sessions_by_id[sess.id] = sess\n", "                    self.sessions_by_id[sess.id] = sess\n" + " "*20), sess_create_t) # fixing if accidentally replaced both
    

    # 3. _get_suitable_rooms trace
    # Let's completely replace _get_suitable_rooms to add tracing
    code = re.sub(
        r'    def _get_suitable_rooms.*?return suitable',
        '''    def _get_suitable_rooms(self, session: ScheduleSession) -> List[Room]:
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
            
        return suitable''',
        code, flags=re.DOTALL
    )

    # 4. _get_domain trace
    code = code.replace(
        'return domain',
        '''if hasattr(self, 'trace'):
            self.trace.trace_domain_size(session, len(domain), len(suitable_rooms), len(self.config.working_days))
        return domain'''
    )

    # 5. _check_hard_constraints
    # Replace the body of _check_hard_constraints to return the constraint that failed, instead of just boolean.
    # Actually, we need to keep _check_hard_constraints returning bool, but we also want the trace to see it.
    # Let's change _check_hard_constraints to return (bool, failed_constraint_name)
    
    check_hc = '''    def _check_hard_constraints(self, session: ScheduleSession, day: str,
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
        return True, None'''
    
    code = re.sub(
        r'    def _check_hard_constraints.*?return True',
        check_hc,
        code, flags=re.DOTALL
    )

    # Update _backtrack to handle tuple
    code = code.replace(
        'if not self._check_hard_constraints(session, day, slot_indices, room_id):',
        'is_valid, fail_reason = self._check_hard_constraints(session, day, slot_indices, room_id)\n            if not is_valid:'
    )
    
    code = code.replace(
        '                continue',
        '''                if hasattr(self, 'trace') and self.trace.level >= 2:
                    self.trace.trace_candidate_rejected(session, day, start_idx if 'start_idx' in locals() else slot_idx, room_id, fail_reason)
                continue'''
    )
    # Wait, the first loop in _backtrack has `start_idx`. The second has `slot_idx`. Let's fix that.
    code = code.replace("if 'start_idx' in locals() else slot_idx", "start_idx if 'start_idx' in locals() else slot_idx") # Will do below

    # Let's do _backtrack cleanly.
    backtrack_regex = r'    def _backtrack\(self, idx: int\) -> bool:.*?return False'
    backtrack_repl = '''    def _backtrack(self, idx: int) -> bool:
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

        return False'''
    
    code = re.sub(backtrack_regex, backtrack_repl, code, flags=re.DOTALL)

    # 6. Final Result trace
    code = code.replace(
        "            return {\n                'status': 'success',",
        """            if hasattr(self, 'trace'):
                self.trace.trace_final_result('success', len(self.sessions), len(self.assignments), self.backtrack_count, time.time() - self.start_time, len(self.sessions))
                self.trace.trace_room_utilization(self.rooms, self.room_schedule, self.time_slots, self.config.working_days, self.dedicated_room_ids, list(self.sections_by_id.values()))
                self.trace.trace_course_summary(list(self.courses_by_id.values()), self.sessions, self.assignments)
            return {
                'status': 'success',"""
    )
    code = code.replace(
        "            return {\n                'status': 'infeasible',",
        """            if hasattr(self, 'trace'):
                self.trace.trace_final_result('infeasible', len(self.sessions), len(self.assignments), self.backtrack_count, time.time() - self.start_time, self.trace._max_depth if hasattr(self.trace, '_max_depth') else 0)
                self.trace.trace_room_utilization(self.rooms, self.room_schedule, self.time_slots, self.config.working_days, self.dedicated_room_ids, list(self.sections_by_id.values()))
                self.trace.trace_course_summary(list(self.courses_by_id.values()), self.sessions, self.assignments)
            return {
                'status': 'infeasible',"""
    )

    with open('scheduler.py', 'w', encoding='utf-8') as f:
        f.write(code)

patch_scheduler()
