import re

# 1. Remove from HTML
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# I can just remove the div with id="variant-navigator" and everything inside it
html = re.sub(r'<div id="variant-navigator".*?</div>\s*</div>', '', html, flags=re.DOTALL)
# The above regex might be fragile if there are nested divs. Let's just find it exactly or use a simpler regex.
start_idx = html.find('<div id="variant-navigator"')
if start_idx != -1:
    end_idx = html.find('</div>\n            </div>', start_idx) + 12 # match inner and outer divs
    # wait, the html was:
    '''            <div id="variant-navigator" style="display: none; background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; align-items: center; justify-content: space-between;">
                <div>
                    <h3 style="margin: 0; color: #0d47a1;">Timetable Alternative <span id="var-current">1</span> of <span id="var-total">3</span></h3>
                    <div style="font-size: 13px; color: #1565c0; margin-top: 5px;">Quality Score: <strong id="var-score">0</strong></div>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button id="btn-var-prev" class="btn primary">◀ Previous Option</button>
                    <button id="btn-var-next" class="btn primary">Next Option ▶</button>
                </div>
            </div>'''
    
    html = html.replace('''            <div id="variant-navigator" style="display: none; background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; align-items: center; justify-content: space-between;">
                <div>
                    <h3 style="margin: 0; color: #0d47a1;">Timetable Alternative <span id="var-current">1</span> of <span id="var-total">3</span></h3>
                    <div style="font-size: 13px; color: #1565c0; margin-top: 5px;">Quality Score: <strong id="var-score">0</strong></div>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button id="btn-var-prev" class="btn primary">◀ Previous Option</button>
                    <button id="btn-var-next" class="btn primary">Next Option ▶</button>
                </div>
            </div>
''', '')
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("HTML reversed!")

# 2. Remove from app.js
with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Replace the specific initialization that included loadVariantMetadata()
js = js.replace("""function loadTimetableViewsInit() {
    loadVariantMetadata();
    const activeBtn = document.querySelector('.view-btn.active');
    if (!activeBtn) {
        const masterBtn = document.querySelector('.view-btn[data-view="master"]');
        if (masterBtn) masterBtn.click();
    }
}""", """function loadTimetableViewsInit() {
    const activeBtn = document.querySelector('.view-btn.active');
    if (!activeBtn) {
        const masterBtn = document.querySelector('.view-btn[data-view="master"]');
        if (masterBtn) masterBtn.click();
    }
}""")

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(js)
print("app.js reversed!")
