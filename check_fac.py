import json
with open('database.json', 'r', encoding='utf-8') as f: db = json.load(f)

fac = {}
for c in db['courses']:
    f_ids = c.get('faculty_ids', [])
    for f in f_ids:
        theory_slots = c['l'] + c['t']
        lab_slots = c['p'] * len(c.get('lab_batches', []))
        fac[f] = fac.get(f, 0) + theory_slots + lab_slots
        
for k, v in fac.items():
    print(f"Faculty {k} teaches {v} slots")
