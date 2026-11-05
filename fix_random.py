import re

with open('scheduler.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_score_return = """        sec_sched = self.section_schedule.get(session.section_id, {})
        section_day_load = len(sec_sched.get(day, {}))
        score -= section_day_load * 0.5

        return score"""
        
new_score_return = """        sec_sched = self.section_schedule.get(session.section_id, {})
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

        return score"""
        
code = code.replace(old_score_return, new_score_return)

with open('scheduler.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Added random noise to _score_candidate!")
