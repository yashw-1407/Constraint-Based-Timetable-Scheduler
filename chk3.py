import json
with open('database.json', 'r') as f:
    db = json.load(f)
for c in db['courses']:
    if c['id'] in ['C5A06', 'C5A08']:
        print(f"{c['id']} L={c.get('l')} P={c.get('p')}")
