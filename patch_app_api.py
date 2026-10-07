import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix POST
post_replacement = """            p=float(data.get('p', 0)),
            faculty_ids=data.get('faculty_ids', []),
            assistant_faculty_ids=data.get('assistant_faculty_ids', []),
            room_type=data.get('room_type', RoomType.THEORY_ROOM),"""
content = re.sub(
    r"p=int\(data\.get\('p', 0\)\),\s*faculty_ids=data\.get\('faculty_ids', \[\]\),\s*room_type=data\.get\('room_type', RoomType\.THEORY_ROOM\),",
    post_replacement,
    content
)

# Fix PUT
put_replacement = """                section_id=data['section_id'],
                l=float(data.get('l', 0)),
                t=float(data.get('t', 0)),
                p=float(data.get('p', 0)),
                faculty_ids=data.get('faculty_ids', []),
                assistant_faculty_ids=data.get('assistant_faculty_ids', []),
                room_type=data['room_type'],"""
content = re.sub(
    r"section_id=data\['section_id'\],\s*course_type=data\['course_type'\],\s*l=float\(data\.get\('l', 0\)\),\s*t=float\(data\.get\('t', 0\)\),\s*p=float\(data\.get\('p', 0\)\),\s*faculty_ids=data\.get\('faculty_ids', \[\]\),\s*room_type=data\['room_type'\],",
    put_replacement,
    content
)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("app.py patched!")
