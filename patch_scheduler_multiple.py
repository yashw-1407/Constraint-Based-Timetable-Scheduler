import re

with open('scheduler.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace _score_candidate to use random if seed is set
old_score = """        # Add random noise based on variant_seed to generate different valid timetables
        if getattr(self, 'variant_seed', 0) > 0:
            score += random.uniform(-5, 5)"""
            
new_score = """        # Add random noise based on variant_seed to generate different valid timetables
        if getattr(self, 'variant_seed', None) is not None:
            # use a local random instance initialized with the seed
            import random
            rng = random.Random(self.variant_seed + hash(session.id) + start_slot_idx)
            score += rng.uniform(-5, 5)"""
code = code.replace(old_score, new_score)


match = re.search(r'# ------------------------------------------------------------------\n\s*# Main Solving.*?def load_assignments_data', code, re.DOTALL)

new_main = """# ------------------------------------------------------------------
    # Main Solving
    # ------------------------------------------------------------------
    def solve(self, seed=None) -> dict:
        \"\"\"Main entry point: solve the CSP and return a single result.\"\"\"
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

    def solve_multiple(self, requested_count=5, base_seed=1000, max_attempts=30) -> dict:
        alternatives = []
        signatures = set()
        
        for attempt in range(max_attempts):
            seed = base_seed + attempt
            result = self.solve(seed=seed)
            
            if result.get('status') == 'success':
                assigns = list(self.assignments.values())
                signature = self._create_signature(assigns)
                
                if signature not in signatures:
                    signatures.add(signature)
                    # Create the alternative structure
                    alternatives.append({
                        'alternative_id': len(alternatives) + 1,
                        'seed': seed,
                        'assignments_data': result['assignments_data'],
                        'soft_score': result['soft_score'],
                        'stats': result['stats'],
                        'signature': signature
                    })
                    
            if len(alternatives) == requested_count:
                break
                
        # By default, sort by soft score or just leave as is. User didn't specify sorting, but it's nice.
        alternatives.sort(key=lambda x: -x['soft_score']['total_score'])
        
        if not alternatives:
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

    def load_assignments_data"""

code = code[:match.start()] + new_main + code[match.end():]

with open('scheduler.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Scheduler rewritten!")
