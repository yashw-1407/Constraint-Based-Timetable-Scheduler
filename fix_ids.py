import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Fix the duplicate IDs for the multiple generation section
html = html.replace('id="gen-status"', 'id="gen-status-alt"')
html = html.replace("""<div id="gen-status-alt" style="margin-top: 20px; display: none;">
                <h3 id="gen-status-text"></h3>
                <div id="gen-score" style="background: #e8f5e9; padding: 15px; border-radius: 5px; margin-top: 10px; display: none;"></div>
                <div id="gen-diagnostics" style="background: #ffebee; padding: 15px; border-radius: 5px; margin-top: 10px; display: none;"></div>
            </div>""", """<div id="gen-status-alt" style="margin-top: 20px; display: none;">
                <h3 id="gen-status-text-alt"></h3>
                <div id="gen-score-alt" style="background: #e8f5e9; padding: 15px; border-radius: 5px; margin-top: 10px; display: none;"></div>
                <div id="gen-diagnostics-alt" style="background: #ffebee; padding: 15px; border-radius: 5px; margin-top: 10px; display: none;"></div>
            </div>""")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

old_js = """document.getElementById('btn-generate-multiple')?.addEventListener('click', async () => {
    const statusDiv = document.getElementById('gen-status');
    const statusText = document.getElementById('gen-status-text');
    const scoreDiv = document.getElementById('gen-score');
    const diagDiv = document.getElementById('gen-diagnostics');"""
    
new_js = """document.getElementById('btn-generate-multiple')?.addEventListener('click', async () => {
    const statusDiv = document.getElementById('gen-status-alt');
    const statusText = document.getElementById('gen-status-text-alt');
    const scoreDiv = document.getElementById('gen-score-alt');
    const diagDiv = document.getElementById('gen-diagnostics-alt');"""
    
js = js.replace(old_js, new_js)

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(js)
print("IDs fixed!")
