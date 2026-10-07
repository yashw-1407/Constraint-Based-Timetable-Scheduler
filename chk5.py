import json
with open('database.json', 'r') as f:
    db = json.load(f)
for c in db['courses']:
    facs = c.get('faculty_ids', [])
    if 'F006' in facs:
        print(f"{c['id']} {c['name']} L={c.get('l')} P={c.get('p')} batches={len(c.get('lab_batches', []))}")
