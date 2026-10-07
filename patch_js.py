import re

with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

trace_funcs = """
// ---------------------------------------------------------------------------
// Trace / Debug
// ---------------------------------------------------------------------------
async function loadTraceConfig() {
    try {
        const res = await fetchJSON('/api/debug/trace/config');
        if (res) {
            document.getElementById('trace-level').value = res.level;
            document.getElementById('trace-filter').value = res.session_filter ? res.session_filter.join(', ') : '';
        }
    } catch (err) {
        console.error('Failed to load trace config:', err);
    }
}

async function saveTraceConfig() {
    const level = parseInt(document.getElementById('trace-level').value, 10);
    const filter = document.getElementById('trace-filter').value;
    
    try {
        await fetchJSON('/api/debug/trace/config', {
            method: 'POST',
            body: JSON.stringify({ level: level, session_filter: filter })
        });
        showNotification('Trace configuration saved', 'success');
    } catch (err) {
        showNotification(err.message, 'error');
    }
}
"""

if 'saveTraceConfig()' not in js:
    js = js + '\n' + trace_funcs

# Hook loadTraceConfig into initialization
if 'loadTraceConfig();' not in js:
    js = js.replace('loadConfig();', 'loadConfig();\n    loadTraceConfig();')

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(js)
