// ---------------------------------------------------------------------------
// Notifications & Fetch Helpers
// ---------------------------------------------------------------------------
function showNotification(message, type = 'success') {
    const notif = document.getElementById('notification');
    if (!notif) return;
    notif.textContent = message;
    notif.className = `notification ${type}`;
    setTimeout(() => {
        notif.classList.add('hidden');
    }, 3000);
}

async function fetchJSON(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.message || data.error || `HTTP error! status: ${response.status}`);
        }
        return data;
    } catch (error) {
        showNotification(error.message, 'error');
        throw error;
    }
}

function clearForm(formId) {
    const form = document.getElementById(formId);
    if (form) form.reset();
}

// ---------------------------------------------------------------------------
// Tab Switching
// ---------------------------------------------------------------------------
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        e.target.classList.add('active');
        const targetId = e.target.getAttribute('data-target');
        const section = document.getElementById(targetId);
        if (section) section.classList.add('active');

        loadTabData(targetId);
    });
});

function loadTabData(tabId) {
    if (tabId === 'config') loadConfig();
    else if (tabId === 'rooms') loadRooms();
    else if (tabId === 'faculty') loadFaculty();
    else if (tabId === 'sections') loadSections();
    else if (tabId === 'courses') loadCourses();
    else if (tabId === 'views') loadTimetableViewsInit();
}

// ---------------------------------------------------------------------------
// Configuration Tab
// ---------------------------------------------------------------------------
async function loadConfig() {
    try {
        const config = await fetchJSON('/api/config');
        if (config) {
            const daysCheckboxes = document.querySelectorAll('input[name="working_days"]');
            daysCheckboxes.forEach(cb => {
                cb.checked = config.working_days.includes(cb.value);
            });
            document.getElementById('start_time').value = config.start_time;
            document.getElementById('end_time').value = config.end_time;
            document.getElementById('slot_duration_minutes').value = config.slot_duration_minutes;
            document.getElementById('lunch_start').value = config.lunch_start;
            document.getElementById('lunch_end').value = config.lunch_end;

            const breaksContainer = document.getElementById('breaks-container');
            breaksContainer.innerHTML = '';
            if (config.breaks) {
                config.breaks.forEach(b => addBreakRow(b.start_time, b.end_time));
            }
            loadTimeSlots();
        }
    } catch (e) {
        console.error("Config load error:", e);
    }
}

function addBreakRow(start = '', end = '') {
    const container = document.getElementById('breaks-container');
    const row = document.createElement('div');
    row.className = 'break-row';
    row.innerHTML = `
        <input type="time" class="break-start" value="${start}" required>
        <span>to</span>
        <input type="time" class="break-end" value="${end}" required>
        <button type="button" class="btn danger remove-break">X</button>
    `;
    row.querySelector('.remove-break').addEventListener('click', () => row.remove());
    container.appendChild(row);
}

document.getElementById('btn-add-break')?.addEventListener('click', () => addBreakRow());

document.getElementById('form-config')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const working_days = Array.from(document.querySelectorAll('input[name="working_days"]:checked')).map(cb => cb.value);
    const breaks = Array.from(document.querySelectorAll('.break-row')).map(row => ({
        start_time: row.querySelector('.break-start').value,
        end_time: row.querySelector('.break-end').value
    }));

    const payload = {
        working_days,
        start_time: document.getElementById('start_time').value,
        end_time: document.getElementById('end_time').value,
        slot_duration_minutes: parseInt(document.getElementById('slot_duration_minutes').value),
        lunch_start: document.getElementById('lunch_start').value,
        lunch_end: document.getElementById('lunch_end').value,
        breaks
    };

    try {
        await fetchJSON('/api/config', { method: 'POST', body: JSON.stringify(payload) });
        showNotification('Configuration saved');
        loadTimeSlots();
    } catch (e) { }
});

async function loadTimeSlots() {
    try {
        const slots = await fetchJSON('/api/time-slots');
        const list = document.getElementById('time-slots-list');
        list.innerHTML = '';
        slots.forEach(slot => {
            const li = document.createElement('li');
            li.textContent = `Slot ${slot.index}: ${slot.start_time} - ${slot.end_time}`;
            list.appendChild(li);
        });
    } catch (e) { }
}

document.getElementById('btn-load-demo')?.addEventListener('click', async () => {
    try {
        const scenario = document.getElementById('demo-scenario-select')?.value || 'standard';
        const res = await fetchJSON('/api/load-demo', {
            method: 'POST',
            body: JSON.stringify({ scenario: scenario })
        });
        showNotification(res.message);
        loadConfig();
    } catch (e) { }
});

document.getElementById('btn-clear-data')?.addEventListener('click', async () => {
    if (!confirm('Are you sure you want to clear all data?')) return;
    try {
        await fetchJSON('/api/clear', { method: 'POST' });
        showNotification('Data cleared successfully');
        loadConfig();
    } catch (e) { }
});

// ---------------------------------------------------------------------------
// Table Data & CRUD Operations
// ---------------------------------------------------------------------------
let editingEndpoint = null;
let editingId = null;

async function loadTableData(endpoint, tableId, columns, rowIdKey = 'id') {
    try {
        const data = await fetchJSON(endpoint);
        const tbody = document.querySelector(`#${tableId} tbody`);
        tbody.innerHTML = '';
        data.forEach(item => {
            const tr = document.createElement('tr');
            columns.forEach(col => {
                const td = document.createElement('td');
                if (typeof col === 'function') {
                    td.innerHTML = col(item);
                } else {
                    td.textContent = item[col] !== null && item[col] !== undefined ? item[col] : '';
                }
                tr.appendChild(td);
            });
            const actionTd = document.createElement('td');
            const editBtn = document.createElement('button');
            editBtn.className = 'btn';
            editBtn.style.marginRight = '5px';
            editBtn.textContent = 'Edit';
            editBtn.onclick = () => editItem(endpoint, item);
            actionTd.appendChild(editBtn);

            const delBtn = document.createElement('button');
            delBtn.className = 'btn danger';
            delBtn.textContent = 'Delete';
            delBtn.onclick = () => deleteItem(endpoint, item[rowIdKey], () => loadTableData(endpoint, tableId, columns, rowIdKey));
            actionTd.appendChild(delBtn);
            tr.appendChild(actionTd);
            tbody.appendChild(tr);
        });
        return data;
    } catch (e) { }
}

async function deleteItem(endpoint, id, callback) {
    if (!confirm('Are you sure you want to delete this item?')) return;
    try {
        await fetchJSON(`${endpoint}/${id}`, { method: 'DELETE' });
        showNotification('Deleted successfully');
        callback();
    } catch (e) { }
}

function editItem(endpoint, item) {
    editingEndpoint = endpoint;
    editingId = item.id;

    let prefix = '';
    if (endpoint.includes('/rooms')) prefix = 'room_';
    else if (endpoint.includes('/faculty')) prefix = 'faculty_';
    else if (endpoint.includes('/sections')) prefix = 'section_';
    else if (endpoint.includes('/batches')) prefix = 'batch_';
    else if (endpoint.includes('/courses')) prefix = 'course_';

    for (const key in item) {
        const field = document.getElementById(prefix + key);
        if (field) {
            if (field.tagName === 'SELECT' && field.multiple && Array.isArray(item[key])) {
                if (key !== 'lab_batches') {
                    Array.from(field.options).forEach(opt => {
                        opt.selected = item[key].includes(opt.value);
                    });
                }
            } else {
                field.value = item[key] !== null ? item[key] : '';
            }
        }
    }

    if (prefix === 'course_') {
        if (item.faculty_ids && item.faculty_ids.length > 0) {
            document.getElementById('course_faculty').value = item.faculty_ids[0];
        } else {
            document.getElementById('course_faculty').value = '';
        }

        selectedAsstFaculty = [];
        if (Array.isArray(item.assistant_faculty_ids)) {
            item.assistant_faculty_ids.forEach(fid => {
                const fac = (window._facultyList || []).find(f => f.id === fid);
                selectedAsstFaculty.push({ id: fid, name: fac ? fac.name : fid });
            });
        }
        renderAsstFacultyTags();

        updateBatchDropdown();
        const batchSelect = document.getElementById('course_lab_batches');
        if (item.p > 0) {
            batchSelect.style.display = 'block';
            if (Array.isArray(item.lab_batches)) {
                Array.from(batchSelect.options).forEach(opt => {
                    opt.selected = item.lab_batches.includes(opt.value);
                });
            }
        } else {
            batchSelect.style.display = 'none';
        }
    }

    const formId = 'form-' + prefix.replace('_', '');
    const form = document.getElementById(formId);
    if (form) {
        const btn = form.querySelector('button[type="submit"]');
        if (btn) {
            btn.textContent = 'Update';
            btn.classList.add('warning');
        }
    }
}

function resetEditState(formId) {
    editingEndpoint = null;
    editingId = null;
    if (formId === 'form-course') {
        selectedAsstFaculty = [];
        renderAsstFacultyTags();
    }
    const form = document.getElementById(formId);
    if (form) {
        const btn = form.querySelector('button[type="submit"]');
        if (btn) {
            const entityName = formId.replace('form-', '').charAt(0).toUpperCase() + formId.replace('form-', '').slice(1);
            btn.textContent = 'Add ' + entityName;
            btn.classList.remove('warning');
        }
    }
}

// ---------------------------------------------------------------------------
// Rooms Tab
// ---------------------------------------------------------------------------
function loadRooms() {
    loadTableData('/api/rooms', 'table-rooms', ['id', 'name', 'room_type', 'capacity', 'category']);
}

document.getElementById('form-room')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        id: document.getElementById('room_id').value,
        name: document.getElementById('room_name').value,
        room_type: document.getElementById('room_type').value,
        capacity: parseInt(document.getElementById('room_capacity').value) || null,
        category: document.getElementById('room_category').value || null
    };
    try {
        if (editingEndpoint === '/api/rooms' && editingId) {
            await fetchJSON('/api/rooms/' + editingId, { method: 'PUT', body: JSON.stringify(payload) });
            showNotification('Room updated');
        } else {
            await fetchJSON('/api/rooms', { method: 'POST', body: JSON.stringify(payload) });
            showNotification('Room added');
        }
        resetEditState('form-room');
        clearForm('form-room');
        loadRooms();
    } catch (e) { }
});

// ---------------------------------------------------------------------------
// Faculty Tab
// ---------------------------------------------------------------------------
function loadFaculty() {
    loadTableData('/api/faculty', 'table-faculty', ['id', 'name']);
}

document.getElementById('form-faculty')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        id: document.getElementById('faculty_id').value,
        name: document.getElementById('faculty_name').value
    };
    try {
        if (editingEndpoint === '/api/faculty' && editingId) {
            await fetchJSON('/api/faculty/' + editingId, { method: 'PUT', body: JSON.stringify(payload) });
            showNotification('Faculty updated');
        } else {
            await fetchJSON('/api/faculty', { method: 'POST', body: JSON.stringify(payload) });
            showNotification('Faculty added');
        }
        resetEditState('form-faculty');
        clearForm('form-faculty');
        loadFaculty();
    } catch (e) { }
});

// ---------------------------------------------------------------------------
// Sections Tab
// ---------------------------------------------------------------------------
async function loadSections() {
    try {
        const sections = await fetchJSON('/api/sections');
        const tbody = document.querySelector('#table-sections tbody');
        tbody.innerHTML = '';
        sections.forEach(s => {
            const tr = document.createElement('tr');
            ['id', 'name', 'semester', 'division', 'strength'].forEach(col => {
                const td = document.createElement('td');
                td.textContent = s[col] !== null && s[col] !== undefined ? s[col] : '';
                tr.appendChild(td);
            });

            // Home Room column
            const hrTd = document.createElement('td');
            hrTd.textContent = s.home_room_id || '-';
            tr.appendChild(hrTd);

            // Batches column
            const batchesTd = document.createElement('td');
            if (s.batches && s.batches.length > 0) {
                const batchTotal = s.batches.reduce((sum, b) => sum + (b.strength || 0), 0);
                let badge = '';
                if (s.strength !== null && s.strength !== undefined) {
                    if (batchTotal > s.strength) {
                        badge = ` <span class="badge" style="background:#fef2f2;color:#dc2626;border:1px solid #fecaca;font-size:11px;padding:2px 6px;" title="Total batch strength (${batchTotal}) exceeds section capacity (${s.strength})">Total: ${batchTotal}/${s.strength} (Exceeds Limit!)</span>`;
                    } else if (batchTotal === s.strength) {
                        badge = ` <span class="badge" style="background:#f0fdf4;color:#166534;border:1px solid #bbf7d0;font-size:11px;padding:2px 6px;">Total: ${batchTotal}/${s.strength} (Full)</span>`;
                    } else {
                        badge = ` <span class="badge" style="background:#f8fafc;color:#475569;border:1px solid #cbd5e1;font-size:11px;padding:2px 6px;">Total: ${batchTotal}/${s.strength}</span>`;
                    }
                }
                batchesTd.innerHTML = s.batches.map(b => `${b.name} (${b.strength || '?'})`).join(', ') + badge;
            } else {
                batchesTd.textContent = 'None';
            }
            tr.appendChild(batchesTd);

            const actionTd = document.createElement('td');
            const editBtn = document.createElement('button');
            editBtn.className = 'btn';
            editBtn.style.marginRight = '5px';
            editBtn.textContent = 'Edit';
            editBtn.onclick = () => editItem('/api/sections', s);
            actionTd.appendChild(editBtn);

            const delBtn = document.createElement('button');
            delBtn.className = 'btn danger';
            delBtn.textContent = 'Delete';
            delBtn.onclick = async () => {
                if (!confirm('Delete section and its batches?')) return;
                await fetchJSON(`/api/sections/${s.id}`, { method: 'DELETE' });
                showNotification('Section deleted');
                loadSections();
            };
            actionTd.appendChild(delBtn);
            tr.appendChild(actionTd);
            tbody.appendChild(tr);
        });

        window._sectionsData = sections;

        const batchSecSelect = document.getElementById('batch_section');
        batchSecSelect.innerHTML = '<option value="">Select Section</option>';
        sections.forEach(s => {
            batchSecSelect.innerHTML += `<option value="${s.id}">${s.name}</option>`;
        });

        // Populate Home Room dropdown
        try {
            const rooms = await fetchJSON('/api/rooms');
            const hrSelect = document.getElementById('section_home_room_id');
            if (hrSelect) {
                hrSelect.innerHTML = '<option value="">Home Room (Optional)</option>';
                rooms.filter(r => r.room_type === 'THEORY_ROOM').forEach(r => {
                    hrSelect.innerHTML += `<option value="${r.id}">${r.name} (${r.id})</option>`;
                });
            }
        } catch(e) {}
    } catch (e) { }
}

document.getElementById('form-section')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        id: document.getElementById('section_id').value,
        name: document.getElementById('section_name').value,
        semester: parseInt(document.getElementById('section_semester').value),
        division: document.getElementById('section_division').value,
        strength: parseInt(document.getElementById('section_strength').value) || null,
        home_room_id: document.getElementById('section_home_room_id').value || null
    };
    try {
        if (editingEndpoint === '/api/sections' && editingId) {
            await fetchJSON('/api/sections/' + editingId, { method: 'PUT', body: JSON.stringify(payload) });
            showNotification('Section updated');
        } else {
            await fetchJSON('/api/sections', { method: 'POST', body: JSON.stringify(payload) });
            showNotification('Section added');
        }
        resetEditState('form-section');
        clearForm('form-section');
        loadSections();
    } catch (e) { }
});

document.getElementById('form-batch')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const secId = document.getElementById('batch_section').value;
    const batchStrength = parseInt(document.getElementById('batch_strength').value) || 0;

    // Client-side section capacity validation
    if (window._sectionsData && secId) {
        const sec = window._sectionsData.find(s => s.id === secId);
        if (sec && sec.strength) {
            const existingTotal = (sec.batches || [])
                .filter(b => b.id !== (editingEndpoint === '/api/batches' ? editingId : null))
                .reduce((sum, b) => sum + (b.strength || 0), 0);
            if (existingTotal + batchStrength > sec.strength) {
                showNotification(`Total batch strength (${existingTotal + batchStrength}) would exceed Section '${sec.name}' capacity (${sec.strength})!`, 'error');
                return;
            }
        }
    }
    const payload = {
        id: document.getElementById('batch_id').value,
        name: document.getElementById('batch_name').value,
        section_id: document.getElementById('batch_section').value,
        strength: parseInt(document.getElementById('batch_strength').value) || null
    };
    if (!payload.section_id) {
        showNotification('Please select a section for the batch', 'error');
        return;
    }
    try {
        if (editingEndpoint === '/api/batches' && editingId) {
            await fetchJSON('/api/batches/' + editingId, { method: 'PUT', body: JSON.stringify(payload) });
            showNotification('Batch updated');
        } else {
            await fetchJSON('/api/batches', { method: 'POST', body: JSON.stringify(payload) });
            showNotification('Batch added');
        }
        resetEditState('form-batch');
        clearForm('form-batch');
        loadSections();
    } catch (e) { }
});

// ---------------------------------------------------------------------------
// Courses Tab
// ---------------------------------------------------------------------------
async function loadCourses() {
    await loadTableData('/api/courses', 'table-courses', [
        'id', 'code', 'name', 'section_id',
        (item) => `${item.l}-${item.t}-${item.p}`,
        (item) => item.lab_batches && item.lab_batches.length ? item.lab_batches.join(', ') : '-',
        (item) => item.faculty_ids && item.faculty_ids.length ? item.faculty_ids.join(', ') : '-',
        (item) => item.assistant_faculty_ids && item.assistant_faculty_ids.length ? item.assistant_faculty_ids.join(', ') : '-',
        'room_type',
        (item) => item.required_room_id || '-'
    ]);

    try {
        const sections = await fetchJSON('/api/sections');
        const secSelect = document.getElementById('course_section');
        secSelect.innerHTML = '<option value="">Select Section</option>';
        sections.forEach(s => secSelect.innerHTML += `<option value="${s.id}">${s.name}</option>`);

        const faculty = await fetchJSON('/api/faculty');
        window._facultyList = faculty;
        const facSelect = document.getElementById('course_faculty');
        facSelect.innerHTML = '<option value="">Select Faculty</option>';
        faculty.forEach(f => facSelect.innerHTML += `<option value="${f.id}">${f.name}</option>`);

        const asstFacSelect = document.getElementById('course_assistant_faculty');
        if (asstFacSelect) {
            asstFacSelect.innerHTML = '<option value="">Select Assistant Faculty (Optional)</option>';
            faculty.forEach(f => asstFacSelect.innerHTML += `<option value="${f.id}">${f.name}</option>`);
        }

        const rooms = await fetchJSON('/api/rooms');
        const roomSelect = document.getElementById('course_required_room');
        roomSelect.innerHTML = '<option value="">Required Room (Optional)</option>';
        rooms.forEach(r => roomSelect.innerHTML += `<option value="${r.id}">${r.name}</option>`);

        window._sectionsData = sections;
    } catch (e) { }
}

let selectedAsstFaculty = [];

function renderAsstFacultyTags() {
    const container = document.getElementById('course_asst_tags');
    if (!container) return;
    container.innerHTML = selectedAsstFaculty.map(f => `
        <span class="badge" style="background:#eff6ff;color:#1e40af;border:1px solid #bfdbfe;font-size:11.5px;padding:2px 8px;border-radius:4px;display:inline-flex;align-items:center;gap:4px;">
            ${f.name}
            <span style="cursor:pointer;font-weight:bold;margin-left:2px;" onclick="removeAsstFaculty('${f.id}')">&times;</span>
        </span>
    `).join('');
}

window.removeAsstFaculty = function(id) {
    selectedAsstFaculty = selectedAsstFaculty.filter(f => f.id !== id);
    renderAsstFacultyTags();
};

document.getElementById('course_assistant_faculty')?.addEventListener('change', (e) => {
    const val = e.target.value;
    if (!val) return;
    const fac = (window._facultyList || []).find(f => f.id === val);
    const name = fac ? fac.name : val;
    if (!selectedAsstFaculty.some(item => item.id === val)) {
        selectedAsstFaculty.push({ id: val, name: name });
        renderAsstFacultyTags();
    }
    e.target.value = '';
});

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

document.getElementById('course_section')?.addEventListener('change', updateBatchDropdown);

document.getElementById('course_p')?.addEventListener('input', (e) => {
    const p = parseInt(e.target.value) || 0;
    const batchSelect = document.getElementById('course_lab_batches');
    if (p > 0) {
        batchSelect.style.display = 'block';
        updateBatchDropdown();
    } else {
        batchSelect.style.display = 'none';
        Array.from(batchSelect.options).forEach(o => o.selected = false);
    }
});

document.getElementById('form-course')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const mainFac = document.getElementById('course_faculty').value;
    const facultyIds = mainFac ? [mainFac] : [];
    const assistantFacultyIds = selectedAsstFaculty.map(f => f.id);

    const batchSelect = document.getElementById('course_lab_batches');
    const labBatches = Array.from(batchSelect.selectedOptions).map(opt => opt.value);

    const payload = {
        id: document.getElementById('course_id').value,
        name: document.getElementById('course_name').value,
        code: document.getElementById('course_code').value,
        section_id: document.getElementById('course_section').value,
        l: parseFloat(document.getElementById('course_l').value) || 0,
        t: parseFloat(document.getElementById('course_t').value) || 0,
        p: parseFloat(document.getElementById('course_p').value) || 0,
        faculty_ids: facultyIds,
        assistant_faculty_ids: assistantFacultyIds,
        room_type: document.getElementById('course_room_type').value,
        required_room_id: document.getElementById('course_required_room').value || null,
        lab_batches: labBatches,
    };

    try {
        if (editingEndpoint === '/api/courses' && editingId) {
            await fetchJSON('/api/courses/' + editingId, { method: 'PUT', body: JSON.stringify(payload) });
            showNotification('Course updated');
        } else {
            await fetchJSON('/api/courses', { method: 'POST', body: JSON.stringify(payload) });
            showNotification('Course added');
        }
        resetEditState('form-course');
        clearForm('form-course');
        selectedAsstFaculty = [];
        renderAsstFacultyTags();

        document.getElementById('course_l').value = '0';
        document.getElementById('course_t').value = '0';
        document.getElementById('course_p').value = '0';

        const bSel = document.getElementById('course_lab_batches');
        bSel.style.display = 'none';
        Array.from(bSel.options).forEach(o => o.selected = false);

        loadCourses();
    } catch (e) { }
});

// ---------------------------------------------------------------------------
// Generate Tab
// ---------------------------------------------------------------------------
document.getElementById('btn-generate')?.addEventListener('click', async () => {
    const btn = document.getElementById('btn-generate');
    const statusDiv = document.getElementById('generate-status');
    const statusCard = document.getElementById('gen-status-card');
    const statusText = document.getElementById('gen-status-text');
    const scoreDiv = document.getElementById('gen-score');
    const diagDiv = document.getElementById('gen-diagnostics');

    btn.disabled = true;
    btn.innerHTML = 'Generating...';
    statusDiv.style.display = 'block';
    statusCard.className = 'status-card';
    statusText.textContent = 'Generating institutional schedule... please wait';
    statusText.style.color = 'var(--text-secondary)';
    scoreDiv.style.display = 'none';
    diagDiv.style.display = 'none';

    try {
        const res = await fetchJSON('/api/generate', { method: 'POST' });

        if (res.status === 'success') {
            const stats = res.stats || {};
            statusCard.className = 'status-card success-card';
            statusText.innerHTML = `Schedule Generated Successfully`;
            statusText.style.color = 'var(--success)';
            scoreDiv.style.display = 'block';

            let detailsHtml = '';
            if (res.soft_score && res.soft_score.details) {
                detailsHtml = '<div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:8px;">' +
                    Object.entries(res.soft_score.details)
                    .map(([k, v]) => `<span style="background:white;border:1px solid #cbd5e1;border-radius:6px;padding:4px 10px;font-size:12px;color:#334155;">${v.description || k}: <strong>${v.score}/${v.max}</strong></span>`)
                    .join('') + '</div>';
            }
            scoreDiv.innerHTML = `
                <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
                    <div>
                        <div style="font-size:1.25rem;font-weight:700;color:var(--success);">${res.soft_score ? res.soft_score.percentage : 0}% Distribution Score</div>
                        <div style="font-size:12.5px;color:var(--text-secondary);margin-top:2px;">${stats.total_sessions || 0} sessions allocated · <strong>${stats.backtracks || 0} backtracks</strong> · ${stats.time_ms || 0}ms computation time</div>
                    </div>
                    <button type="button" class="btn primary btn-sm" onclick="document.querySelector('.tab-btn[data-target=\\'views\\']').click()">
                        Open Timetable Views &rarr;
                    </button>
                </div>
                ${detailsHtml}
            `;

            setTimeout(() => {
                showNotification('Timetable ready! Switch to Timetable Views tab', 'success');
            }, 600);

        } else {
            statusCard.className = 'status-card error-card';
            statusText.innerHTML = `Generation Failed`;
            statusText.style.color = 'var(--danger)';
            diagDiv.style.display = 'block';
            diagDiv.innerHTML = `<strong>Error:</strong> ${res.message || 'Infeasible problem'}<br><pre style="font-size:12px;margin-top:8px;white-space:pre-wrap;">${res.diagnostics || ''}</pre>`;
        }
    } catch (e) {
        statusCard.className = 'status-card error-card';
        statusText.innerHTML = `Error: ${e.message}`;
        statusText.style.color = 'var(--danger)';
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Generate Timetable';
    }
});

document.getElementById('btn-validate')?.addEventListener('click', async () => {
    const reportDiv = document.getElementById('validation-report');
    const content = document.getElementById('val-content');
    reportDiv.style.display = 'block';
    content.innerHTML = 'Validating...';
    try {
        const res = await fetchJSON('/api/validation');
        if (res.valid) {
            content.innerHTML = '<span style="color:green;font-weight:600;">All hard constraints satisfied. Timetable is conflict-free!</span>';
        } else {
            content.innerHTML = `<ul style="color:red;">${res.conflicts.map(c => `<li>${c}</li>`).join('')}</ul>`;
        }
    } catch (e) { }
});

// ---------------------------------------------------------------------------
// Timetable Views Tab
// ---------------------------------------------------------------------------
let globalConfig = null;

async function fetchConfigForViews() {
    if (!globalConfig) {
        const res = await fetch('/api/config');
        if (res.ok) {
            globalConfig = await res.json();
        }
    }
    return globalConfig;
}

function generateTimelineColumns(config, timeSlots) {
    let breaks = [...(config.breaks || [])];
    if (config.lunch_start && config.lunch_end) {
        breaks.push({ start_time: config.lunch_start, end_time: config.lunch_end, is_lunch: true });
    }
    breaks.sort((a, b) => a.start_time.localeCompare(b.start_time));

    let sortedSlots = [...timeSlots].sort((a, b) => a.start_time.localeCompare(b.start_time));
    let all_blocks = [];
    sortedSlots.forEach(s => all_blocks.push({ type: 'slot', ...s }));
    breaks.forEach(b => all_blocks.push({ type: 'break', ...b }));
    all_blocks.sort((a, b) => a.start_time.localeCompare(b.start_time));
    return all_blocks;
}

async function fetchMasterAssignments() {
    const res = await fetch('/api/timetable/master');
    if (!res.ok) return null;
    return await res.json();
}

function renderUnifiedGrid(assignments, filterType, filterValue, config, timeSlots) {
    const container = document.getElementById('view-content');
    container.innerHTML = '';

    if (!assignments || assignments.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No timetable data available. Please generate a timetable first.</p></div>';
        return;
    }

    let filtered = assignments;
    if (filterType === 'section') {
        filtered = assignments.filter(a => a.section_id === filterValue);
    } else if (filterType === 'faculty') {
        filtered = assignments.filter(a => (a.faculty_ids && a.faculty_ids.includes(filterValue)) || a.faculty_id === filterValue);
    } else if (filterType === 'room') {
        filtered = assignments.filter(a => a.room_id === filterValue);
    }

    const days = config.working_days;
    const timeline = generateTimelineColumns(config, timeSlots);

    let uniqueSections = [];
    if (filterType === 'master') {
        let secMap = {};
        assignments.forEach(a => {
            secMap[a.section_id] = a.section_name || a.section_id;
        });
        uniqueSections = Object.keys(secMap).sort().map(id => ({ id: id, name: secMap[id] }));
    }

    let rowGroups = [];
    days.forEach(day => {
        if (filterType === 'master') {
            uniqueSections.forEach((sec, idx) => {
                rowGroups.push({
                    day: day,
                    rowLabel: sec.name,
                    filterVal: sec.id,
                    isFirstOfGroup: idx === 0,
                    groupSize: uniqueSections.length
                });
            });
        } else {
            rowGroups.push({ day: day, rowLabel: day, filterVal: null, isFirstOfGroup: true, groupSize: 1 });
        }
    });

    let table = document.createElement('table');
    table.className = 'timetable-grid';

    let thead = document.createElement('thead');
    let headRow = document.createElement('tr');

    if (filterType === 'master') {
        headRow.innerHTML = `<th>Day</th><th>Section</th>`;
    } else {
        headRow.innerHTML = `<th>Day</th>`;
    }

    timeline.forEach(col => {
        if (col.type === 'break') {
            headRow.innerHTML += `<th class="break-col"><div class="break-title">${col.is_lunch ? 'LUNCH' : 'BREAK'}</div><div class="break-time">${col.start_time} - ${col.end_time}</div></th>`;
        } else {
            headRow.innerHTML += `<th><div class="slot-time">${col.start_time} - ${col.end_time}</div></th>`;
        }
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    let tbody = document.createElement('tbody');

    rowGroups.forEach(rg => {
        let tr = document.createElement('tr');

        if (filterType === 'master') {
            if (rg.isFirstOfGroup) {
                tr.innerHTML = `<td class="day-header" rowspan="${rg.groupSize}">${rg.day}</td>`;
            }
            tr.innerHTML += `<td class="day-header">${rg.rowLabel}</td>`;
        } else {
            tr.innerHTML = `<td class="day-header">${rg.rowLabel}</td>`;
        }

        let colsHTML = [];
        let currentGroup = null;

        timeline.forEach(col => {
            let activeSessions = filtered.filter(a => {
                let matchFilter = filterType === 'master' ? (a.day === rg.day && a.section_id === rg.filterVal) : (a.day === rg.day);
                return matchFilter && a.time_start <= col.start_time && a.time_end >= col.end_time;
            });

            if (activeSessions.length === 0) {
                if (currentGroup) { colsHTML.push(currentGroup); currentGroup = null; }
                if (col.type === 'break') {
                    colsHTML.push({ type: 'break', col: col });
                } else {
                    colsHTML.push({ type: 'empty' });
                }
            } else {
                activeSessions.sort((a, b) => (a.batch_name || '').localeCompare(b.batch_name || ''));
                let sig = activeSessions.map(a => `${a.course_name}_${a.batch_name}_${a.room_name}`).join('|');

                if (!currentGroup) {
                    currentGroup = { type: 'sessions', sig: sig, sessions: activeSessions, colspan: 1 };
                } else if (currentGroup.sig === sig) {
                    currentGroup.colspan++;
                } else {
                    colsHTML.push(currentGroup);
                    currentGroup = { type: 'sessions', sig: sig, sessions: activeSessions, colspan: 1 };
                }
            }
        });

        if (currentGroup) colsHTML.push(currentGroup);

        colsHTML.forEach(item => {
            if (item.type === 'break') {
                tr.innerHTML += `<td class="tt-cell-break"><span class="break-tag">${item.col.is_lunch ? 'LUNCH' : 'BREAK'}</span></td>`;
            } else if (item.type === 'empty') {
                tr.innerHTML += `<td class="tt-cell-empty"></td>`;
            } else {
                let arr = item.sessions;
                let overallCss = arr.some(a => a.course_type === 'LAB') ? 'tt-cell-lab' : 'tt-cell-theory';

                let detailsArr = arr.map(a => {
                    let facs = a.faculty_name ? a.faculty_name : (a.faculty_ids ? a.faculty_ids.join(', ') : '');
                    let bBadge = (a.batch_name && a.batch_name !== 'ALL') ? `<span class="tt-batch">${a.batch_name}</span>` : '';
                    let rRoom = a.room_name ? `Room: ${a.room_name}` : '';
                    let rFac = facs && filterType !== 'faculty' ? `Faculty: ${facs}` : '';
                    let rSec = (filterType !== 'master' && filterType !== 'section' && a.section_name) ? a.section_name : '';

                    let meta = [rSec, rFac, rRoom].filter(Boolean);

                    return `
                        <div class="tt-session-card">
                            <div class="tt-subj">${a.course_name} ${bBadge}</div>
                            ${meta.length > 0 ? `<div class="tt-meta">${meta.map(m => `<span>${m}</span>`).join('<span class="tt-meta-divider">|</span>')}</div>` : ''}
                        </div>
                    `;
                });

                let htmlBlock = detailsArr.join('<hr class="tt-session-divider">');
                tr.innerHTML += `<td colspan="${item.colspan}" class="${overallCss}">${htmlBlock}</td>`;
            }
        });

        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    const wrapper = document.createElement('div');
    wrapper.className = 'timetable-wrapper';
    wrapper.appendChild(table);
    container.appendChild(wrapper);
}

async function renderMasterView() {
    const config = await fetchConfigForViews();
    const tsRes = await fetch('/api/time-slots');
    const timeSlots = await tsRes.json();
    const assignments = await fetchMasterAssignments();
    renderUnifiedGrid(assignments, 'master', null, config, timeSlots);
}

async function renderSectionView(sectionId) {
    const config = await fetchConfigForViews();
    const tsRes = await fetch('/api/time-slots');
    const timeSlots = await tsRes.json();
    const assignments = await fetchMasterAssignments();
    renderUnifiedGrid(assignments, 'section', sectionId, config, timeSlots);
}

async function renderFacultyView(facultyId) {
    const config = await fetchConfigForViews();
    const tsRes = await fetch('/api/time-slots');
    const timeSlots = await tsRes.json();
    const assignments = await fetchMasterAssignments();
    renderUnifiedGrid(assignments, 'faculty', facultyId, config, timeSlots);
}

async function renderRoomView(roomId) {
    const config = await fetchConfigForViews();
    const tsRes = await fetch('/api/time-slots');
    const timeSlots = await tsRes.json();
    const assignments = await fetchMasterAssignments();
    renderUnifiedGrid(assignments, 'room', roomId, config, timeSlots);
}

document.querySelectorAll('.view-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
        document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        const view = e.target.dataset.view;
        const selector = document.getElementById('view-selector');

        const btnPrint = document.getElementById('btn-print');
        if (btnPrint) btnPrint.style.display = 'inline-block';

        if (view === 'master') {
            selector.style.display = 'none';
            await renderMasterView();
        } else {
            selector.style.display = 'inline-block';
            selector.innerHTML = '<option value="">Select...</option>';

            let data = [];
            if (view === 'section') {
                const res = await fetch('/api/sections');
                data = await res.json();
                data.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.id;
                    opt.textContent = d.name || d.id;
                    selector.appendChild(opt);
                });
                selector.onchange = (ev) => renderSectionView(ev.target.value);
            } else if (view === 'faculty') {
                const res = await fetch('/api/faculty');
                data = await res.json();
                data.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.id;
                    opt.textContent = d.name || d.id;
                    selector.appendChild(opt);
                });
                selector.onchange = (ev) => renderFacultyView(ev.target.value);
            } else if (view === 'room') {
                const res = await fetch('/api/rooms');
                data = await res.json();
                data.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.id;
                    opt.textContent = d.name || d.id;
                    selector.appendChild(opt);
                });
                selector.onchange = (ev) => renderRoomView(ev.target.value);
            }

            document.getElementById('view-content').innerHTML = '<div class="empty-state"><p>Select an option from the dropdown above to view its timetable.</p></div>';
        }
    });
});

function loadTimetableViewsInit() {
    const activeBtn = document.querySelector('.view-btn.active');
    if (!activeBtn) {
        const masterBtn = document.querySelector('.view-btn[data-view="master"]');
        if (masterBtn) masterBtn.click();
    }
}

// ---------------------------------------------------------------------------
// Excel Import Tab
// ---------------------------------------------------------------------------
document.getElementById('btn-preview-import')?.addEventListener('click', async () => {
    const fileInput = document.getElementById('excel-file');
    if (!fileInput || !fileInput.files.length) {
        showNotification('Please select an Excel file first.', 'error');
        return;
    }
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const btn = document.getElementById('btn-preview-import');
        btn.textContent = 'Previewing...';
        btn.disabled = true;

        const res = await fetch('/api/import-excel?preview=true', { method: 'POST', body: formData });
        const data = await res.json();

        btn.textContent = 'Preview Data';
        btn.disabled = false;

        const previewDiv = document.getElementById('import-preview');
        const countsDiv = document.getElementById('preview-counts');
        const errorsDiv = document.getElementById('preview-errors');
        previewDiv.style.display = 'block';

        if (!res.ok) {
            countsDiv.innerHTML = '';
            let errorMsg = data.error || 'Validation failed';
            if (data.details) errorMsg += '<br>' + data.details.join('<br>');
            errorsDiv.innerHTML = errorMsg;
            document.getElementById('btn-import-excel').style.display = 'none';
        } else {
            errorsDiv.innerHTML = '';
            countsDiv.innerHTML = `
                <ul style="margin-left: 20px; line-height: 1.8;">
                    <li><strong>Faculty:</strong> ${data.counts.faculty} members</li>
                    <li><strong>Rooms:</strong> ${data.counts.rooms} rooms</li>
                    <li><strong>Sections:</strong> ${data.counts.sections} sections</li>
                    <li><strong>Batches:</strong> ${data.counts.batches} batches</li>
                    <li><strong>Courses:</strong> ${data.counts.courses} courses</li>
                </ul>
                <p style="color: #10b981; font-weight: 600; margin-top: 12px;">Validation passed. Ready to persist into SQLite.</p>
            `;
            document.getElementById('btn-import-excel').style.display = 'inline-block';
        }
    } catch (e) {
        showNotification('Failed to preview Excel file.', 'error');
    }
});

document.getElementById('btn-import-excel')?.addEventListener('click', async () => {
    const fileInput = document.getElementById('excel-file');
    if (!fileInput || !fileInput.files.length) return;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    try {
        const btn = document.getElementById('btn-import-excel');
        btn.textContent = 'Importing to SQLite...';
        btn.disabled = true;

        const res = await fetch('/api/import-excel', { method: 'POST', body: formData });
        const data = await res.json();
        if (!res.ok) {
            showNotification(data.error || 'Import failed', 'error');
        } else {
            showNotification('Dataset imported and saved to SQLite successfully!');
            document.getElementById('import-preview').style.display = 'none';
            btn.style.display = 'none';
            if (typeof loadRooms === 'function') await loadRooms();
            if (typeof loadFaculty === 'function') await loadFaculty();
            if (typeof loadSections === 'function') await loadSections();
            if (typeof loadCourses === 'function') await loadCourses();
        }
        btn.textContent = 'Import to SQLite';
        btn.disabled = false;
    } catch (e) {
        showNotification('Import failed.', 'error');
    }
});
