import json
with open('database.json', 'r', encoding='utf-8') as f:
    db = json.load(f)
found = False
for c in db['courses']:
    if c.get('required_room_id'):
        print(f"{c['id']}: {c['name']} -> {c['required_room_id']}")
        found = True
if not found:
    print("No required_room_id set in existing courses.")
