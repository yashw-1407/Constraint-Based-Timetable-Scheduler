import re

with open('scheduler.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_get_suitable = """    def _get_suitable_rooms(self, session: ScheduleSession) -> List[Room]:
        \"\"\"Get rooms suitable for a session (type match, capacity, specific room).\"\"\"
        suitable = []
        strength = self._get_scheduling_strength(session)
        for r in self.rooms:
            # Check exclusivity constraint for dedicated rooms
            if r.id in self.dedicated_room_ids and session.required_room_id != r.id:
                continue
                
            if not check_room_suitability(session, r):
                continue
            if not check_room_capacity_by_strength(r, strength):
                continue
            suitable.append(r)
        return suitable"""
        
new_get_suitable = """    def _get_suitable_rooms(self, session: ScheduleSession) -> List[Room]:
        \"\"\"Get rooms suitable for a session (type match, capacity, specific room).\"\"\"
        suitable = []
        strength = self._get_scheduling_strength(session)
        
        # Determine if we should enforce a section home room
        home_room_id = None
        if not session.required_room_id and session.course_type == CourseType.THEORY:
            section = self.sections_by_id.get(session.section_id)
            if section and getattr(section, 'home_room_id', None):
                home_room_id = section.home_room_id
                
        for r in self.rooms:
            # Check exclusivity constraint for dedicated rooms
            if r.id in self.dedicated_room_ids and session.required_room_id != r.id:
                continue
                
            # If home room applies, ONLY allow the home room
            if home_room_id and r.id != home_room_id:
                continue
                
            if not check_room_suitability(session, r):
                continue
            if not check_room_capacity_by_strength(r, strength):
                continue
            suitable.append(r)
            
        return suitable"""
        
code = code.replace(old_get_suitable, new_get_suitable)

with open('scheduler.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("scheduler.py patched for suitable rooms")
