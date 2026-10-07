import json

with open('database.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

for s in db['sections']:
    if s['id'] == 'S3A': s['home_room_id'] = 'R005'
    elif s['id'] == 'S3B': s['home_room_id'] = 'R006'
    elif s['id'] == 'S5A': s['home_room_id'] = 'R003'
    elif s['id'] == 'S5B': s['home_room_id'] = 'R004'

with open('database.json', 'w', encoding='utf-8') as f:
    json.dump(db, f, indent=4)
print("Updated database.json with section home rooms using S3A, etc")
