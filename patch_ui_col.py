import re

# 1. Update index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()
html = html.replace('<th>Faculty</th><th>Room Type</th>', '<th>Faculty</th><th>Asst Faculty</th><th>Room Type</th>')
with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

# 2. Update app.js (renderCourses function)
with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

render_courses_match = r"(const tr = document\.createElement\('tr'\);\s*tr\.innerHTML = `\s*<td>\$\{c\.id\}</td>\s*<td>\$\{c\.code\}</td>\s*<td>\$\{c\.name\}</td>\s*<td>\$\{c\.section_id\}</td>\s*<td>\$\{c\.l\}-\$\{c\.t\}-\$\{c\.p\}</td>\s*<td>\$\{c\.lab_batches\.join\(', '\)\}</td>\s*<td>\$\{c\.faculty_ids\.join\(', '\)\}</td>\s*)(<td>\$\{c\.room_type\}</td>)"

def repl(m):
    return m.group(1) + "<td>${c.assistant_faculty_ids ? c.assistant_faculty_ids.join(', ') : ''}</td>\n                " + m.group(2)

js = re.sub(render_courses_match, repl, js)

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(js)

print("UI Patched for Assistant Faculty column.")
