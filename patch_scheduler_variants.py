import re

with open('scheduler.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add import random if not there
if 'import random' not in code:
    code = code.replace('import time', 'import time\nimport random')

# 2. Update _score_candidate to use randomness
old_score = """        sec_sched = self.section_schedule.get(session.section_id, {})
        section_day_load = len(sec_sched.get(day, {}))
        score -= section_day_load * 2"""

new_score = """        sec_sched = self.section_schedule.get(session.section_id, {})
        section_day_load = len(sec_sched.get(day, {}))
        score -= section_day_load * 2
        
        # Add random noise based on variant_seed to generate different valid timetables
        if getattr(self, 'variant_seed', 0) > 0:
            score += random.uniform(-5, 5)"""
code = code.replace(old_score, new_score)

# 3. Update solve() to generate 3 variants
old_solve_start = """    def solve(self) -> dict:
        \"\"\"Main entry point: solve the CSP and return the result.\"\"\"
        # Static MRV ordering: labs first, then by number of suitable rooms"""

old_solve = code[code.find(old_solve_start):code.find('def _backtrack(self, idx: int) -> bool:')]

new_solve = """    def solve(self, num_variants=3) -> dict:
        \"\"\"Main entry point: solve the CSP and return multiple variants.\"\"\"
        # Compute true domain sizes for MRV
        domain_sizes = {}
        for s in self.sessions:
            domain_sizes[s.id] = len(self._get_domain(s))
            
        self.sessions.sort(
            key=lambda s: (domain_sizes[s.id], -s.duration_slots)
        )

        variants = []
        best_assignments = None
        
        for v in range(num_variants):
            self.assignments.clear()
            self.section_schedule.clear()
            self.faculty_schedule.clear()
            self.room_schedule.clear()
            self.backtrack_count = 0
            self.start_time = time.time()
            self.variant_seed = v
            
            if self._backtrack(0):
                assignments_list = list(self.assignments.values())
                soft_score = compute_total_soft_score(
                    assignments_list, self.sessions, self.config, self.time_slots
                )
                elapsed_ms = int((time.time() - self.start_time) * 1000)
                
                # Store deep copy of assignments
                import copy
                variants.append({
                    'index': v,
                    'assignments_data': [a.to_dict() for a in assignments_list],
                    'soft_score': soft_score,
                    'stats': {
                        'total_sessions': len(self.sessions),
                        'backtracks': self.backtrack_count,
                        'time_ms': elapsed_ms,
                    }
                })
            else:
                if v == 0:
                    return {
                        'status': 'infeasible',
                        'message': 'No feasible timetable found...',
                        'diagnostics': self._diagnose()
                    }
                break

        # Sort variants by soft score total descending
        variants.sort(key=lambda x: -x['soft_score']['total'])
        
        # Load the best variant as the active state
        self.load_assignments_data(variants[0]['assignments_data'])
                
        return {
            'status': 'success',
            'variants': variants,
            'active_variant_index': 0
        }
        
    def load_assignments_data(self, assignments_data: list):
        \"\"\"Load a specific variant's state into the engine.\"\"\"
        self.assignments.clear()
        self.section_schedule.clear()
        self.faculty_schedule.clear()
        self.room_schedule.clear()
        
        for ad in assignments_data:
            from models import Assignment
            assign = Assignment.from_dict(ad)
            sess = self.sessions_by_id[assign.session_id]
            self._assign(sess, assign.day, assign.start_slot_index, assign.room_id)

"""
code = code.replace(old_solve, new_solve)

with open('scheduler.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Scheduler patched for multiple variants!")
