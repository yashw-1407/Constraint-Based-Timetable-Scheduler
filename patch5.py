import re

with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

import_logic = js.find('function renderUnifiedGrid(')
end = js.find('async function renderMasterView')
old_func = js[import_logic:end]

new_func = """function renderUnifiedGrid(assignments, filterType, filterValue, config, timeSlots) {
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
        
        let skipUntilTime = null;
        
        timeline.forEach(col => {
            if (skipUntilTime && col.start_time < skipUntilTime) {
                return;
            }
            skipUntilTime = null;
            
            if (col.type === 'break') {
                tr.innerHTML += `<td class="tt-cell-break">${col.is_lunch ? 'L U N C H' : 'B R E A K'}</td>`;
                return;
            }
            
            let key = filterType === 'master' ? `${rg.day}_${rg.filterVal}_${col.start_time}` : `${rg.day}_${col.start_time}`;
            let arr = assignMap[key];
            
            if (arr && arr.length > 0) {
                let maxEnd = arr.reduce((max, curr) => curr.time_end > max ? curr.time_end : max, arr[0].time_end);
                
                let colspan = 1;
                let endReached = false;
                for (let i = timeline.indexOf(col) + 1; i < timeline.length; i++) {
                    let nextCol = timeline[i];
                    if (nextCol.start_time >= maxEnd) {
                        endReached = true;
                        break;
                    }
                    colspan++;
                }
                skipUntilTime = maxEnd;
                
                let overallCss = arr[0].course_type === 'LAB' ? 'tt-cell-lab' : 'tt-cell-theory';
                
                let detailsArr = arr.map(a => {
                    let facs = a.faculty_name ? a.faculty_name : (a.faculty_ids ? a.faculty_ids.join(', ') : '');
                    let bBadge = (a.batch_name && a.batch_name !== 'ALL') ? `<span class="tt-batch">${a.batch_name}</span>` : '';
                    let rRoom = `<span>🚪 ${a.room_name}</span>`;
                    let rFac = `<span>🧑‍🏫 ${facs}</span>`;
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
                
                tr.innerHTML += `<td colspan="${colspan}" class="${overallCss}">${htmlBlock}</td>`;
            } else {
                tr.innerHTML += `<td class="tt-cell-empty"></td>`;
            }
        });
        
        tbody.appendChild(tr);
    });
    
    table.appendChild(tbody);
    container.appendChild(table);
}
"""

js = js.replace(old_func, new_func)

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(js)
print('Replaced renderUnifiedGrid')
