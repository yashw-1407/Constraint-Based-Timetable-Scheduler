import re

with open('excel_import.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = '''
            req_room_raw = str(r.get('required_room')).strip() if r.get('required_room') else None
            req_room_id = None
            if req_room_raw:
                # Try to map by name first
                matched_room = next((rm for rm in data['rooms'] if rm['name'] == req_room_raw or rm['id'] == req_room_raw), None)
                if matched_room:
                    req_room_id = matched_room['id']
                else:
                    req_room_id = req_room_raw # fallback

            data['courses'].append(dict(
                id=str(r.get('course_id')),
                name=str(r.get('name')),
                code=str(r.get('code')),
                section_id=str(r.get('section_id')),
                course_type="THEORY" if float(r.get('L') or 0) > 0 else "LAB",
                l=float(r.get('L') or 0),
                t=float(r.get('T') or 0),
                p=float(r.get('P') or 0),
                faculty_ids=fac_ids,
                room_type=str(r.get('room_type') or 'THEORY_ROOM'),
                required_room_id=req_room_id,
                lab_batches=batches
            ))
'''

# Find the start of data['courses'].append and replace it.
start_idx = content.find("data['courses'].append(dict(")
if start_idx != -1:
    end_idx = content.find("))", start_idx) + 2
    content = content[:start_idx] + replacement.strip() + content[end_idx:]

with open('excel_import.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("excel_import patched.")
