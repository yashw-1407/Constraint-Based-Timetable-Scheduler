import json
with open('database.json', 'r') as f:
    db = json.load(f)
for c in db['courses']:
    if c['p'] > 0:
        print(f"{c['id']} P={c['p']} batches={len(c.get('lab_batches', []))} type={c['room_type']}")
