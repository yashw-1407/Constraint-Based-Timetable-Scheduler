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
    const hash = (window.location.hash || '').replace('#', '');
    if (hash) {
        const btn = document.querySelector(`.tab-btn[data-target="${hash}"]`);
        if (btn) btn.click();
    }
});

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
            statusText.style.color = 'var(--success)';
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

            // After 1.5s, prompt user to go to Views tab
            setTimeout(() => {
                showNotification('Timetable ready! Switch to Timetable Views tab', 'success');
            }, 600);

        } else {
            statusCard.className = 'status-card error-card';
            statusText.innerHTML = `Generation Infeasible: ${(res.stats||{}).scheduled||0}/${(res.stats||{}).total_sessions||'?'} sessions scheduled`;
            statusText.style.color = 'var(--danger)';
            diagDiv.style.display = 'block';
            diagDiv.innerHTML = `<strong>Diagnostic Conflict:</strong> ${res.message || 'Infeasible problem'}<br><pre class="diagnostics-pre">${res.diagnostics || ''}</pre>`;
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

async function fetchMasterAssignments() {
    const res = await fetch('/api/timetable/master');
    if (!res.ok) return null;
    return await res.json();
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
                        <div class="tt-session-card">
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

function loadTimetableViewsInit() {
    const activeBtn = document.querySelector('.view-btn.active');
    if (!activeBtn) {
        const masterBtn = document.querySelector('.view-btn[data-view="master"]');
        if (masterBtn) masterBtn.click();
    }
}


let currentVariantIndex = 0;
let totalVariants = 0;

async function loadVariantMetadata() {
    try {
        const nav = document.getElementById('variant-navigator');
        if (!nav) return;
        const res = await fetch('/api/timetable/metadata');
        if (!res.ok) {
            nav.style.display = 'none';
            return;
        }
        const data = await res.json();
        
        if (data.num_variants > 1) {
            nav.style.display = 'flex';
            currentVariantIndex = data.active_variant_index;
            totalVariants = data.num_variants;
            
            const curEl = document.getElementById('var-current');
            const totEl = document.getElementById('var-total');
            const scoreEl = document.getElementById('var-score');
            const prevBtn = document.getElementById('btn-var-prev');
            const nextBtn = document.getElementById('btn-var-next');
            if (curEl) curEl.textContent = currentVariantIndex + 1;
            if (totEl) totEl.textContent = totalVariants;
            if (scoreEl) scoreEl.textContent = data.active_score ? data.active_score.total_score : 0;
            if (prevBtn) prevBtn.disabled = currentVariantIndex === 0;
            if (nextBtn) nextBtn.disabled = currentVariantIndex === totalVariants - 1;
        } else {
            nav.style.display = 'none';
        }
    } catch (e) {
        const nav = document.getElementById('variant-navigator');
        if (nav) nav.style.display = 'none';
    }
}

document.getElementById('btn-var-prev')?.addEventListener('click', async () => {
    if (currentVariantIndex > 0) await switchVariant(currentVariantIndex - 1);
});

document.getElementById('btn-var-next')?.addEventListener('click', async () => {
    if (currentVariantIndex < totalVariants - 1) await switchVariant(currentVariantIndex + 1);
});

async function switchVariant(index) {
    try {
        await fetch('/api/timetable/variant/' + index, { method: 'POST' });
        await loadVariantMetadata();
        
        // Refresh the active view
        const activeBtn = document.querySelector('.view-btn.active');
        if (activeBtn) {
            if (activeBtn.dataset.view === 'master') {
                await renderMasterView();
            } else {
                const selector = document.getElementById('view-selector');
                if (selector.value) {
                    if (activeBtn.dataset.view === 'section') await renderSectionView(selector.value);
                    else if (activeBtn.dataset.view === 'faculty') await renderFacultyView(selector.value);
                    else if (activeBtn.dataset.view === 'room') await renderRoomView(selector.value);
                }
            }
        }
    } catch (e) {
        showNotification('Failed to switch timetable variant', 'error');
    }
}


document.getElementById('btn-generate-multiple')?.addEventListener('click', async () => {
    const statusDiv = document.getElementById('gen-status-alt');
    const statusText = document.getElementById('gen-status-text-alt');
    const scoreDiv = document.getElementById('gen-score-alt');
    const diagDiv = document.getElementById('gen-diagnostics-alt');
    const altList = document.getElementById('alternatives-list');
    
    statusDiv.style.display = 'block';
    statusText.textContent = 'Generating alternatives... Please wait';
    statusText.style.color = '';
    scoreDiv.style.display = 'none';
    diagDiv.style.display = 'none';
    altList.innerHTML = '<p style="color: #666;">Generating...</p>';
    
    try {
        const count = document.getElementById('alt-count').value;
        const divPct = document.getElementById('alt-diversity').value;
        const res = await fetchJSON('/api/generate-multiple', { 
            method: 'POST',
            body: JSON.stringify({ count: count, min_diversity_pct: divPct })
        });
        
        if (res.status === 'success' || res.status === 'partial') {
            lastGeneratedResult = res;
            statusText.textContent = `Generated ${res.generated} unique diverse feasible timetables out of ${res.requested} requested.`;
            statusText.style.color = 'var(--success)';
            renderAlternativesList(res);
        } else {
            statusText.textContent = `Generation Failed (Infeasible)`;
            statusText.style.color = 'var(--danger)';
            diagDiv.style.display = 'block';
            diagDiv.innerHTML = `<strong>Error:</strong> ${res.message}<br><pre>${res.diagnostics}</pre>`;
            altList.innerHTML = '<p style="color: #666;">No alternatives to display.</p>';
        }
    } catch (e) {
        statusText.textContent = 'Error: ' + e.message;
        statusText.style.color = 'var(--danger)';
    }
});

let lastGeneratedResult = null; // store globally when generated

async function makeActive(index) {
    try {
        await fetch('/api/timetable/variant/' + index, { method: 'POST' });
        if (lastGeneratedResult) {
            lastGeneratedResult.active_variant_index = index;
            renderAlternativesList(lastGeneratedResult);
        }
    } catch (e) {
        showNotification('Failed to set active alternative', 'error');
    }
}

function renderAlternativesList(res) {
    const altList = document.getElementById('alternatives-list');
    altList.innerHTML = '';
    res.alternatives.forEach((alt, idx) => {
        const isActive = res.active_variant_index === idx;
        
        const card = document.createElement('div');
        card.style.border = isActive ? '2px solid var(--primary)' : '1px solid #ccc';
        card.style.padding = '15px';
        card.style.borderRadius = '8px';
        card.style.background = isActive ? '#f0f7ff' : '#fff';
        
        const divDisplay = alt.diversity_pct === 'Base' ? 'Base' : `${alt.diversity_pct}%`;
        const changedDisplay = alt.diversity_pct === 'Base' ? '' : `Changed: ${alt.changed_assignments}/${alt.stats.total_sessions} sessions &bull; `;
        
        let html = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h3 style="margin: 0 0 5px 0; font-size: 1.1em;">Alternative ${alt.alternative_id} ${isActive ? '<span style="font-size: 12px; background: var(--primary); color: white; padding: 2px 6px; border-radius: 4px; margin-left: 10px;">ACTIVE</span>' : ''}</h3>
                    
                    <div style="margin-top: 10px;">
                        ${alt.stats.total_sessions}/${alt.stats.total_sessions} sessions
                    </div>
                    <div style="margin-top: 5px; font-weight: bold;">
                        Soft Constraint Score: ${alt.soft_score.percentage}% (${alt.soft_score.total_score})
                    </div>
                    <div style="margin-top: 5px; color: #2c3e50;">
                        Diversity: ${divDisplay}
                    </div>
                    <div style="color: #666; font-size: 13px; margin-top: 5px;">
                        ${changedDisplay}Seed: ${alt.seed} &bull; Time: ${alt.stats.time_ms} ms &bull; Backtracks: ${alt.stats.backtracks}
                    </div>
                </div>
                <div style="display: flex; gap: 10px; margin-top: 5px;">
                    <button class="btn" onclick="document.querySelector('button[data-target=views]').click()">View</button>
                    ${!isActive ? `<button class="btn primary" onclick="makeActive(${idx})">Make Active</button>` : ''}
                </div>
            </div>
        `;
        card.innerHTML = html;
        altList.appendChild(card);
    });
}



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
