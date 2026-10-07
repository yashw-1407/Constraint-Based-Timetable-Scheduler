import json
with open('database.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

for c in db['courses']:
    # Keep required room ONLY for Mini Project and AI-Assisted
    if 'Mini Project' in c['name'] or 'AI-Assisted' in c['name']:
        pass
    else:
        c['required_room_id'] = ''

with open('database.json', 'w', encoding='utf-8') as f:
    json.dump(db, f, indent=4)
print("Cleared all required_room_ids except for special fixed courses.")
