import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Add tab
if 'data-tab="trace-tab"' not in html:
    html = html.replace(
        '<button class="tab-btn" data-tab="views-tab">Timetable Views</button>',
        '<button class="tab-btn" data-tab="views-tab">Timetable Views</button>\n            <button class="tab-btn" data-tab="trace-tab" style="background-color: #555; color: white;">Trace / Debug</button>'
    )

# Add tab content
trace_tab = """
        <!-- Trace Tab -->
        <div id="trace-tab" class="tab-content">
            <h2>Scheduler Trace & Debug</h2>
            <div class="card">
                <h3>Trace Configuration</h3>
                <p>Use tracing to diagnose constraint failures and see the internal decisions made by the CSP solver.</p>
                <form id="trace-form">
                    <div class="form-group">
                        <label>Trace Level</label>
                        <select id="trace-level">
                            <option value="0">0 - Disabled</option>
                            <option value="1">1 - Summary Only</option>
                            <option value="2">2 - Decisions & Constraints</option>
                            <option value="3">3 - Full Candidate Trace (Slow)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Session Filter (Optional)</label>
                        <input type="text" id="trace-filter" placeholder="e.g. C3A06_L0, Algorithms Lab, S3A">
                        <small>Comma-separated list of session IDs, course names, or section IDs to limit trace output.</small>
                    </div>
                    <button type="button" class="btn-primary" onclick="saveTraceConfig()">Save Trace Config</button>
                </form>
            </div>

            <div class="card" style="margin-top: 20px;">
                <h3>Trace Output</h3>
                <p>Run a timetable generation from the "Generate" tab, then download the trace files here.</p>
                <div style="display: flex; gap: 10px;">
                    <button class="btn-success" onclick="window.open('/api/debug/trace/download/txt', '_blank')">Download TXT Trace</button>
                    <button class="btn-success" onclick="window.open('/api/debug/trace/download/json', '_blank')">Download JSON Trace</button>
                </div>
            </div>
        </div>
"""
if 'id="trace-tab"' not in html:
    html = html.replace('    </main>', trace_tab + '\n    </main>')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
