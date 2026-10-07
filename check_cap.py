import json
with open('database.json', 'r', encoding='utf-8') as f: db = json.load(f)
for s in db['sections']: print(f"Section {s['id']}: strength={s['strength']}, hr={s.get('home_room_id')}")
for r in db['rooms']: print(f"Room {r['id']}: capacity={r['capacity']}")
