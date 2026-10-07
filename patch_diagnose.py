import re

with open('scheduler.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_diag = """    def _diagnose(self) -> str:
        theory_demand = 0
        generic_lab_demand = 0
        dedicated_demand = {}
        
        for s in self.sessions:
            if s.required_room_id:
                dedicated_demand[s.required_room_id] = dedicated_demand.get(s.required_room_id, 0) + s.duration_slots
            elif s.room_type == 'THEORY_ROOM':
                theory_demand += s.duration_slots
            elif s.room_type == 'LAB':
                generic_lab_demand += s.duration_slots
                
        theory_slots_avail = len(self.time_slots) * len(self.config.working_days) * len(
            [r for r in self.rooms if r.room_type == 'THEORY_ROOM' and r.id not in self.dedicated_room_ids]
        )
        generic_lab_slots_avail = len(self.time_slots) * len(self.config.working_days) * len(
            [r for r in self.rooms if r.room_type == 'LAB' and r.id not in self.dedicated_room_ids]
        )

        warnings = []"""
        
new_diag = """    def _diagnose(self) -> str:
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
"""

code = code.replace(old_diag, new_diag)

old_diag2 = """        if theory_demand > theory_slots_avail:
            warnings.append(f"Theory demand ({theory_demand}) exceeds available generic theory slots ({theory_slots_avail})")"""
            
new_diag2 = """        if generic_theory_demand > theory_slots_avail:
            warnings.append(f"Generic theory demand ({generic_theory_demand}) exceeds available generic theory slots ({theory_slots_avail})")"""
            
code = code.replace(old_diag2, new_diag2)

with open('scheduler.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("diagnose patched")
