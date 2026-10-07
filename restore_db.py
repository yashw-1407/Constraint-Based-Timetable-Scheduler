import json
reqs = {
    'C3A01': 'R005', 'C3A02': 'R005', 'C3A03': 'R005', 'C3A04': 'R005', 'C3A05': 'R005',
    'C3A06': 'R001', 'C3A07': 'R002', 'C3A08': 'R002',
    'C3B01': 'R006', 'C3B02': 'R006', 'C3B03': 'R006', 'C3B04': 'R006', 'C3B05': 'R006',
    'C3B06': 'R001', 'C3B07': 'R002', 'C3B08': 'R002',
    'C5A01': 'R003', 'C5A02': 'R003', 'C5A03': 'R003', 'C5A04': 'R003',
    'C5A05': 'R002', 'C5A06': 'R007', 'C5A08': 'R007',
    'C5B01': 'R004', 'C5B02': 'R004', 'C5B03': 'R004', 'C5B04': 'R004',
    'C5B05': 'R002', 'C5B06': 'R007', 'C5B08': 'R007'
}
with open('database.json', 'r', encoding='utf-8') as f:
    db = json.load(f)
for c in db['courses']:
    if c['id'] in reqs:
        c['required_room_id'] = reqs[c['id']]
for s in db['sections']:
    if s['id'] == 'S3A': s['home_room_id'] = 'R005'
    elif s['id'] == 'S3B': s['home_room_id'] = 'R006'
    elif s['id'] == 'S5A': s['home_room_id'] = 'R003'
    elif s['id'] == 'S5B': s['home_room_id'] = 'R004'
with open('database.json', 'w', encoding='utf-8') as f:
    json.dump(db, f, indent=4)
print("Restored database.json")
