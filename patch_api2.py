import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

def inject_put_route(entity, attr_name, constructor_code, var_name):
    old_route = f"@app.route('/api/{entity}/<id>', methods=['DELETE'])\ndef delete_{entity}(id):\n    app_data['{attr_name}'] = [{var_name} for {var_name} in app_data['{attr_name}'] if {var_name}.id != id]\n    save_data(app_data)\n    return jsonify({{'status': 'ok'}})"
    
    new_route = f"""@app.route('/api/{entity}/<id>', methods=['DELETE', 'PUT'])
def manage_{entity}_id(id):
    if request.method == 'DELETE':
        app_data['{attr_name}'] = [{var_name} for {var_name} in app_data['{attr_name}'] if {var_name}.id != id]
        save_data(app_data)
        return jsonify({{'status': 'ok'}})
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            new_obj = {constructor_code}
            for i, item in enumerate(app_data['{attr_name}']):
                if item.id == id:
                    app_data['{attr_name}'][i] = new_obj
                    break
            else:
                return jsonify({{'error': 'Not found'}}), 404
            save_data(app_data)
            return jsonify({{'status': 'ok'}})
        except Exception as e:
            return jsonify({{'error': str(e)}}), 400"""
    
    if old_route in code:
        return code.replace(old_route, new_route)
    else:
        print(f"Could not find exact route for {entity}")
        return code

# 1. Rooms
room_constructor = """Room(
                id=data['id'],
                name=data['name'],
                room_type=data['room_type'],
                capacity=int(data['capacity']) if data.get('capacity') else None,
                category=data.get('category') or None,
            )"""
code = inject_put_route('rooms', 'rooms', room_constructor, 'r')

# 3. Sections
sec_constructor = """Section(
                id=data['id'],
                name=data['name'],
                semester=int(data['semester']),
                division=data['division'],
                strength=int(data['strength']) if data.get('strength') else None,
            )"""
code = inject_put_route('sections', 'sections', sec_constructor, 's')

# 4. Batches
batch_constructor = """Batch(
                id=data['id'],
                name=data['name'],
                section_id=data['section_id'],
                strength=int(data['strength']) if data.get('strength') else None,
            )"""
code = inject_put_route('batches', 'batches', batch_constructor, 'b')

# 5. Courses
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
code = inject_put_route('courses', 'courses', course_constructor, 'c')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Backend patched for PUT!")
