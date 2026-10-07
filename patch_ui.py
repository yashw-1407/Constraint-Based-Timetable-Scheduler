import re

# 1. Update style.css
with open('static/style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Add a professional timetable table styling
professional_css = """

/* Professional Timetable Styling */
.timetable-grid {
    border-collapse: separate;
    border-spacing: 0;
    width: 100%;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    background: #ffffff;
    font-size: 14px;
}

.timetable-grid th, .timetable-grid td {
    border: 1px solid #eeeeee;
    padding: 10px;
    text-align: center;
    vertical-align: middle;
}

.timetable-grid th {
    background-color: #f8f9fa;
    color: #333333;
    font-weight: 600;
    position: sticky;
    top: 0;
    z-index: 2;
    border-bottom: 2px solid #dee2e6;
}

.timetable-grid th:first-child {
    position: sticky;
    left: 0;
    z-index: 3;
    background-color: #f8f9fa;
}

.timetable-grid .day-header {
    background-color: #f1f3f5;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 13px;
    position: sticky;
    left: 0;
    z-index: 1;
    border-right: 2px solid #dee2e6;
}

/* Distinct, elegant colors */
.tt-cell-theory {
    background-color: #e3f2fd;
    color: #0d47a1;
    border: 1px solid #bbdefb !important;
    border-radius: 4px;
}

.tt-cell-lab {
    background-color: #e8f5e9;
    color: #1b5e20;
    border: 1px solid #c8e6c9 !important;
    border-radius: 4px;
}

.tt-cell-empty {
    background-color: #fafafa;
    color: #bdbdbd;
}

.tt-cell-break {
    background-color: #fff3e0;
    color: #e65100;
    font-weight: bold;
    letter-spacing: 2px;
    writing-mode: vertical-rl;
    transform: rotate(180deg);
    border-left: 2px dashed #ffb74d !important;
    border-right: 2px dashed #ffb74d !important;
}

.tt-session-card {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.tt-subj {
    font-weight: bold;
    font-size: 13px;
    line-height: 1.2;
}

.tt-meta {
    font-size: 11px;
    opacity: 0.85;
    display: flex;
    justify-content: center;
    gap: 8px;
    flex-wrap: wrap;
}

.tt-batch {
    display: inline-block;
    padding: 1px 4px;
    border-radius: 3px;
    background: rgba(0,0,0,0.08);
    font-weight: bold;
}
"""

if 'Professional Timetable Styling' not in css:
    css += professional_css
    with open('static/style.css', 'w', encoding='utf-8') as f:
        f.write(css)


# 2. Update app.js
with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Fix the faculty filter bug
js = js.replace(
    "filtered = assignments.filter(a => a.faculty_id === filterValue || (a.faculty_name && a.faculty_name.includes(filterValue)));",
    "filtered = assignments.filter(a => (a.faculty_ids && a.faculty_ids.includes(filterValue)) || a.faculty_id === filterValue);"
)

# Improve cell rendering logic in renderUnifiedGrid
old_cell_logic = """
                    let cellContent = '-';
                    let className = '';
                    if (overlapping.length > 0) {
                        const s = overlapping[0];
                        cellContent = `${s.course_name}<br>(${s.batch_name})<br>${s.faculty_name}<br>${s.room_name}`;
                        className = s.course_type === 'LAB' ? 'style="background-color: #d4edda;"' : 'style="background-color: #cce5ff;"';
                    }
                    
                    rowHtml += `<td colspan="${colspan}" ${className}>${cellContent}</td>`;
"""

new_cell_logic = """
                    let cellContent = '-';
                    let className = 'tt-cell-empty';
                    
                    if (overlapping.length > 0) {
                        const s = overlapping[0];
                        className = s.course_type === 'LAB' ? 'tt-cell-lab' : 'tt-cell-theory';
                        
                        let batchHtml = s.batch_name && s.batch_name !== 'ALL' ? `<span class="tt-batch">${s.batch_name}</span>` : '';
                        
                        cellContent = `
                            <div class="tt-session-card">
                                <div class="tt-subj">${s.course_name} ${batchHtml}</div>
                                <div class="tt-meta">
                                    <span>🧑‍🏫 ${s.faculty_name || s.faculty_ids.join(',')}</span>
                                    <span>🚪 ${s.room_name}</span>
                                </div>
                            </div>
                        `;
                    }
                    
                    rowHtml += `<td colspan="${colspan}" class="${className}">${cellContent}</td>`;
"""
if "tt-session-card" not in js:
    js = js.replace(old_cell_logic, new_cell_logic)

# Replace table class to use our new professional styling
js = js.replace("<table border=\"1\"", "<table class=\"timetable-grid\"")
js = js.replace("style=\"background-color: #f8f9fa;\"", "class=\"tt-cell-break\"")
js = js.replace("<td>BREAK</td>", "<td>B<br>R<br>E<br>A<br>K</td>")
js = js.replace("<td>LUNCH</td>", "<td>L<br>U<br>N<br>C<br>H</td>")
js = js.replace("<strong>${sec.name}</strong>", "<div class=\"day-header\">${sec.name}</div>")
js = js.replace("<td><strong>${day}</strong></td>", "<td class=\"day-header\">${day}</td>")

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(js)
print('UI Patched successfully')
