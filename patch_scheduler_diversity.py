import re

with open('scheduler.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update solve signature and diversity mapping
new_solve_sig = """    def solve(self, seed=None, previous_alternatives=None) -> dict:
        \"\"\"Main entry point: solve the CSP and return a single result.\"\"\"
        self.diversity_penalties = {}
        if previous_alternatives:
            for alt in previous_alternatives:
                for ad in alt['assignments_data']:
                    key = (ad['session_id'], ad['day'], ad['start_slot_index'], ad['room_id'])
                    self.diversity_penalties[key] = self.diversity_penalties.get(key, 0) + 1
                    
        domain_sizes = {}"""
        
code = code.replace("""    def solve(self, seed=None) -> dict:
        \"\"\"Main entry point: solve the CSP and return a single result.\"\"\"
        domain_sizes = {}""", new_solve_sig)


# 2. Add diversity bonus/penalty in _score_candidate
old_score_return = """            rng = random.Random(rng_seed)
            # Add tie-breaking noise. Keep it smaller than major heuristics
            score += rng.uniform(-0.05, 0.05)

        return score"""
        
new_score_return = """            rng = random.Random(rng_seed)
            # Add tie-breaking noise. Keep it smaller than major heuristics
            score += rng.uniform(-0.05, 0.05)

        # Diversity pressure bonus/penalty
        if getattr(self, 'diversity_penalties', None):
            key = (session.id, day, start_slot_idx, room_id)
            penalty = self.diversity_penalties.get(key, 0)
            score -= penalty * 1.5  # Encourage different choices!

        return score"""
        
code = code.replace(old_score_return, new_score_return)


# 3. Add _calculate_diversity and update solve_multiple
new_methods = """    def _calculate_diversity(self, assignments_list, previous_alternatives):
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
    
# Replace everything from def solve_multiple to def load_assignments_data
match = re.search(r'    def solve_multiple.*?    def load_assignments_data', code, re.DOTALL)
if match:
    code = code[:match.start()] + new_methods + code[match.end()-len('    def load_assignments_data'):]
else:
    print("Match failed for solve_multiple")

with open('scheduler.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("scheduler patched with diversity!")
