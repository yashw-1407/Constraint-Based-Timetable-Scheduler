import json

with open('database.json', 'r') as f:
    db = json.load(f)

db['config'] = {
    "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
    "start_time": "09:00",
    "end_time": "17:00",
    "slot_duration_minutes": 60,
    "lunch_start": "12:15",
    "lunch_end": "13:30",
    "breaks": [
        {"start_time": "10:00", "end_time": "10:15"},
        {"start_time": "15:30", "end_time": "15:45"}
    ]
}

with open('database.json', 'w') as f:
    json.dump(db, f, indent=2)

print("Config updated.")
