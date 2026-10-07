import re

with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Replace the catch block in generate to show real error
js = js.replace("statusText.textContent = 'Error during generation';", "statusText.textContent = 'Error: ' + e.message;")

# Re-write renderMasterView
master_view_code = '''
async function renderMasterView() {
    const content = document.getElementById('view-content');
    content.innerHTML = 'Loading...';
    try {
        const configData = await fetchJSON('/api/config');
        const slotsData = await fetchJSON('/api/time-slots');
        const data = await fetchJSON('/api/timetable/master');
        
        if (!data || data.length === 0 || !configData || !slotsData) {
            content.innerHTML = '<p>No timetable data available.</p>';
            return;
        }

        // Group data by day, then section
        const schedule = {};
        const days = configData.working_days;
        
        // Find all unique sections from the data
        const sectionsSet = new Set();
        data.forEach(row => sectionsSet.add(row.section_name));
        const sections = Array.from(sectionsSet).sort();

        // Initialize schedule structure
        days.forEach(day => {
            schedule[day] = {};
            sections.forEach(sec => {
                schedule[day][sec] = {};
            });
        });

        // Populate schedule
        data.forEach(row => {
            const day = row.day;
            const sec = row.section_name;
            const startIdx = parseInt(row.time_start_idx || row.start_slot_index || 0); // We need start_slot_index in the API response!
            // Wait, we need to make sure the API returns start_slot_index and duration_slots
            if (!schedule[day][sec][row.time_start]) {
                schedule[day][sec][row.time_start] = [];
            }
            schedule[day][sec][row.time_start].push(row);
        });
        
        // Let's create a combined timeline of periods (slots + breaks)
        // Convert times to minutes for sorting
        const timeToMin = (t) => {
            const parts = t.split(':');
            return parseInt(parts[0]) * 60 + parseInt(parts[1]);
        };
        
        let timeline = [];
        slotsData.forEach(s => {
            timeline.push({ type: 'slot', start: s.start_time, end: s.end_time, startMin: timeToMin(s.start_time), endMin: timeToMin(s.end_time), original: s });
        });
        
        const lunch = { type: 'break', label: 'LUNCH', start: configData.lunch_start, end: configData.lunch_end, startMin: timeToMin(configData.lunch_start), endMin: timeToMin(configData.lunch_end) };
        timeline.push(lunch);
        
        configData.breaks.forEach(b => {
            const bstart = b.start_time || b.start;
            const bend = b.end_time || b.end;
            if(bstart && bend) {
                timeline.push({ type: 'break', label: 'BREAK', start: bstart, end: bend, startMin: timeToMin(bstart), endMin: timeToMin(bend) });
            }
        });
        
        // Sort timeline
        timeline.sort((a, b) => a.startMin - b.startMin);
        
        // Filter out zero-duration or invalid overlaps if needed, but they shouldn't overlap if generation was right.
        
        let html = '<table class="timetable-grid" style="width:100%; border-collapse: collapse;">';
        html += '<thead><tr><th style="border:1px solid #ccc; padding:8px;">Day</th><th style="border:1px solid #ccc; padding:8px;">Section</th>';
        timeline.forEach(p => {
            html += \<th style="border:1px solid #ccc; padding:8px; \">\ - \<br>\</th>\;
        });
        html += '</tr></thead><tbody>';
        
        days.forEach(day => {
            sections.forEach((sec, sIdx) => {
                html += '<tr>';
                if (sIdx === 0) {
                    html += \<td rowspan="\" style="border:1px solid #ccc; padding:8px; font-weight:bold; vertical-align:middle; text-align:center;">\</td>\;
                }
                html += \<td style="border:1px solid #ccc; padding:8px; font-weight:bold;">\</td>\;
                
                let skipSlots = 0;
                
                for (let i = 0; i < timeline.length; i++) {
                    const p = timeline[i];
                    if (p.type === 'break') {
                        if (sIdx === 0) {
                            html += \<td rowspan="\" style="border:1px solid #ccc; background:#f0f0f0; text-align:center; vertical-align:middle; font-weight:bold; color:#777;">\</td>\;
                        }
                        continue;
                    }
                    
                    if (skipSlots > 0) {
                        skipSlots--;
                        continue;
                    }
                    
                    const cellClasses = schedule[day] && schedule[day][sec] && schedule[day][sec][p.start] ? schedule[day][sec][p.start] : [];
                    
                    if (cellClasses.length === 0) {
                        html += '<td style="border:1px solid #ccc; padding:8px; text-align:center; color:#ccc;">-</td>';
                    } else {
                        // Find max duration to set colspan
                        let maxDuration = 1;
                        cellClasses.forEach(c => {
                            // duration_slots comes from API if we update it
                            if (c.duration_slots && c.duration_slots > maxDuration) {
                                maxDuration = c.duration_slots;
                            }
                        });
                        
                        let cellBg = cellClasses.some(c => c.course_type === 'LAB') ? '#e6f7ff' : '#f9f9f9';
                        html += \<td colspan="\" style="border:1px solid #ccc; padding:8px; background:\; vertical-align:top;">\;
                        
                        cellClasses.forEach(c => {
                            html += \<div style="margin-bottom:8px; border-bottom:1px solid #eee; padding-bottom:4px;">\;
                            html += \<strong>\</strong> \;
                            if (c.course_type === 'LAB' && c.batch_name) {
                                html += \<span style="background:#007bff; color:white; padding:2px 4px; border-radius:3px; font-size:0.8em;">\</span>\;
                            }
                            html += \<br><small>\ | \</small>\;
                            html += \</div>\;
                        });
                        
                        html += '</td>';
                        
                        skipSlots = maxDuration - 1;
                    }
                }
                html += '</tr>';
            });
        });
        
        html += '</tbody></table>';
        content.innerHTML = html;
        
    } catch (e) {
        content.innerHTML = 'Error loading master view: ' + e.message;
    }
}
'''
js = re.sub(r'async function renderMasterView\(\) \{.*?\n\}\n', master_view_code + '\n', js, flags=re.DOTALL)

# Add Preview logic to import-excel
import_logic = '''
document.getElementById('btn-preview-import')?.addEventListener('click', async () => {
    const fileInput = document.getElementById('excel-file');
    if (!fileInput.files.length) {
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
            countsDiv.innerHTML = 
                <ul>
                    <li>Faculty: </li>
                    <li>Rooms: </li>
                    <li>Sections: </li>
                    <li>Batches: </li>
                    <li>Courses: </li>
                </ul>
                <p style="color:green; font-weight:bold;">Validation Passed. Ready to import.</p>
            ;
            document.getElementById('btn-import-excel').style.display = 'inline-block';
        }
    } catch (e) {
        showNotification('Failed to preview file.', 'error');
    }
});

// Update the actual import button to just use the original logic but inside the new tab
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
'''
# Replace the old btn-import-excel logic
js = re.sub(r"document\.getElementById\('btn-import-excel'\)\?\.addEventListener\('click', async \(\) => \{.*?\n\}\);\n", import_logic + '\n', js, flags=re.DOTALL)

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(js)
