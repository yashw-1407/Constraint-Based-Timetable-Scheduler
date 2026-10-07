import re

with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Update loadSections
old_load = """            res.forEach(s => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${s.id}</td>
                    <td>${s.name}</td>
                    <td>${s.semester}</td>
                    <td>${s.division}</td>
                    <td>${s.strength || '-'}</td>
                    <td><button class="btn danger" onclick="deleteSection('${s.id}')">Delete</button></td>
                `;
                tbody.appendChild(tr);
            });"""
            
new_load = """            res.forEach(s => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${s.id}</td>
                    <td>${s.name}</td>
                    <td>${s.semester}</td>
                    <td>${s.division}</td>
                    <td>${s.strength || '-'}</td>
                    <td>${s.home_room_id || '-'}</td>
                    <td><button class="btn danger" onclick="deleteSection('${s.id}')">Delete</button></td>
                `;
                tbody.appendChild(tr);
            });"""
js = js.replace(old_load, new_load)

# 2. Update section-form submit
old_submit = """        const data = {
            id: document.getElementById('section-id').value,
            name: document.getElementById('section-name').value,
            semester: document.getElementById('section-semester').value,
            division: document.getElementById('section-division').value,
            strength: document.getElementById('section-strength').value || null
        };"""
        
new_submit = """        const data = {
            id: document.getElementById('section-id').value,
            name: document.getElementById('section-name').value,
            semester: document.getElementById('section-semester').value,
            division: document.getElementById('section-division').value,
            strength: document.getElementById('section-strength').value || null,
            home_room_id: document.getElementById('section-homeroom').value || null
        };"""
js = js.replace(old_submit, new_submit)

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(js)
print("app.js patched")
