import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update the Add Section form
old_form = """                        <div class="form-group">
                            <label>Strength:</label>
                            <input type="number" id="section-strength" placeholder="Optional">
                        </div>
                        <button type="submit" class="btn primary">Add Section</button>"""
                        
new_form = """                        <div class="form-group">
                            <label>Strength:</label>
                            <input type="number" id="section-strength" placeholder="Optional">
                        </div>
                        <div class="form-group">
                            <label>Home Room (Theory):</label>
                            <input type="text" id="section-homeroom" placeholder="Optional Room ID">
                        </div>
                        <button type="submit" class="btn primary">Add Section</button>"""
html = html.replace(old_form, new_form)

# 2. Update the Section table headers
old_table = """                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Semester</th>
                            <th>Division</th>
                            <th>Strength</th>
                            <th>Actions</th>
                        </tr>
                    </thead>"""
                    
new_table = """                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Semester</th>
                            <th>Division</th>
                            <th>Strength</th>
                            <th>Home Room</th>
                            <th>Actions</th>
                        </tr>
                    </thead>"""
html = html.replace(old_table, new_table)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("index.html patched")
