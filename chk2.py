import json
with open('database.json', 'r') as f:
    db = json.load(f)
for c in db['courses']:
    if c['id'] in ['C5A06', 'C5A08']:
        print(f"{c['id']} req={c.get('required_room_id')}")
for r in db['rooms']:
    if r['name'] == 'CLH310' or r['id'] == 'R007' or r['id'] == 'CLH310':
        print(r)
