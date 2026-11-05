const API_BASE = '';

// Notification system
function showNotification(message, type = 'success') {
    const notif = document.getElementById('notification');
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
    document.getElementById(formId).reset();
}

// Tab Switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        e.target.classList.add('active');
        const targetId = e.target.getAttribute('data-target');
        document.getElementById(targetId).classList.add('active');
        window.location.hash = targetId;
        
        loadTabData(targetId);
    });
});

window.addEventListener('DOMContentLoaded', () => {
    checkAuthStatus();
    fetchTerms();
    fetchPublishingStatus();
    const hash = (window.location.hash || '').replace('#', '');
    if (hash) {
        const btn = document.querySelector(`.tab-btn[data-target="${hash}"]`);
        if (btn) btn.click();
    }
});

// Academic Terms Management
async function fetchTerms() {
    try {
        const res = await fetch('/api/terms');
        if (!res.ok) return;
        const data = await res.json();
        const selector = document.getElementById('header-term-select');
        if (!selector) return;

        selector.innerHTML = (data.terms || []).map(t =>
            `<option value="${t.id}" ${t.id === data.active_term_id ? 'selected' : ''}>${t.name}</option>`
        ).join('');

        selector.onchange = async (e) => {
            const termId = e.target.value;
            try {
                const actRes = await fetchJSON(`/api/terms/activate/${termId}`, { method: 'POST' });
                showNotification(`Active semester set to ${actRes.active_term ? actRes.active_term.name : termId}`, 'info');
                fetchPublishingStatus();
                loadTimetableViewsInit();
            } catch (err) {
                showNotification('Failed to switch academic term', 'error');
            }
        };
    } catch (e) {
        console.warn('Could not load terms:', e);
    }
}

// Load data based on tab
function loadTabData(tabId) {
    if (tabId === 'config') {
        loadConfig();
    } else if (tabId === 'rooms') loadRooms();
    else if (tabId === 'faculty') loadFaculty();
    else if (tabId === 'sections') loadSections();
    else if (tabId === 'courses') loadCourses();
    else if (tabId === 'views') loadTimetableViewsInit();
}

// Configuration Tab
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
        console.error("Config not loaded", e);
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

document.getElementById('btn-add-break').addEventListener('click', () => addBreakRow());

document.getElementById('form-config').addEventListener('submit', async (e) => {
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

document.getElementById('btn-load-demo').addEventListener('click', async () => {
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
document.getElementById('btn-clear-data').addEventListener('click', async () => {
    if (!confirm('Are you sure you want to clear all data?')) return;
    try {
        await fetchJSON('/api/clear', { method: 'POST' });
        showNotification('Data cleared');
        loadConfig();
    } catch (e) { }
});

// Common Data Loading Functions
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
    if (!confirm('Are you sure?')) return;
    try {
        await fetchJSON(`${endpoint}/${id}`, { method: 'DELETE' });
        showNotification('Deleted successfully');
        callback();
    } catch (e) { }
}

// Rooms Tab
function loadRooms() {
    loadTableData('/api/rooms', 'table-rooms', ['id', 'name', 'room_type', 'capacity', 'category']);
}
document.getElementById('form-room').addEventListener('submit', async (e) => {
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

// Faculty Tab
function loadFaculty() {
    loadTableData('/api/faculty', 'table-faculty', ['id', 'name']);
}
document.getElementById('form-faculty').addEventListener('submit', async (e) => {
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

// Sections Tab (with batches)
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
            // Batches column
            const batchesTd = document.createElement('td');
            if (s.batches && s.batches.length > 0) {
                const batchList = s.batches.map(b => `${b.name} (${b.strength || '?'})`).join(', ');
                batchesTd.innerHTML = batchList;
            } else {
                batchesTd.textContent = 'None';
            }
            tr.appendChild(batchesTd);
            // Actions
            const actionTd = document.createElement('td');
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

        // Populate batch section dropdown
        const batchSecSelect = document.getElementById('batch_section');
        batchSecSelect.innerHTML = '<option value="">Select Section</option>';
        sections.forEach(s => batchSecSelect.innerHTML += `<option value="${s.id}">${s.name}</option>`);
    } catch (e) { }
}

document.getElementById('form-section').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        id: document.getElementById('section_id').value,
        name: document.getElementById('section_name').value,
        semester: parseInt(document.getElementById('section_semester').value),
        division: document.getElementById('section_division').value,
        strength: parseInt(document.getElementById('section_strength').value) || null
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

document.getElementById('form-batch').addEventListener('submit', async (e) => {
    e.preventDefault();
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

// Courses Tab
async function loadCourses() {
    await loadTableData('/api/courses', 'table-courses',
        ['id', 'code', 'name', 'section_id',
         (item) => `${item.l}-${item.t}-${item.p}`,
         (item) => item.lab_batches && item.lab_batches.length ? item.lab_batches.join(', ') : '-',
         (item) => item.faculty_ids ? item.faculty_ids.join(', ') : '',
         (item) => item.assistant_faculty_ids && item.assistant_faculty_ids.length ? item.assistant_faculty_ids.join(', ') : '',
         'room_type']);
    
    // Populate dropdowns
    try {
        const sections = await fetchJSON('/api/sections');
        const secSelect = document.getElementById('course_section');
        secSelect.innerHTML = '<option value="">Select Section</option>';
        sections.forEach(s => secSelect.innerHTML += `<option value="${s.id}">${s.name}</option>`);
        
        const faculty = await fetchJSON('/api/faculty');
                const facSelect = document.getElementById('course_faculty');
        facSelect.innerHTML = '<option value="">Select Faculty</option>';
        faculty.forEach(f => facSelect.innerHTML += `<option value="${f.id}">${f.name}</option>`);
        
        const asstFacSelect = document.getElementById('course_assistant_faculty');
        if (asstFacSelect) {
            asstFacSelect.innerHTML = '';
            faculty.forEach(f => asstFacSelect.innerHTML += `<option value="${f.id}">${f.name}</option>`);
        }
        
        const rooms = await fetchJSON('/api/rooms');
        const roomSelect = document.getElementById('course_required_room');
        roomSelect.innerHTML = '<option value="">Required Room (Optional)</option>';
        rooms.forEach(r => roomSelect.innerHTML += `<option value="${r.id}">${r.name}</option>`);

        // Store sections data for batch dropdown updates
        window._sectionsData = sections;
    } catch(e) {}
}

// Update batch dropdown when section changes
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
});

document.getElementById('form-course').addEventListener('submit', async (e) => {
    e.preventDefault();
        const facSelect = document.getElementById('course_faculty');
    const facultyIds = Array.from(facSelect.selectedOptions).map(opt => opt.value).filter(val => val !== "");
    
    const asstFacSelect = document.getElementById('course_assistant_faculty');
    const assistantFacultyIds = asstFacSelect ? Array.from(asstFacSelect.selectedOptions).map(opt => opt.value).filter(val => val !== "") : [];
    
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
        
        document.getElementById('course_l').value = '0';
        document.getElementById('course_t').value = '0';
        document.getElementById('course_p').value = '0';
        
        const bSel = document.getElementById('course_lab_batches');
        bSel.style.display = 'none';
        Array.from(bSel.options).forEach(o => o.selected = false);

        loadCourses();
    } catch (e) { }
});

// Generate Tab
document.getElementById('btn-generate').addEventListener('click', async () => {
    const btn = document.getElementById('btn-generate');
    const statusDiv = document.getElementById('generate-status');
    const statusCard = document.getElementById('gen-status-card');
    const statusText = document.getElementById('gen-status-text');
    const scoreDiv = document.getElementById('gen-score');
    const diagDiv = document.getElementById('gen-diagnostics');

    // Show loading state
    btn.disabled = true;
    btn.innerHTML = 'Generating...';
    statusDiv.style.display = 'block';
    statusCard.className = 'status-card';
    statusText.textContent = 'Running CSP solver... please wait';
    statusText.style.color = 'var(--text-muted)';
    scoreDiv.style.display = 'none';
    diagDiv.style.display = 'none';

    try {
        const res = await fetchJSON('/api/generate', { method: 'POST' });

        if (res.status === 'success') {
            const bestVariant = res.variants && res.variants.length > 0 ? res.variants[res.active_variant_index || 0] : res;
            const stats = bestVariant.stats || {};

            statusCard.className = 'status-card success-card';
            statusText.innerHTML = `Timetable generated successfully!`;
            statusText.style.color = 'var(--color-success)';
            scoreDiv.style.display = 'block';

            let detailsHtml = '';
            if (bestVariant.soft_score && bestVariant.soft_score.details) {
                detailsHtml = '<div class="score-details-list">' +
                    Object.entries(bestVariant.soft_score.details)
                    .map(([k,v]) => `<span class="score-chip">${v.description || k}: <strong>${v.score}/${v.max}</strong></span>`)
                    .join('') + '</div>';
            }
            scoreDiv.innerHTML = `
                <div class="score-header-row">
                    <div class="score-percent-value">${bestVariant.soft_score ? bestVariant.soft_score.percentage : 0}% Quality Score</div>
                    <div class="score-meta-stats">${stats.total_sessions || 0} sessions | ${stats.backtracks || 0} backtracks | ${stats.time_ms || 0}ms</div>
                </div>
                ${detailsHtml}
            `;

            const btnExport = document.getElementById('btn-export-excel');
            if (btnExport) btnExport.style.display = 'inline-flex';
            const btnPrint = document.getElementById('btn-print');
            if (btnPrint) btnPrint.style.display = 'inline-block';
            fetchPublishingStatus();

            const varPanel = document.getElementById('variants-comparison-panel');
            if (varPanel) varPanel.style.display = 'none';

            setTimeout(() => {
                showNotification('Timetable ready! Switch to Timetable Views tab', 'success');
            }, 600);

        } else {
            statusCard.className = 'status-card error-card';
            statusText.innerHTML = `Generation Infeasible: ${(res.stats||{}).scheduled||0}/${(res.stats||{}).total_sessions||'?'} sessions scheduled`;
            statusText.style.color = 'var(--color-danger)';
            diagDiv.style.display = 'block';
            diagDiv.innerHTML = `<strong>Diagnostic Conflict:</strong> ${res.message || 'Infeasible problem'}<br><pre class="diagnostics-pre">${res.diagnostics || ''}</pre>`;
        }
    } catch (e) {
        statusCard.className = 'status-card error-card';
        statusText.innerHTML = `Error: ${e.message}`;
        statusText.style.color = 'var(--color-danger)';
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Generate Timetable';
    }
});

document.getElementById('btn-validate').addEventListener('click', async () => {
    const reportDiv = document.getElementById('validation-report');
    const content = document.getElementById('val-content');
    reportDiv.style.display = 'block';
    content.innerHTML = '<span class="val-pending">Validating configuration against hard constraints...</span>';
    try {
        const res = await fetchJSON('/api/validation');
        if (res.valid) {
            content.innerHTML = '<div class="val-success-banner">All hard constraints satisfied. No conflicts found.</div>';
        } else {
            content.innerHTML = `<ul class="val-error-list">${res.conflicts.map(c => `<li>${c}</li>`).join('')}</ul>`;
        }
    } catch (e) { }
});


// Timetable Views
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
    let columns = [];
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

let cachedMasterAssignments = [];
async function fetchMasterAssignments() {
    const res = await fetch('/api/timetable/master');
    if (!res.ok) return null;
    cachedMasterAssignments = await res.json();
    return cachedMasterAssignments;
}

function renderUnifiedGrid(assignments, filterType, filterValue, config, timeSlots) {
    const container = document.getElementById('view-content');
    container.innerHTML = '';
    
    if (!assignments || assignments.length === 0) {
        container.innerHTML = '<p>No timetable data available.</p>';
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
            headRow.innerHTML += `<th class="break-col">${col.is_lunch ? 'LUNCH' : 'BREAK'}<br><span style="font-size:10px;font-weight:normal;">${col.start_time}-${col.end_time}</span></th>`;
        } else {
            headRow.innerHTML += `<th>${col.start_time}-${col.end_time}</th>`;
        }
    });
    thead.appendChild(headRow);
    table.appendChild(thead);
    
    let tbody = document.createElement('tbody');
    
    let assignMap = {};
    filtered.forEach(a => {
        let key = filterType === 'master' ? `${a.day}_${a.section_id}_${a.time_start}` : `${a.day}_${a.time_start}`;
        if (!assignMap[key]) assignMap[key] = [];
        assignMap[key].push(a);
    });
    
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
            if (col.type === 'break') {
                if (currentGroup) { colsHTML.push(currentGroup); currentGroup = null; }
                colsHTML.push({ type: 'break', col: col });
                return;
            }
            
            // Find all active sessions in this exact slot
            let activeSessions = filtered.filter(a => {
                let matchFilter = filterType === 'master' ? (a.day === rg.day && a.section_id === rg.filterVal) : (a.day === rg.day);
                // Active if the session starts at or before this slot AND ends at or after this slot ends
                return matchFilter && a.time_start <= col.start_time && a.time_end >= col.end_time;
            });
            
            if (activeSessions.length === 0) {
                if (currentGroup) { colsHTML.push(currentGroup); currentGroup = null; }
                colsHTML.push({ type: 'empty' });
            } else {
                // Generate a signature for the exact set of sessions active right now
                activeSessions.sort((a, b) => a.session_id.localeCompare(b.session_id));
                let sig = activeSessions.map(a => a.session_id).join('|');
                
                if (!currentGroup) {
                    currentGroup = { type: 'sessions', sig: sig, sessions: activeSessions, colspan: 1 };
                } else if (currentGroup.sig === sig) {
                    // Exact same sessions continue into this slot! Extend colspan!
                    currentGroup.colspan++;
                } else {
                    // Sessions changed! Commit current group and start a new one
                    colsHTML.push(currentGroup);
                    currentGroup = { type: 'sessions', sig: sig, sessions: activeSessions, colspan: 1 };
                }
            }
        });
        
        if (currentGroup) { colsHTML.push(currentGroup); }

        colsHTML.forEach(item => {
            if (item.type === 'break') {
                tr.innerHTML += `<td class="tt-cell-break">${item.col.is_lunch ? 'L U N C H' : 'B R E A K'}</td>`;
            } else if (item.type === 'empty') {
                tr.innerHTML += `<td class="tt-cell-empty"></td>`;
            } else {
                let arr = item.sessions;
                let overallCss = arr.some(a => a.course_type === 'LAB') ? 'tt-cell-lab' : 'tt-cell-theory';
                
                let detailsArr = arr.map(a => {
                    let facs = a.faculty_name ? a.faculty_name : (a.faculty_ids ? a.faculty_ids.join(', ') : '');
                    let bBadge = (a.batch_name && a.batch_name !== 'ALL') ? `<span class="tt-batch">${a.batch_name}</span>` : '';
                    let rRoom = `<span>Room: ${a.room_name}</span>`;
                    let rFac = `<span>Faculty: ${facs}</span>`;
                    let rSec = filterType !== 'master' ? `<span>${a.section_name || a.section_id}</span>` : '';
                    
                    let meta = [];
                    if (rSec) meta.push(rSec);
                    if (rFac && filterType !== 'faculty') meta.push(rFac);
                    if (rRoom && filterType !== 'room') meta.push(rRoom);
                    
                    return `
                        <div class="tt-session-card" data-session-id="${a.session_id}" style="cursor: pointer;" title="Click to adjust session placement">
                            <div class="tt-subj">${a.course_name} ${bBadge}</div>
                            <div class="tt-meta">${meta.join(' | ')}</div>
                        </div>
                    `;
                });
                
                let htmlBlock = detailsArr.join('<hr style="margin:4px 0; border:0; border-top:1px dashed rgba(0,0,0,0.1);">');
                tr.innerHTML += `<td colspan="${item.colspan}" class="${overallCss}">${htmlBlock}</td>`;
            }
        });
        
        tbody.appendChild(tr);
    });
      
    table.appendChild(tbody);
    const scrollContainer = document.createElement('div');
    scrollContainer.className = 'table-scroll';
    scrollContainer.appendChild(table);
    container.appendChild(scrollContainer);

    scrollContainer.querySelectorAll('.tt-session-card').forEach(card => {
        card.addEventListener('click', (e) => {
            const sid = e.currentTarget.getAttribute('data-session-id');
            if (sid) openMoveModal(sid);
        });
    });
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
        const btnExport = document.getElementById('btn-export-excel');
        if (btnExport) btnExport.style.display = 'inline-flex';
        
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
            
            document.getElementById('view-content').innerHTML = '<div class="empty-state"><p>Select from the dropdown above to view the timetable.</p></div>';
        }
    });
});


let editingEndpoint = null;
let editingId = null;

function editItem(endpoint, item) {
    editingEndpoint = endpoint;
    editingId = item.id;
    
    // Determine entity prefix based on endpoint
    let prefix = '';
    if (endpoint.includes('/rooms')) prefix = 'room_';
    else if (endpoint.includes('/faculty')) prefix = 'faculty_';
    else if (endpoint.includes('/sections')) prefix = 'section_';
    else if (endpoint.includes('/batches')) prefix = 'batch_';
    else if (endpoint.includes('/courses')) prefix = 'course_';

    // Populate form fields
    for (const key in item) {
        const field = document.getElementById(prefix + key);
        if (field) {
            if (field.tagName === 'SELECT' && field.multiple && Array.isArray(item[key])) {
                // Ignore lab_batches for now, we will handle it after
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

    // Specially handle course sections and batches
    if (prefix === 'course_') {
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
        
        const labDur = document.getElementById('course_lab_duration');
        if (labDur) {
            labDur.style.display = 'none';
        }
    }
    
    // Change submit button text
    const formId = 'form-' + prefix.replace('_', '');
    const form = document.getElementById(formId);
    if (form) {
        const btn = form.querySelector('button[type="submit"]');
        if (btn) {
            btn.textContent = 'Update';
            btn.classList.add('warning'); // optionally change color
        }
    }
}


function resetEditState(formId) {
    editingEndpoint = null;
    editingId = null;
    const form = document.getElementById(formId);
    if (form) {
        const btn = form.querySelector('button[type="submit"]');
        if (btn) {
            btn.textContent = 'Add ' + formId.replace('form-', '').charAt(0).toUpperCase() + formId.replace('form-', '').slice(1);
            btn.classList.remove('warning');
        }
    }
}

// Timetable Views Initialization & Publishing Lifecycle
async function loadTimetableViewsInit() {
    await fetchPublishingStatus();
    const activeBtn = document.querySelector('.view-btn.active');
    if (!activeBtn) {
        const masterBtn = document.querySelector('.view-btn[data-view="master"]');
        if (masterBtn) masterBtn.click();
    } else {
        const view = activeBtn.dataset.view;
        const selector = document.getElementById('view-selector');
        if (view === 'master') {
            await renderMasterView();
        } else if (selector && selector.value) {
            if (view === 'section') await renderSectionView(selector.value);
            else if (view === 'faculty') await renderFacultyView(selector.value);
            else if (view === 'room') await renderRoomView(selector.value);
        }
    }
}

// Publishing State Management
async function fetchPublishingStatus() {
    try {
        const res = await fetch('/api/timetable/status');
        if (!res.ok) return;
        const data = await res.json();
        updatePublishingUI(data);
    } catch (e) {
        console.warn('Could not load timetable status:', e);
    }
}

function updatePublishingUI(data) {
    const headerChip = document.getElementById('header-lifecycle-chip');
    const viewsBadge = document.getElementById('views-lifecycle-badge');
    const btnPublish = document.getElementById('btn-publish-schedule');
    const btnUnpublish = document.getElementById('btn-unpublish-schedule');

    const isPublished = Boolean(data && data.is_published);
    const label = isPublished ? 'Published' : 'Draft';

    if (headerChip) {
        headerChip.textContent = label;
        headerChip.className = isPublished ? 'lifecycle-chip chip-published' : 'lifecycle-chip chip-draft';
        if (data && data.published_at) {
            headerChip.title = `Published at ${data.published_at} UTC`;
        } else {
            headerChip.title = 'Schedule in draft state';
        }
    }

    if (viewsBadge) {
        viewsBadge.textContent = label;
        viewsBadge.className = isPublished ? 'lifecycle-chip chip-published' : 'lifecycle-chip chip-draft';
    }

    if (btnPublish && btnUnpublish) {
        if (isPublished) {
            btnPublish.style.display = 'none';
            btnUnpublish.style.display = 'inline-block';
        } else {
            btnPublish.style.display = 'inline-block';
            btnUnpublish.style.display = 'none';
        }
    }
}

document.getElementById('btn-publish-schedule')?.addEventListener('click', async () => {
    try {
        const res = await fetchJSON('/api/timetable/publish', { method: 'POST' });
        showNotification('Timetable published to institutional registry', 'success');
        updatePublishingUI(res);
    } catch (err) {
        showNotification('Failed to publish timetable: ' + err.message, 'error');
    }
});

document.getElementById('btn-unpublish-schedule')?.addEventListener('click', async () => {
    try {
        const res = await fetchJSON('/api/timetable/unpublish', { method: 'POST' });
        showNotification('Timetable reverted to Draft state', 'info');
        updatePublishingUI(res);
    } catch (err) {
        showNotification('Failed to unpublish timetable: ' + err.message, 'error');
    }
});

// Candidate Variants Comparison & Pareto Selection
let candidateVariants = [];
let activeVariantIndex = 0;

function renderVariantsComparison(variants, activeIdx) {
    candidateVariants = variants || [];
    activeVariantIndex = activeIdx || 0;

    const panel = document.getElementById('variants-comparison-panel');
    const grid = document.getElementById('variants-grid');
    if (!panel || !grid) return;

    if (!candidateVariants || candidateVariants.length === 0) {
        panel.style.display = 'none';
        grid.innerHTML = '';
        return;
    }

    panel.style.display = 'block';
    grid.innerHTML = '';

    candidateVariants.forEach((v, idx) => {
        const isActive = idx === activeVariantIndex;
        const card = document.createElement('div');
        card.className = isActive ? 'variant-card active-variant' : 'variant-card';

        const score = v.soft_score ? v.soft_score.percentage : 0;
        const divLabel = v.diversity_pct === 'Base' ? 'Baseline Pareto' : `${v.diversity_pct}% Divergence`;
        const stats = v.stats || {};

        let chipsHtml = '';
        if (v.soft_score && v.soft_score.details) {
            chipsHtml = Object.entries(v.soft_score.details)
                .slice(0, 3)
                .map(([k, d]) => `<span class="score-chip">${d.description || k}: <strong>${d.score}/${d.max}</strong></span>`)
                .join('');
        }

        card.innerHTML = `
            <div class="variant-card-header">
                <h4 class="variant-title">Candidate Schedule ${idx + 1}</h4>
                ${isActive ? '<span class="variant-active-indicator">Active Selection</span>' : ''}
            </div>
            <div class="variant-metrics-row">
                <span class="variant-score-badge">${score}% Quality</span>
                <span class="variant-diversity-tag">${divLabel}</span>
            </div>
            <div class="variant-chips-wrap">
                ${chipsHtml}
            </div>
            <div style="font-size: 11.5px; color: var(--color-text-secondary); margin-top: auto;">
                ${stats.total_sessions || 0} sessions &bull; ${stats.backtracks || 0} backtracks &bull; ${stats.time_ms || 0}ms
            </div>
            <div style="display: flex; gap: var(--space-2); margin-top: var(--space-2);">
                <button type="button" class="btn btn-sm btn-outline btn-inspect-variant" data-index="${idx}" style="flex: 1;">
                    Inspect Views
                </button>
                ${!isActive ? `<button type="button" class="btn btn-sm btn-primary btn-activate-variant" data-index="${idx}" style="flex: 1;">Activate</button>` : ''}
            </div>
        `;

        grid.appendChild(card);
    });

    grid.querySelectorAll('.btn-activate-variant').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const idx = parseInt(e.currentTarget.getAttribute('data-index'), 10);
            await activateVariant(idx);
        });
    });

    grid.querySelectorAll('.btn-inspect-variant').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const idx = parseInt(e.currentTarget.getAttribute('data-index'), 10);
            if (idx !== activeVariantIndex) {
                await activateVariant(idx);
            }
            const viewsTabBtn = document.querySelector('.tab-btn[data-target="views"]');
            if (viewsTabBtn) viewsTabBtn.click();
        });
    });
}

async function activateVariant(index) {
    try {
        await fetchJSON('/api/timetable/variant/' + index, { method: 'POST' });
        activeVariantIndex = index;
        renderVariantsComparison(candidateVariants, activeVariantIndex);
        showNotification(`Activated Candidate Schedule ${index + 1}`, 'success');

        const activeBtn = document.querySelector('.view-btn.active');
        if (activeBtn) {
            activeBtn.click();
        }
    } catch (e) {
        showNotification('Failed to activate timetable candidate', 'error');
    }
}

document.getElementById('btn-generate-multiple')?.addEventListener('click', async () => {
    const btn = document.getElementById('btn-generate-multiple');
    const singleBtn = document.getElementById('btn-generate');
    const statusDiv = document.getElementById('generate-status');
    const statusCard = document.getElementById('gen-status-card');
    const statusText = document.getElementById('gen-status-text');
    const scoreDiv = document.getElementById('gen-score');
    const diagDiv = document.getElementById('gen-diagnostics');

    btn.disabled = true;
    if (singleBtn) singleBtn.disabled = true;
    btn.innerHTML = 'Generating 3 Alternatives...';
    statusDiv.style.display = 'block';
    statusCard.className = 'status-card';
    statusText.textContent = 'Exploring solution space with randomized heuristic orderings...';
    statusText.style.color = 'var(--color-text-secondary)';
    scoreDiv.style.display = 'none';
    diagDiv.style.display = 'none';

    try {
        const res = await fetchJSON('/api/generate-multiple', {
            method: 'POST',
            body: JSON.stringify({ count: 3, min_diversity_pct: 15 })
        });

        if (res.status === 'success' || res.status === 'partial') {
            statusCard.className = 'status-card success-card';
            statusText.textContent = `Generated ${res.generated} candidate timetable alternatives with verified diversity`;
            statusText.style.color = 'var(--color-success)';

            const variants = res.variants || res.alternatives || [];
            renderVariantsComparison(variants, res.active_variant_index || 0);

            const btnExport = document.getElementById('btn-export-excel');
            if (btnExport) btnExport.style.display = 'inline-flex';
            const btnPrint = document.getElementById('btn-print');
            if (btnPrint) btnPrint.style.display = 'inline-block';

            fetchPublishingStatus();

            showNotification(`Generated ${res.generated} candidate alternatives successfully!`, 'success');
        } else {
            statusCard.className = 'status-card error-card';
            statusText.textContent = 'Candidate Generation Infeasible';
            statusText.style.color = 'var(--color-danger)';
            diagDiv.style.display = 'block';
            diagDiv.innerHTML = `<strong>Diagnostic Conflict:</strong> ${res.message || 'Infeasible problem'}<br><pre class="diagnostics-pre">${res.diagnostics || ''}</pre>`;
        }
    } catch (e) {
        statusCard.className = 'status-card error-card';
        statusText.textContent = `Error: ${e.message}`;
        statusText.style.color = 'var(--color-danger)';
    } finally {
        btn.disabled = false;
        if (singleBtn) singleBtn.disabled = false;
        btn.innerHTML = 'Generate 3 Alternatives';
    }
});



// ---------------------------------------------------------------------------
// Trace / Debug
// ---------------------------------------------------------------------------
async function loadTraceConfig() {
    try {
        const res = await fetchJSON('/api/debug/trace/config');
        if (res) {
            const lvl = document.getElementById('trace-level');
            const flt = document.getElementById('trace-filter');
            if (lvl) lvl.value = res.level;
            if (flt) flt.value = res.session_filter ? res.session_filter.join(', ') : '';
        }
    } catch (err) {
        console.error('Failed to load trace config:', err);
    }
}

async function saveTraceConfig() {
    const lvl = document.getElementById('trace-level');
    const flt = document.getElementById('trace-filter');
    if (!lvl) return;
    const level = parseInt(lvl.value, 10);
    const filter = flt ? flt.value : '';
    
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

// ── Excel Ingestion Modal & Controls ─────────────────────────────────────────
(function () {
    const modal = document.getElementById('modal-import');
    const btnOpen = document.getElementById('btn-open-import');
    const btnClose = document.getElementById('btn-close-import');
    const btnCancel = document.getElementById('btn-cancel-import');
    const form = document.getElementById('form-import-excel');
    const feedback = document.getElementById('import-feedback');
    const submitBtn = document.getElementById('btn-submit-import');

    function openModal() {
        if (modal) {
            modal.style.display = 'flex';
            if (feedback) { feedback.style.display = 'none'; feedback.innerHTML = ''; }
            if (form) form.reset();
        }
    }

    function closeModal() {
        if (modal) modal.style.display = 'none';
    }

    if (btnOpen) btnOpen.addEventListener('click', openModal);
    if (btnClose) btnClose.addEventListener('click', closeModal);
    if (btnCancel) btnCancel.addEventListener('click', closeModal);

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });
    }

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('excel-file-input');
            if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
                alert('Please select an Excel workbook (.xlsx)');
                return;
            }

            const mode = form.querySelector('input[name="import_mode"]:checked')?.value || 'replace';
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('mode', mode);

            submitBtn.disabled = true;
            submitBtn.textContent = 'Validating & Ingesting...';
            if (feedback) feedback.style.display = 'none';

            try {
                const res = await fetch('/api/import/excel', {
                    method: 'POST',
                    body: formData
                });
                const result = await res.json();

                if (res.ok && result.status === 'ok') {
                    const counts = result.imported || {};
                    feedback.className = 'import-feedback-box feedback-success';
                    feedback.innerHTML = `
                        <strong>Import Successful!</strong><br>
                        Ingested: ${counts.rooms || 0} rooms, ${counts.faculty || 0} faculty, ${counts.sections || 0} sections, ${counts.batches || 0} batches, ${counts.courses || 0} courses.
                    `;
                    feedback.style.display = 'block';
                    showNotification('Institutional data imported successfully', 'success');

                    const activeTab = document.querySelector('.tab-btn.active')?.dataset.target || 'config';
                    loadTabData(activeTab);

                    setTimeout(closeModal, 1800);
                } else {
                    feedback.className = 'import-feedback-box feedback-error';
                    const errList = (result.errors || [result.message || 'Validation error'])
                        .map(err => `<li>${err}</li>`).join('');
                    feedback.innerHTML = `
                        <strong>Import Validation Failed:</strong>
                        <ul style="margin: 6px 0 0 16px; padding: 0;">${errList}</ul>
                    `;
                    feedback.style.display = 'block';
                }
            } catch (err) {
                feedback.className = 'import-feedback-box feedback-error';
                feedback.innerHTML = `<strong>Network Error:</strong> ${err.message}`;
                feedback.style.display = 'block';
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Upload & Validate';
            }
        });
    }
})();

// Interactive Schedule Move Modal
async function openMoveModal(sessionId) {
    const session = (cachedMasterAssignments || []).find(a => a.session_id === sessionId);
    if (!session) {
        showNotification('Session details not found in active schedule', 'error');
        return;
    }

    const modal = document.getElementById('modal-move-session');
    const titleEl = document.getElementById('move-modal-course-title');
    const metaEl = document.getElementById('move-modal-course-meta');
    const posEl = document.getElementById('move-modal-current-pos');
    const idInput = document.getElementById('move-session-id');
    const daySelect = document.getElementById('move-target-day');
    const slotSelect = document.getElementById('move-target-slot');
    const roomSelect = document.getElementById('move-target-room');
    const feedback = document.getElementById('move-feedback');

    if (!modal) return;

    idInput.value = sessionId;
    titleEl.textContent = `${session.course_code}: ${session.course_name}`;
    metaEl.textContent = `Section: ${session.section_name} | Batch: ${session.batch_name} | Faculty: ${session.faculty_name} | Duration: ${session.duration_slots || 1} period(s)`;
    posEl.textContent = `Current Placement: ${session.day}, ${session.time_start} - ${session.time_end} in ${session.room_name}`;
    if (feedback) feedback.style.display = 'none';

    try {
        const [config, timeSlotsRes, roomsRes] = await Promise.all([
            fetchConfigForViews(),
            fetch('/api/time-slots'),
            fetch('/api/rooms')
        ]);
        const timeSlots = await timeSlotsRes.json();
        const rooms = await roomsRes.json();

        daySelect.innerHTML = (config.working_days || []).map(d =>
            `<option value="${d}" ${d === session.day ? 'selected' : ''}>${d}</option>`
        ).join('');

        slotSelect.innerHTML = timeSlots.map((ts, idx) =>
            `<option value="${idx}" ${idx === session.start_slot_index ? 'selected' : ''}>Period ${idx + 1} (${ts.start_time} - ${ts.end_time})</option>`
        ).join('');

        roomSelect.innerHTML = rooms.map(r =>
            `<option value="${r.id}" ${r.id === session.room_id ? 'selected' : ''}>${r.name} (${r.room_type}, Cap: ${r.capacity})</option>`
        ).join('');

        modal.style.display = 'flex';
    } catch (err) {
        showNotification('Could not load modal configuration options', 'error');
    }
}

(function initMoveModal() {
    const modal = document.getElementById('modal-move-session');
    const btnClose = document.getElementById('btn-close-move');
    const btnCancel = document.getElementById('btn-cancel-move');
    const btnCheck = document.getElementById('btn-check-move');
    const form = document.getElementById('form-move-session');
    const feedback = document.getElementById('move-feedback');
    const btnApply = document.getElementById('btn-apply-move');

    function closeModal() {
        if (modal) modal.style.display = 'none';
    }

    if (btnClose) btnClose.addEventListener('click', closeModal);
    if (btnCancel) btnCancel.addEventListener('click', closeModal);
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });
    }

    if (btnCheck) {
        btnCheck.addEventListener('click', async () => {
            const sessionId = document.getElementById('move-session-id').value;
            const targetDay = document.getElementById('move-target-day').value;
            const targetSlot = document.getElementById('move-target-slot').value;
            const targetRoom = document.getElementById('move-target-room').value;

            btnCheck.disabled = true;
            btnCheck.textContent = 'Checking...';
            try {
                const res = await fetchJSON('/api/timetable/validate-move', {
                    method: 'POST',
                    body: JSON.stringify({
                        session_id: sessionId,
                        target_day: targetDay,
                        target_start_slot: parseInt(targetSlot, 10),
                        target_room_id: targetRoom
                    })
                });

                if (res.valid) {
                    feedback.className = 'import-feedback-box feedback-success';
                    feedback.innerHTML = `<strong>Conflict-Free:</strong> ${res.message}`;
                    feedback.style.display = 'block';
                } else {
                    feedback.className = 'import-feedback-box feedback-error';
                    feedback.innerHTML = `<strong>Conflict Detected:</strong> ${res.message}`;
                    feedback.style.display = 'block';
                }
            } catch (err) {
                feedback.className = 'import-feedback-box feedback-error';
                feedback.innerHTML = `<strong>Validation Error:</strong> ${err.message}`;
                feedback.style.display = 'block';
            } finally {
                btnCheck.disabled = false;
                btnCheck.textContent = 'Check Feasibility';
            }
        });
    }

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const sessionId = document.getElementById('move-session-id').value;
            const targetDay = document.getElementById('move-target-day').value;
            const targetSlot = document.getElementById('move-target-slot').value;
            const targetRoom = document.getElementById('move-target-room').value;

            btnApply.disabled = true;
            btnApply.textContent = 'Relocating Session...';

            try {
                const res = await fetchJSON('/api/timetable/move', {
                    method: 'POST',
                    body: JSON.stringify({
                        session_id: sessionId,
                        target_day: targetDay,
                        target_start_slot: parseInt(targetSlot, 10),
                        target_room_id: targetRoom
                    })
                });

                if (res.status === 'ok') {
                    showNotification('Session relocated successfully', 'success');
                    closeModal();
                    fetchPublishingStatus();
                    const activeBtn = document.querySelector('.view-btn.active');
                    if (activeBtn) activeBtn.click();
                } else {
                    feedback.className = 'import-feedback-box feedback-error';
                    feedback.innerHTML = `<strong>Cannot Apply Move:</strong> ${res.message}`;
                    feedback.style.display = 'block';
                }
            } catch (err) {
                feedback.className = 'import-feedback-box feedback-error';
                feedback.innerHTML = `<strong>Move Failed:</strong> ${err.message}`;
                feedback.style.display = 'block';
            } finally {
                btnApply.disabled = false;
                btnApply.textContent = 'Apply Move';
            }
        });
    }
})();

// Authentication & Role Session Management
let currentUser = null;

async function checkAuthStatus() {
    try {
        const res = await fetch('/api/auth/me');
        if (!res.ok) return;
        const data = await res.json();
        currentUser = data.authenticated ? data.user : null;
        updateAuthHeaderUI();
    } catch (e) {
        console.warn('Could not check auth status:', e);
    }
}

function updateAuthHeaderUI() {
    const badge = document.getElementById('header-user-badge');
    const btn = document.getElementById('btn-auth-action');
    if (!badge || !btn) return;

    if (currentUser) {
        badge.textContent = `${currentUser.username} (${currentUser.role})`;
        badge.className = 'lifecycle-chip chip-published';
        badge.style.display = 'inline-block';
        btn.textContent = 'Sign Out';
        btn.onclick = handleSignOut;
    } else {
        badge.style.display = 'none';
        btn.textContent = 'Sign In';
        btn.onclick = openAuthModal;
    }
}

async function handleSignOut() {
    try {
        await fetchJSON('/api/auth/logout', { method: 'POST' });
        currentUser = null;
        updateAuthHeaderUI();
        showNotification('Signed out successfully', 'info');
    } catch (e) {
        showNotification('Sign out failed', 'error');
    }
}

function openAuthModal() {
    const modal = document.getElementById('modal-auth');
    if (modal) modal.style.display = 'flex';
}

function closeAuthModal() {
    const modal = document.getElementById('modal-auth');
    if (modal) modal.style.display = 'none';
}

(function initAuthModal() {
    const modal = document.getElementById('modal-auth');
    const btnClose = document.getElementById('btn-close-auth');
    const btnCancel = document.getElementById('btn-cancel-auth');
    const form = document.getElementById('form-auth-login');
    const feedback = document.getElementById('auth-feedback');
    const quickBtns = document.querySelectorAll('.btn-quick-login');

    if (btnClose) btnClose.addEventListener('click', closeAuthModal);
    if (btnCancel) btnCancel.addEventListener('click', closeAuthModal);
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeAuthModal();
        });
    }

    quickBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const u = btn.getAttribute('data-username');
            const p = btn.getAttribute('data-password');
            const userField = document.getElementById('auth-username');
            const passField = document.getElementById('auth-password');
            if (userField && passField) {
                userField.value = u;
                passField.value = p;
                form.requestSubmit();
            }
        });
    });

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('auth-username').value.trim();
            const password = document.getElementById('auth-password').value;
            const submitBtn = document.getElementById('btn-submit-auth');

            submitBtn.disabled = true;
            submitBtn.textContent = 'Authenticating...';
            if (feedback) feedback.style.display = 'none';

            try {
                const res = await fetchJSON('/api/auth/login', {
                    method: 'POST',
                    body: JSON.stringify({ username, password })
                });

                if (res.status === 'ok') {
                    currentUser = res.user;
                    updateAuthHeaderUI();
                    showNotification(`Welcome, ${res.user.name}!`, 'success');
                    closeAuthModal();
                } else {
                    feedback.className = 'import-feedback-box feedback-error';
                    feedback.innerHTML = `<strong>Error:</strong> ${res.error || 'Authentication failed'}`;
                    feedback.style.display = 'block';
                }
            } catch (err) {
                feedback.className = 'import-feedback-box feedback-error';
                feedback.innerHTML = `<strong>Error:</strong> ${err.message}`;
                feedback.style.display = 'block';
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Sign In';
            }
        });
    }
})();
