import json
with open('database.json', 'r', encoding='utf-8') as f:
    db = json.load(f)
c = next(c for c in db['courses'] if c['id'] == 'C3A06')
print(f"C3A06: room_type={c.get('room_type')}")
