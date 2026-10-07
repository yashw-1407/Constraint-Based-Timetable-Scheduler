import json
with open('database.json', 'r') as f:
    db = json.load(f)
for c in db['courses']:
    if c['id'] in ['C5A08', 'C5B08']:
        print(f"{c['id']} {c['faculty_ids']}")
