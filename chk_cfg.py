import json
with open('database.json', 'r') as f:
    db = json.load(f)
print(db['config'])
