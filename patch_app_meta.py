import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

new_route = """
@app.route('/api/timetable/metadata', methods=['GET'])
def get_metadata():
    result = app_data.get('result')
    if not result or result.get('status') != 'success':
        return jsonify({'error': 'No valid timetable'}), 400
    variants = result.get('variants', [])
    active_idx = result.get('active_variant_index', 0)
    score = variants[active_idx]['soft_score'] if variants else {}
    return jsonify({
        'num_variants': len(variants),
        'active_variant_index': active_idx,
        'active_score': score
    })

# ---------------------------------------------------------------------------
# Validation API
"""
code = code.replace("# ---------------------------------------------------------------------------\n# Validation API", new_route)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Backend metadata route added!")
