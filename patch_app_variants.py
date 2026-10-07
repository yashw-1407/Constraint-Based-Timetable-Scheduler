import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

new_route = """
@app.route('/api/timetable/variant/<int:index>', methods=['POST'])
def select_variant(index):
    engine = app_data.get('engine')
    result = app_data.get('result')
    if not engine or not result or result.get('status') != 'success':
        return jsonify({'error': 'No generated timetable found'}), 400
        
    variants = result.get('variants', [])
    if index < 0 or index >= len(variants):
        return jsonify({'error': 'Invalid variant index'}), 400
        
    engine.load_assignments_data(variants[index]['assignments_data'])
    result['active_variant_index'] = index
    return jsonify({'status': 'ok'})

# ---------------------------------------------------------------------------
# Validation API
"""
code = code.replace("# ---------------------------------------------------------------------------\n# Validation API", new_route)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Backend variant route added!")
