import json
with open('database.json', 'r') as f:
    db = json.load(f)
room_map = {r['name']: r['id'] for r in db['rooms']}
for c in db['courses']:
    req = c.get('required_room_id')
    if req in room_map:
        c['required_room_id'] = room_map[req]
        print(f"Fixed {c['id']}: {req} -> {room_map[req]}")
with open('database.json', 'w') as f:
    json.dump(db, f, indent=2)
