import json
import os
import threading
from models import WorkingConfig, Room, Faculty, Section, Batch, Course

DB_FILE = 'database.json'
_lock = threading.Lock()

def _dataclass_to_dict(obj):
    return obj.to_dict()

def save_data(app_data):
    """Transactional save to JSON file."""
    with _lock:
        data = {
            'config': app_data['config'].to_dict() if app_data['config'] else None,
            'rooms': [r.to_dict() for r in app_data['rooms']],
            'faculty': [f.to_dict() for f in app_data['faculty']],
            'sections': [s.to_dict() for s in app_data['sections']],
            'batches': [b.to_dict() for b in app_data['batches']],
            'courses': [c.to_dict() for c in app_data['courses']],
        }
        temp_file = DB_FILE + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(temp_file, DB_FILE)

def load_data(app_data):
    """Load from JSON file into app_data."""
    with _lock:
        if not os.path.exists(DB_FILE):
            return
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('config'):
                app_data['config'] = WorkingConfig.from_dict(data['config'])
            app_data['rooms'] = [Room.from_dict(d) for d in data.get('rooms', [])]
            app_data['faculty'] = [Faculty.from_dict(d) for d in data.get('faculty', [])]
            app_data['sections'] = [Section.from_dict(d) for d in data.get('sections', [])]
            app_data['batches'] = [Batch.from_dict(d) for d in data.get('batches', [])]
            app_data['courses'] = [Course.from_dict(d) for d in data.get('courses', [])]
        except Exception as e:
            print(f"Error loading database: {e}")
