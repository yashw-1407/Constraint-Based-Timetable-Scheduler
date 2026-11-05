import re

with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

import_logic = """
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
                <ul style="margin-left: 20px;">
                    <li>Faculty: ${data.counts.faculty}</li>
                    <li>Rooms: ${data.counts.rooms}</li>
                    <li>Sections: ${data.counts.sections}</li>
                    <li>Batches: ${data.counts.batches}</li>
                    <li>Courses: ${data.counts.courses}</li>
                </ul>
                <p style="color:green; font-weight:bold; margin-top: 10px;">Validation Passed. Ready to import.</p>
            `;
            document.getElementById('btn-import-excel').style.display = 'inline-block';
        }
    } catch (e) {
        showNotification('Failed to preview file.', 'error');
    }
});

document.getElementById('btn-import-excel')?.addEventListener('click', async () => {
    const fileInput = document.getElementById('excel-file');
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    try {
        const btn = document.getElementById('btn-import-excel');
        btn.textContent = 'Importing...';
        btn.disabled = true;
        const res = await fetch('/api/import-excel', { method: 'POST', body: formData });
        const data = await res.json();
        if (!res.ok) {
            showNotification(data.error || 'Import failed', 'error');
        } else {
            showNotification('Dataset imported successfully!');
            document.getElementById('import-preview').style.display = 'none';
            btn.style.display = 'none';
            await loadRooms();
            await loadFaculty();
            await loadSections();
            await loadCourses();
        }
        btn.textContent = 'Import Dataset';
        btn.disabled = false;
    } catch (e) {
        showNotification('Import failed.', 'error');
    }
});
"""

if 'btn-preview-import' not in js:
    with open('static/app.js', 'a', encoding='utf-8') as f:
        f.write('\n' + import_logic)
    print('Appended import logic to app.js')
else:
    print('Already there')
