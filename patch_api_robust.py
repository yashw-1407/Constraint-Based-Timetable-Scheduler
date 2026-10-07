import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read().replace('\r\n', '\n')

def patch(entity, attr, code_body, var):
    global code
    
    start_str = f"@app.route('/api/{entity}/<id>', methods=['DELETE'])"
    
    # Check if we already patched it (e.g. methods=['DELETE', 'PUT'])
    if f"@app.route('/api/{entity}/<id>', methods=['DELETE', 'PUT'])" in code:
        return
        
    start_idx = code.find(start_str)
    if start_idx == -1:
        print(f"Could not find start for {entity}")
        return
        
    end_str = "return jsonify({'status': 'ok'})"
    end_idx = code.find(end_str, start_idx)
    if end_idx == -1:
        print(f"Could not find end for {entity}")
        return
        
    end_idx += len(end_str)
    
    old_block = code[start_idx:end_idx]
    
    # We will keep the exact old delete logic for the DELETE branch
    delete_logic = old_block.replace(start_str + f"\ndef delete_{entity}(id):", "").strip()
    # Add indentation
    delete_logic = "        " + delete_logic.replace('\n    ', '\n        ')
    
    new_route = f"""@app.route('/api/{entity}/<id>', methods=['DELETE', 'PUT'])
def manage_{entity}_id(id):
    if request.method == 'DELETE':
{delete_logic}
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            new_obj = {code_body}
            for i, item in enumerate(app_data['{attr}']):
                if item.id == id:
                    app_data['{attr}'][i] = new_obj
                    break
            else:
                return jsonify({{'error': 'Not found'}}), 404
            save_data(app_data)
            return jsonify({{'status': 'ok'}})
        except Exception as e:
            return jsonify({{'error': str(e)}}), 400"""
            
    code = code[:start_idx] + new_route + code[end_idx:]

room_constructor = """Room(
                id=data['id'],
                name=data['name'],
                room_type=data['room_type'],
                capacity=int(data['capacity']) if data.get('capacity') else None,
                category=data.get('category') or None,
            )"""
patch('rooms', 'rooms', room_constructor, 'r')

sec_constructor = """Section(
                id=data['id'],
                name=data['name'],
                semester=int(data['semester']),
                division=data['division'],
                strength=int(data['strength']) if data.get('strength') else None,
            )"""
patch('sections', 'sections', sec_constructor, 's')

batch_constructor = """Batch(
                id=data['id'],
                name=data['name'],
                section_id=data['section_id'],
                strength=int(data['strength']) if data.get('strength') else None,
            )"""
patch('batches', 'batches', batch_constructor, 'b')

course_constructor = """Course(
                id=data['id'],
                name=data['name'],
                code=data['code'],
                section_id=data['section_id'],
                course_type=data['course_type'],
                l=float(data.get('l', 0)),
                t=float(data.get('t', 0)),
                p=float(data.get('p', 0)),
                faculty_ids=data.get('faculty_ids', []),
                room_type=data['room_type'],
                required_room_id=data.get('required_room_id') or None,
                lab_batches=data.get('lab_batches', []),
            )"""
patch('courses', 'courses', course_constructor, 'c')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Done patching missing routes!')
