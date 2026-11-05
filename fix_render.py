import re

with open('static/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = """    rowGroups.forEach(rg => {
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
                activeSessions.sort((a, b) => a.id.localeCompare(b.id));
                let sig = activeSessions.map(a => a.id).join('|');
                
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
                    let rRoom = `<span>🏠 ${a.room_name}</span>`;
                    let rFac = `<span>👨‍🏫 ${facs}</span>`;
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
    });"""

# Extract the block to replace
start_idx = content.find("    rowGroups.forEach(rg => {")
end_idx = content.find("    table.appendChild(tbody);")

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + replacement + "\n      \n    " + content[end_idx:]
    with open('static/app.js', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully replaced timetable render logic!")
else:
    print("Could not find the block to replace.")
