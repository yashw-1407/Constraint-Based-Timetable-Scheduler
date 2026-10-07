import json
with open('database.json', 'r') as f:
    for c in json.load(f)['courses']:
        if 'Lab' in c['name'] or 'Project' in c['name'] or 'AI-Assisted' in c['name']:
            print(f"{c['name']}: P={c.get('p')}")
