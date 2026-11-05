import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# I will write a UI patch for app.js to handle editing dynamically.
# Let's inspect app.js first.
with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Update loadTableData to include an Edit button
old_loadTableData = '''            const delBtn = document.createElement('button');
            delBtn.className = 'btn danger';
            delBtn.textContent = 'Delete';
            delBtn.onclick = () => deleteItem(endpoint, item[rowIdKey], () => loadTableData(endpoint, tableId, columns, rowIdKey));
            actionTd.appendChild(delBtn);'''

new_loadTableData = '''            const editBtn = document.createElement('button');
            editBtn.className = 'btn';
            editBtn.style.marginRight = '5px';
            editBtn.textContent = 'Edit';
            editBtn.onclick = () => editItem(endpoint, item);
            actionTd.appendChild(editBtn);

            const delBtn = document.createElement('button');
            delBtn.className = 'btn danger';
            delBtn.textContent = 'Delete';
            delBtn.onclick = () => deleteItem(endpoint, item[rowIdKey], () => loadTableData(endpoint, tableId, columns, rowIdKey));
            actionTd.appendChild(delBtn);'''

js = js.replace(old_loadTableData, new_loadTableData)

# Add editItem logic
edit_logic = '''
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
            // Check if it's a multi-select or special field
            if (field.tagName === 'SELECT' && field.multiple && Array.isArray(item[key])) {
                Array.from(field.options).forEach(opt => {
                    opt.selected = item[key].includes(opt.value);
                });
            } else {
                field.value = item[key] !== null ? item[key] : '';
            }
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
'''
if 'function editItem' not in js:
    js += '\n' + edit_logic

# Update form submit listeners to handle PUT
# For rooms
js = js.replace('''await fetchJSON('/api/rooms', { method: 'POST', body: JSON.stringify(payload) });
        showNotification('Room added');''', '''
        if (editingEndpoint === '/api/rooms' && editingId) {
            await fetchJSON('/api/rooms/' + editingId, { method: 'PUT', body: JSON.stringify(payload) });
            showNotification('Room updated');
        } else {
            await fetchJSON('/api/rooms', { method: 'POST', body: JSON.stringify(payload) });
            showNotification('Room added');
        }
        resetEditState('form-room');''')

# For faculty
js = js.replace('''await fetchJSON('/api/faculty', { method: 'POST', body: JSON.stringify(payload) });
        showNotification('Faculty added');''', '''
        if (editingEndpoint === '/api/faculty' && editingId) {
            await fetchJSON('/api/faculty/' + editingId, { method: 'PUT', body: JSON.stringify(payload) });
            showNotification('Faculty updated');
        } else {
            await fetchJSON('/api/faculty', { method: 'POST', body: JSON.stringify(payload) });
            showNotification('Faculty added');
        }
        resetEditState('form-faculty');''')

# For sections
js = js.replace('''await fetchJSON('/api/sections', { method: 'POST', body: JSON.stringify(payload) });
        showNotification('Section added');''', '''
        if (editingEndpoint === '/api/sections' && editingId) {
            await fetchJSON('/api/sections/' + editingId, { method: 'PUT', body: JSON.stringify(payload) });
            showNotification('Section updated');
        } else {
            await fetchJSON('/api/sections', { method: 'POST', body: JSON.stringify(payload) });
            showNotification('Section added');
        }
        resetEditState('form-section');''')

# For courses
js = js.replace('''await fetchJSON('/api/courses', { method: 'POST', body: JSON.stringify(payload) });
        showNotification('Course added');''', '''
        if (editingEndpoint === '/api/courses' && editingId) {
            await fetchJSON('/api/courses/' + editingId, { method: 'PUT', body: JSON.stringify(payload) });
            showNotification('Course updated');
        } else {
            await fetchJSON('/api/courses', { method: 'POST', body: JSON.stringify(payload) });
            showNotification('Course added');
        }
        resetEditState('form-course');''')


# Add resetEditState
reset_logic = '''
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
'''
if 'function resetEditState' not in js:
    js += '\n' + reset_logic

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(js)

print("Frontend patched for editing!")
