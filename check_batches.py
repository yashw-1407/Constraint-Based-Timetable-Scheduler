import json
with open('database.json', 'r', encoding='utf-8') as f: db = json.load(f)
for b in db['batches']:
    print(f"{b['id']}: {b['strength']}")
