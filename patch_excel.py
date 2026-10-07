import re

with open('excel_import.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace(
    'ws.append(["section_id", "name", "semester", "division", "strength"])',
    'ws.append(["section_id", "name", "semester", "division", "strength", "home_room_id"])'
)
code = code.replace(
    'ws.append(["3A", "Section 3A", 3, "A", 60])',
    'ws.append(["3A", "Section 3A", 3, "A", 60, "R101"])'
)

old_parse = """            data['sections'].append(Section(
                id=str(r['section_id']), name=str(r['name']),
                semester=int(r['semester']), division=str(r['division']),
                strength=int(r['strength']) if r.get('strength') else None
            ))"""

new_parse = """            data['sections'].append(Section(
                id=str(r['section_id']), name=str(r['name']),
                semester=int(r['semester']), division=str(r['division']),
                strength=int(r['strength']) if r.get('strength') else None,
                home_room_id=str(r.get('home_room_id')).strip() if r.get('home_room_id') and str(r.get('home_room_id')).strip() not in ('None', '') else None
            ))"""
            
code = code.replace(old_parse, new_parse)

with open('excel_import.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Patched excel_import.py")
