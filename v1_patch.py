"""
v1_patch.py - applies all v1 changes to app.py, app.js, and index.html
Run once from the project root: python v1_patch.py
"""

import re, os

BASE = os.path.dirname(os.path.abspath(__file__))

def rw(path, fn):
    with open(path, 'r', encoding='utf-8') as f:
        txt = f.read()
    new = fn(txt)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new)
    changed = txt != new
    print(f"{'CHANGED' if changed else 'NO-CHANGE'}: {os.path.basename(path)}")
    return changed

# ============================================================
# 1. app.py – remove Excel import route, add /api/summary
# ============================================================
def patch_app(txt):
    # --- Remove Excel import route (from the section header through the last line) ---
    txt = re.sub(
        r'# -+\r?\n# Excel Import API\r?\n# -+\r?\n@app\.route.*?return jsonify\(\{\s*\'status\': \'ok\',\s*\'message\':.*?\}\)\s*',
        (
            "# ---------------------------------------------------------------------------\n"
            "# Excel Import API — REMOVED in v1 (demo data only)\n"
            "# ---------------------------------------------------------------------------\n"
            "# Deferred to a future version. Use /api/load-demo or manual entry.\n\n"
        ),
        txt,
        flags=re.DOTALL
    )

    # --- Add /api/summary route just before /api/load-demo ---
    summary_route = '''
# ---------------------------------------------------------------------------
# Pre-Generate Summary API  (v1 addition)
# ---------------------------------------------------------------------------
@app.route('/api/summary', methods=['GET'])
def get_summary():
    """Return a summary of the current dataset before timetable generation."""
    cfg   = app_data['config']
    courses  = app_data['courses']
    sections = app_data['sections']
    batches  = app_data['batches']
    faculty  = app_data['faculty']
    rooms    = app_data['rooms']

    theory_sessions = 0
    lab_sessions    = 0
    total_weekly_hours = 0

    for c in courses:
        theory_sessions += int(c.l) + int(c.t)
        lb = len(c.lab_batches) if c.lab_batches else 0
        if lb > 0 and c.p > 0:
            lab_sessions += lb
        total_weekly_hours += c.l + c.t + c.p

    slots_per_week = 0
    if cfg:
        from time_slots import generate_time_slots
        slots = generate_time_slots(cfg)
        slots_per_week = len(slots) * len(cfg.working_days)

    return jsonify({
        'sections':                 len(sections),
        'batches':                  len(batches),
        'faculty':                  len(faculty),
        'rooms':                    len(rooms),
        'lab_rooms':                len([r for r in rooms if r.room_type == 'LAB']),
        'theory_rooms':             len([r for r in rooms if r.room_type == 'THEORY_ROOM']),
        'courses':                  len(courses),
        'theory_sessions_per_week': theory_sessions,
        'lab_sessions_per_week':    lab_sessions,
        'total_weekly_session_hours': round(total_weekly_hours, 1),
        'available_slots_per_week': slots_per_week,
        'working_days':             cfg.working_days if cfg else [],
        'config_set':               cfg is not None,
    })

'''
    txt = txt.replace(
        "@app.route('/api/load-demo', methods=['POST'])",
        summary_route + "@app.route('/api/load-demo', methods=['POST'])"
    )
    return txt

rw(os.path.join(BASE, 'app.py'), patch_app)


# ============================================================
# 2. app.js – remove Excel import JS event-listeners
# ============================================================
def patch_js(txt):
    # Remove the two Excel import listener blocks (preview + import)
    txt = re.sub(
        r"document\.getElementById\('btn-preview-import'\)\?\.addEventListener.*?document\.getElementById\('btn-import-excel'\)\?\.addEventListener.*?\}\);\s*",
        "// Excel import listeners removed in v1\n\n",
        txt,
        flags=re.DOTALL
    )
    return txt

rw(os.path.join(BASE, 'static', 'app.js'), patch_js)


# ============================================================
# 3. index.html – remove Excel import UI card, add summary modal
# ============================================================
def patch_html(txt):

    # --- Remove any Excel import card if it exists ---
    txt = re.sub(
        r'<!--\s*Excel Import.*?-->\s*<div[^>]*>.*?</div>\s*',
        '',
        txt,
        flags=re.DOTALL
    )

    # --- Replace the generate controls card to add summary first ---
    old_controls = '<div class="generate-controls card">'
    new_before = '''
        <!-- Pre-Generate Summary Panel (v1) -->
        <div class="card" id="pre-gen-summary" style="display:none; margin-bottom:16px;">
            <h3 style="margin-bottom:12px;">📊 Schedule Summary</h3>
            <div id="summary-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:16px;"></div>
            <div id="summary-warnings" style="margin-bottom:12px;"></div>
            <div style="display:flex;gap:12px;flex-wrap:wrap;">
                <button id="btn-confirm-generate" class="btn-generate" style="flex:1;min-width:200px;">
                    <span class="btn-generate-icon">⚡</span> Confirm &amp; Generate
                </button>
                <button id="btn-cancel-generate" class="btn secondary" style="flex:0;">Cancel</button>
            </div>
        </div>

        '''
    txt = txt.replace(old_controls, new_before + old_controls)

    # --- Inject JS to wire up the summary flow right before </body> ---
    summary_script = '''
    <script>
    // ── v1: Pre-Generate Summary ──────────────────────────────────────────────
    (function () {
        const btnGen    = document.getElementById('btn-generate');
        const btnConf   = document.getElementById('btn-confirm-generate');
        const btnCancel = document.getElementById('btn-cancel-generate');
        const panel     = document.getElementById('pre-gen-summary');
        const grid      = document.getElementById('summary-grid');
        const warnings  = document.getElementById('summary-warnings');
        const controls  = document.querySelector('.generate-controls.card');

        function statCard(label, value, color) {
            return `<div style="background:#f9f9fb;border:1px solid #e3e6f0;border-radius:10px;padding:14px 16px;text-align:center;">
                        <div style="font-size:28px;font-weight:700;color:${color || '#3b5bdb'};">${value}</div>
                        <div style="font-size:12px;color:#666;margin-top:4px;">${label}</div>
                    </div>`;
        }

        btnGen && btnGen.addEventListener('click', async (e) => {
            e.stopImmediatePropagation();
            try {
                const res  = await fetch('/api/summary');
                const data = await res.json();

                if (!data.config_set) {
                    alert('Please save a configuration first (Config tab).');
                    return;
                }
                if (data.courses === 0) {
                    alert('No courses defined. Please add courses before generating.');
                    return;
                }

                grid.innerHTML = [
                    statCard('Sections', data.sections, '#1c7ed6'),
                    statCard('Batches', data.batches, '#1c7ed6'),
                    statCard('Faculty', data.faculty, '#1c7ed6'),
                    statCard('Theory Rooms', data.theory_rooms, '#2f9e44'),
                    statCard('Lab Rooms', data.lab_rooms, '#2f9e44'),
                    statCard('Courses', data.courses, '#7048e8'),
                    statCard('Theory Sessions / week', data.theory_sessions_per_week, '#e67700'),
                    statCard('Lab Sessions / week', data.lab_sessions_per_week, '#e67700'),
                    statCard('Total Hours / week', data.total_weekly_session_hours, '#c92a2a'),
                    statCard('Available Slots / week', data.available_slots_per_week, '#495057'),
                ].join('');

                // Warnings
                let w = '';
                if (data.total_weekly_session_hours > data.available_slots_per_week * 0.9)
                    w += '<p style="color:#c92a2a;font-weight:600;">⚠️ Session hours are very close to (or exceed) available slots — scheduling may fail.</p>';
                if (data.lab_rooms === 0 && data.lab_sessions_per_week > 0)
                    w += '<p style="color:#e67700;font-weight:600;">⚠️ Lab sessions exist but no Lab rooms are defined.</p>';
                warnings.innerHTML = w;

                panel.style.display   = 'block';
                controls.style.display = 'none';
            } catch (err) {
                alert('Could not load summary: ' + err.message);
            }
        }, true /* capture so it fires before the existing listener */);

        btnCancel && btnCancel.addEventListener('click', () => {
            panel.style.display    = 'none';
            controls.style.display = '';
        });

        btnConf && btnConf.addEventListener('click', () => {
            panel.style.display    = 'none';
            controls.style.display = '';
            // Trigger the original generate button's default listener
            document.getElementById('btn-generate').dispatchEvent(new MouseEvent('click', { bubbles: true }));
        });
    })();
    </script>
'''
    txt = txt.replace('</body>', summary_script + '\n</body>')
    return txt

rw(os.path.join(BASE, 'templates', 'index.html'), patch_html)

print("\nAll patches applied. Now on branch v1.")
