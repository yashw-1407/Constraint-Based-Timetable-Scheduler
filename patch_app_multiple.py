import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

new_route = """
@app.route('/api/generate-multiple', methods=['POST'])
def generate_multiple():
    if not app_data['config']:
        return jsonify({'error': 'Configuration not set'}), 400
    if not app_data['rooms']:
        return jsonify({'error': 'No rooms defined'}), 400
    if not app_data['courses']:
        return jsonify({'error': 'No courses defined'}), 400

    try:
        data = request.get_json() or {}
        count = int(data.get('count', 5))
        seed = int(data.get('seed', 1000))
        max_attempts = int(data.get('max_attempts', 30))
        
        engine = SchedulingEngine(
            config=app_data['config'],
            courses=app_data['courses'],
            rooms=app_data['rooms'],
            faculty_list=app_data['faculty'],
            sections=app_data['sections'],
            batches=app_data['batches'],
        )
        result = engine.solve_multiple(requested_count=count, base_seed=seed, max_attempts=max_attempts)
        
        # Save state
        app_data['engine'] = engine
        app_data['result'] = result
        
        # Convert variants -> alternatives mapping to maintain compatibility with existing variant code
        if 'alternatives' in result:
            result['variants'] = result['alternatives']
            
        save_data(app_data)
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ---------------------------------------------------------------------------
"""

code = code.replace("# ---------------------------------------------------------------------------\n# Validation API", new_route + "# Validation API")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("app.py patched!")
