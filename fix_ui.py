import re

# 1. Fix app.js
with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

bad_if_else = """    if (tabId === 'config') loadConfig();
    loadTraceConfig();
    else if (tabId === 'rooms') loadRooms();"""

good_if_else = """    if (tabId === 'config') {
        loadConfig();
    } else if (tabId === 'trace') {
        loadTraceConfig();
    } else if (tabId === 'rooms') loadRooms();"""

if bad_if_else in js:
    js = js.replace(bad_if_else, good_if_else)
else:
    # Let's use regex in case whitespace is slightly different
    js = re.sub(
        r"    if \(tabId === 'config'\) loadConfig\(\);\s*loadTraceConfig\(\);\s*else if \(tabId === 'rooms'\) loadRooms\(\);",
        "    if (tabId === 'config') loadConfig();\n    else if (tabId === 'trace') loadTraceConfig();\n    else if (tabId === 'rooms') loadRooms();",
        js
    )

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(js)

# 2. Fix index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

btn_target = '<button class="tab-btn" data-target="views">Timetable Views</button>'
trace_btn = '<button class="tab-btn" data-target="trace" style="background-color: #555; color: white;">Trace / Debug</button>'

if 'data-target="trace"' not in html:
    html = html.replace(btn_target, btn_target + '\n            ' + trace_btn)

# Change trace tab content ID to match target
if 'id="trace-tab"' in html:
    html = html.replace('id="trace-tab"', 'id="trace"')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
