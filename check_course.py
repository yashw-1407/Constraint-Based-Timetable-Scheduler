import json
with open('database.json', 'r', encoding='utf-8') as f:
    db = json.load(f)
c = next(c for c in db['courses'] if c['code'] == '26EMAB229')
print(f"{c['name']}, type={c.get('course_type', 'N/A')}, p={c['p']}, req={c['required_room_id']}")
