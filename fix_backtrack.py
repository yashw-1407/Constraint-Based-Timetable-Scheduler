import re

with open('scheduler.py', 'r', encoding='utf-8') as f:
    code = f.read()

backtrack_repl = """    def _backtrack(self, idx: int) -> bool:
        \"\"\"Recursive backtracking search with MRV and value ordering.\"\"\"
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

        return False\n"""

code = code.replace('    def _backtrack(self, idx: int) -> bool:\n', backtrack_repl)

with open('scheduler.py', 'w', encoding='utf-8') as f:
    f.write(code)
