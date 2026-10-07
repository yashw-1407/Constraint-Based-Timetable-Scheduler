import re

# Patch scheduler.py
with open("scheduler.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add assistant teachers to batch_facs
content = re.sub(
    r'(fac = course.faculty_ids\[b_idx % len\(course.faculty_ids\)\]\s*\n\s*batch_facs = \[fac\])',
    r'\1 + getattr(course, "assistant_faculty_ids", [])',
    content
)

# Also handle the case where course.faculty_ids is empty but assistant teachers exist
content = re.sub(
    r'(batch_facs = \[\]\s*\n\s*if course.faculty_ids:)',
    r'batch_facs = getattr(course, "assistant_faculty_ids", []).copy()\n                    if course.faculty_ids:',
    content
)

with open("scheduler.py", "w", encoding="utf-8") as f:
    f.write(content)

# Patch excel_import.py
with open("excel_import.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add assistant_faculty_ids to the template generator
content = content.replace(
    '"faculty_ids", "room_type", "required_room", "lab_batches"',
    '"faculty_ids", "assistant_faculty_ids", "room_type", "required_room", "lab_batches"'
)
content = content.replace(
    '2, "F001,F002", "THEORY_ROOM"',
    '2, "F001,F002", "F003,F004", "THEORY_ROOM"'
)
content = content.replace(
    '0, "F002", "THEORY_ROOM"',
    '0, "F002", "", "THEORY_ROOM"'
)

# Add assistant_faculty_ids parsing
replacement = """fac_str = str(r.get('faculty_ids') or '')
            fac_ids = [f.strip() for f in fac_str.split(',')] if fac_str and fac_str.strip() else []
            
            asst_fac_str = str(r.get('assistant_faculty_ids') or '')
            asst_fac_ids = [f.strip() for f in asst_fac_str.split(',')] if asst_fac_str and asst_fac_str.strip() else []"""

content = content.replace(
    "fac_str = str(r.get('faculty_ids') or '')\n            fac_ids = [f.strip() for f in fac_str.split(',')] if fac_str and fac_str.strip() else []",
    replacement
)

content = content.replace(
    "faculty_ids=fac_ids,\n                room_type",
    "faculty_ids=fac_ids,\n                assistant_faculty_ids=asst_fac_ids,\n                room_type"
)

with open("excel_import.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied to scheduler.py and excel_import.py")
