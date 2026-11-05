import json
with open('database.json', 'r') as f:
    total = 0
    for c in json.load(f)['courses']:
        if c.get('p', 0) > 0 and not c.get('required_room_id'):
            d = c['p'] * max(1, len(c.get('lab_batches', [])))
            print(f"{c['name']}: {c['p']} * {max(1, len(c.get('lab_batches',[])))} = {d}")
            total += d
    print(f"Total: {total}")
