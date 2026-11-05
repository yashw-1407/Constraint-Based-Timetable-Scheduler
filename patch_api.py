import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

def inject_put_route(entity, attr_name, constructor_code):
    old_route = f"@app.route('/api/{entity}/<id>', methods=['DELETE'])\ndef delete_{entity}(id):\n    app_data['{attr_name}'] = [x for x in app_data['{attr_name}'] if x.id != id]\n    save_data(app_data)\n    return jsonify({{'status': 'ok'}})\n"
    
    # Try finding it with r or f or s or b or c variable name in the list comprehension
    import ast
    # Instead of fragile string matching, I'll use regex to match the delete block
    pattern = r"@app.route\('/api/" + entity + r"/<id>', methods=\['DELETE'\]\)\ndef delete_" + entity + r"\(id\):\n    app_data\['" + attr_name + r"'\] = \[.*?\]\n    save_data\(app_data\)\n    return jsonify\(\{'status': 'ok'\}\)"
    
    new_route = f"""@app.route('/api/{entity}/<id>', methods=['DELETE', 'PUT'])
def manage_{entity}_id(id):
    if request.method == 'DELETE':
        app_data['{attr_name}'] = [x for x in app_data['{attr_name}'] if x.id != id]
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
    
    return re.sub(pattern, new_route, code)

# 1. Rooms
room_constructor = """Room(
                id=data['id'],
                name=data['name'],
                room_type=data['room_type'],
                capacity=int(data['capacity']) if data.get('capacity') else None,
                category=data.get('category') or None,
            )"""
code = inject_put_route('rooms', 'rooms', room_constructor)

# 2. Faculty
fac_constructor = """Faculty(
                id=data['id'],
                name=data['name'],
            )"""
code = inject_put_route('faculty', 'faculty', fac_constructor)

# 3. Sections
sec_constructor = """Section(
                id=data['id'],
                name=data['name'],
                semester=int(data['semester']),
                division=data['division'],
                strength=int(data['strength']) if data.get('strength') else None,
            )"""
code = inject_put_route('sections', 'sections', sec_constructor)

# 4. Batches
batch_constructor = """Batch(
                id=data['id'],
                name=data['name'],
                section_id=data['section_id'],
                strength=int(data['strength']) if data.get('strength') else None,
            )"""
code = inject_put_route('batches', 'batches', batch_constructor)

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
code = inject_put_route('courses', 'courses', course_constructor)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Backend patched for PUT!")
