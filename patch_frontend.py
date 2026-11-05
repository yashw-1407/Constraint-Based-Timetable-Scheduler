import os

# --- PATCH index.html ---
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

old_form = '''        <!-- Courses Tab -->
        <section id="courses" class="tab-content">
            <h2>Courses</h2>
            <form id="form-course" class="add-form complex-form">
                <input type="text" id="course_id" placeholder="Course ID" required>
                <input type="text" id="course_name" placeholder="Name" required>
                <input type="text" id="course_code" placeholder="Code" required>
                <select id="course_section" required><option value="">Select Section</option></select>
                <select id="course_type" required>
                    <option value="THEORY">Theory</option>
                    <option value="LAB">Lab</option>
                </select>
                <input type="number" id="course_weekly_hours" placeholder="Weekly Hours" required>
                <input type="number" id="course_lab_duration" placeholder="Lab Duration (Hours)" style="display: none;">
                <select id="course_batch" style="display: none;"><option value="">Batch (Section-level)</option></select>
                <select id="course_faculty" required><option value="">Select Faculty</option></select>
                <select id="course_room_type" required>
                    <option value="THEORY_ROOM">Theory Room</option>
                    <option value="LAB">Lab</option>
                </select>
                <select id="course_required_room"><option value="">Required Room (Opt)</option></select>
                <button type="submit" class="btn primary">Add Course</button>
            </form>
            <table id="table-courses">
                <thead><tr><th>ID</th><th>Code</th><th>Name</th><th>Section</th><th>Batch</th><th>Type</th><th>Hours</th><th>Faculty</th><th>Room Type</th><th>Actions</th></tr></thead>'''

new_form = '''        <!-- Courses Tab -->
        <section id="courses" class="tab-content">
            <h2>Courses</h2>
            <form id="form-course" class="add-form complex-form">
                <input type="text" id="course_id" placeholder="Course ID (e.g. CS301_3A)" required>
                <input type="text" id="course_name" placeholder="Name" required>
                <input type="text" id="course_code" placeholder="Code" required>
                <select id="course_section" required><option value="">Select Section</option></select>
                
                <div class="ltp-inputs" style="display: flex; gap: 10px;">
                    <input type="number" id="course_l" placeholder="L (Lecture)" value="0" min="0" required style="width: 30%;">
                    <input type="number" id="course_t" placeholder="T (Tutorial)" value="0" min="0" required style="width: 30%;">
                    <input type="number" id="course_p" placeholder="P (Practical)" value="0" min="0" required style="width: 30%;">
                </div>
                
                <select id="course_faculty" multiple required title="Hold Ctrl/Cmd to select multiple" style="height: 80px;">
                </select>
                
                <select id="course_room_type" required>
                    <option value="THEORY_ROOM">Theory Room</option>
                    <option value="LAB">Lab</option>
                </select>
                <select id="course_required_room"><option value="">Required Room (Opt)</option></select>
                
                <select id="course_lab_batches" multiple style="display: none; height: 80px;" title="Hold Ctrl/Cmd to select multiple">
                </select>
                
                <button type="submit" class="btn primary">Add Course</button>
            </form>
            <table id="table-courses">
                <thead><tr><th>ID</th><th>Code</th><th>Name</th><th>Section</th><th>L-T-P</th><th>Batches</th><th>Faculty</th><th>Room Type</th><th>Actions</th></tr></thead>'''

if old_form in html:
    html = html.replace(old_form, new_form)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("index.html patched")
else:
    print("index.html: old form not found")


# --- PATCH app.js ---
with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Update loadCourses columns
js = js.replace(
    "['id', 'code', 'name', 'section_id',\n         (item) => item.batch_id || 'ALL',\n         'course_type', 'weekly_hours', 'faculty_id', 'room_type']",
    "['id', 'code', 'name', 'section_id',\n         (item) => `${item.l}-${item.t}-${item.p}`,\n         (item) => item.lab_batches.length ? item.lab_batches.join(', ') : 'ALL',\n         (item) => item.faculty_ids.join(', '), 'room_type']"
)

# 2. Update batch dropdown logic
old_batch = """// Update batch dropdown when section changes (for LAB courses)
function updateBatchDropdown() {
    const secId = document.getElementById('course_section').value;
    const batchSelect = document.getElementById('course_batch');
    batchSelect.innerHTML = '<option value="">Batch (Section-level)</option>';

    if (secId && window._sectionsData) {
        const sec = window._sectionsData.find(s => s.id === secId);
        if (sec && sec.batches && sec.batches.length > 0) {
            sec.batches.forEach(b => {
                batchSelect.innerHTML += `<option value="${b.id}">${sec.name} - ${b.name} (${b.strength || '?'})</option>`;
            });
        }
    }
}

document.getElementById('course_section').addEventListener('change', updateBatchDropdown);

document.getElementById('course_type').addEventListener('change', (e) => {
    const labDur = document.getElementById('course_lab_duration');
    const batchSelect = document.getElementById('course_batch');
    if (e.target.value === 'LAB') {
        labDur.style.display = 'block';
        labDur.required = true;
        batchSelect.style.display = 'block';
        updateBatchDropdown();
    } else {
        labDur.style.display = 'none';
        labDur.required = false;
        labDur.value = '';
        batchSelect.style.display = 'none';
        batchSelect.value = '';
    }
});"""

new_batch = """// Update batch dropdown when section changes
function updateBatchDropdown() {
    const secId = document.getElementById('course_section').value;
    const batchSelect = document.getElementById('course_lab_batches');
    batchSelect.innerHTML = '';

    if (secId && window._sectionsData) {
        const sec = window._sectionsData.find(s => s.id === secId);
        if (sec && sec.batches && sec.batches.length > 0) {
            sec.batches.forEach(b => {
                batchSelect.innerHTML += `<option value="${b.id}">${sec.name} - ${b.name}</option>`;
            });
        }
    }
}

document.getElementById('course_section').addEventListener('change', updateBatchDropdown);

document.getElementById('course_p').addEventListener('input', (e) => {
    const p = parseInt(e.target.value) || 0;
    const batchSelect = document.getElementById('course_lab_batches');
    if (p > 0) {
        batchSelect.style.display = 'block';
        updateBatchDropdown();
    } else {
        batchSelect.style.display = 'none';
        Array.from(batchSelect.options).forEach(o => o.selected = false);
    }
});"""

js = js.replace(old_batch, new_batch)

# 3. Update form submit payload
old_submit = """    const isLab = document.getElementById('course_type').value === 'LAB';
    const payload = {
        id: document.getElementById('course_id').value,
        name: document.getElementById('course_name').value,
        code: document.getElementById('course_code').value,
        section_id: document.getElementById('course_section').value,
        course_type: document.getElementById('course_type').value,
        weekly_hours: parseInt(document.getElementById('course_weekly_hours').value),
        faculty_id: document.getElementById('course_faculty').value,
        room_type: document.getElementById('course_room_type').value,
        lab_duration_hours: isLab ? parseInt(document.getElementById('course_lab_duration').value) : null,
        required_room_id: document.getElementById('course_required_room').value || null,
        batch_id: isLab ? (document.getElementById('course_batch').value || null) : null,
    };
    try {
        await fetchJSON('/api/courses', { method: 'POST', body: JSON.stringify(payload) });
        showNotification('Course added');
        clearForm('form-course');
        
        const labDur = document.getElementById('course_lab_duration');
        labDur.style.display = 'none';
        labDur.required = false;
        labDur.value = '';

        const batchSelect = document.getElementById('course_batch');
        batchSelect.style.display = 'none';
        batchSelect.value = '';

        loadCourses();"""

new_submit = """    const facSelect = document.getElementById('course_faculty');
    const facultyIds = Array.from(facSelect.selectedOptions).map(opt => opt.value);
    
    const batchSelect = document.getElementById('course_lab_batches');
    const labBatches = Array.from(batchSelect.selectedOptions).map(opt => opt.value);

    const payload = {
        id: document.getElementById('course_id').value,
        name: document.getElementById('course_name').value,
        code: document.getElementById('course_code').value,
        section_id: document.getElementById('course_section').value,
        l: parseInt(document.getElementById('course_l').value) || 0,
        t: parseInt(document.getElementById('course_t').value) || 0,
        p: parseInt(document.getElementById('course_p').value) || 0,
        faculty_ids: facultyIds,
        room_type: document.getElementById('course_room_type').value,
        required_room_id: document.getElementById('course_required_room').value || null,
        lab_batches: labBatches,
    };
    try {
        await fetchJSON('/api/courses', { method: 'POST', body: JSON.stringify(payload) });
        showNotification('Course added');
        clearForm('form-course');
        
        document.getElementById('course_l').value = '0';
        document.getElementById('course_t').value = '0';
        document.getElementById('course_p').value = '0';
        
        const bSel = document.getElementById('course_lab_batches');
        bSel.style.display = 'none';
        Array.from(bSel.options).forEach(o => o.selected = false);

        loadCourses();"""

js = js.replace(old_submit, new_submit)

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(js)
print("app.js patched")
