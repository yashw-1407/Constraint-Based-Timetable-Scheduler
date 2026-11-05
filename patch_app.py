import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Global trace config
trace_globals = """
# Trace config
trace_config = {
    'level': 0,
    'session_filter': None
}
"""
if 'trace_config = {' not in code:
    code = code.replace('app_data = {', trace_globals + '\napp_data = {')

# 2. Add API endpoints
trace_endpoints = """
@app.route('/api/debug/trace/config', methods=['GET', 'POST'])
def manage_trace_config():
    if request.method == 'GET':
        return jsonify(trace_config)
    else:
        data = request.get_json() or {}
        trace_config['level'] = int(data.get('level', 0))
        filter_str = data.get('session_filter', '').strip()
        if filter_str:
            trace_config['session_filter'] = [x.strip() for x in filter_str.split(',') if x.strip()]
        else:
            trace_config['session_filter'] = None
        return jsonify(trace_config)

@app.route('/api/debug/trace/download/<fmt>', methods=['GET'])
def download_trace(fmt):
    import os
    from flask import send_file
    if fmt == 'txt':
        path = 'scheduler_trace.txt'
    elif fmt == 'json':
        path = 'scheduler_trace.json'
    else:
        return jsonify({'error': 'invalid format'}), 400
        
    if not os.path.exists(path):
        return jsonify({'error': 'No trace file found'}), 404
    return send_file(path, as_attachment=True)

"""
if '/api/debug/trace/config' not in code:
    code = code.replace('@app.route(\'/api/validation\', methods=[\'GET\'])', trace_endpoints + '\n@app.route(\'/api/validation\', methods=[\'GET\'])')

# 3. Patch engine creation
from_import = "from scheduler_trace import SchedulerTrace\nfrom scheduler import"
if 'from scheduler_trace import SchedulerTrace' not in code:
    code = code.replace('from scheduler import', from_import)

# patch /api/generate
gen1 = """        from scheduler_trace import SchedulerTrace
        trace = SchedulerTrace(level=trace_config['level'], session_filter=trace_config['session_filter'])
        
        engine = SchedulingEngine(
            config=app_data['config'],
            courses=app_data['courses'],
            rooms=app_data['rooms'],
            faculty_list=app_data['faculty'],
            sections=app_data['sections'],
            batches=app_data['batches'],
            trace=trace
        )"""
code = re.sub(r'        engine = SchedulingEngine\(.*?batches=app_data\[\'batches\'\],\n        \)', gen1, code, flags=re.DOTALL)

# write trace
w1 = """        result = engine.solve()
        if hasattr(engine, 'trace') and engine.trace.enabled:
            engine.trace.write()
        app_data['engine'] = engine"""
code = code.replace("        result = engine.solve()\n        app_data['engine'] = engine", w1)

# patch /api/generate-multiple
gen2 = """        from scheduler_trace import SchedulerTrace
        trace = SchedulerTrace(level=trace_config['level'], session_filter=trace_config['session_filter'])
        
        engine = SchedulingEngine(
            config=app_data['config'],
            courses=app_data['courses'],
            rooms=app_data['rooms'],
            faculty_list=app_data['faculty'],
            sections=app_data['sections'],
            batches=app_data['batches'],
            trace=trace
        )"""
code = re.sub(r'        engine = SchedulingEngine\(.*?batches=app_data\[\'batches\'\],\n        \)', gen2, code, flags=re.DOTALL)

w2 = """        result = engine.solve_multiple(requested_count=count, base_seed=seed, max_attempts=max_attempts, min_diversity_pct=min_div)
        if hasattr(engine, 'trace') and engine.trace.enabled:
            engine.trace.write()
"""
code = code.replace("        result = engine.solve_multiple(requested_count=count, base_seed=seed, max_attempts=max_attempts, min_diversity_pct=min_div)\n", w2)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)
