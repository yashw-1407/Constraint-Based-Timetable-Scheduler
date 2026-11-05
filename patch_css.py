import re
with open('static/style.css', 'a', encoding='utf-8') as f:
    f.write('''
/* Unified Timetable Grid */
.timetable-grid {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
    font-size: 14px;
    table-layout: fixed;
}
.timetable-grid th, .timetable-grid td {
    border: 1px solid #ccc;
    padding: 8px;
    text-align: center;
    vertical-align: middle;
}
.timetable-grid th {
    background-color: #f0f4f8;
    color: #333;
}
.timetable-grid .break-col {
    background-color: #e2e8f0;
    width: 60px;
}
.timetable-grid .break-cell {
    background-color: #e2e8f0;
}
.timetable-grid .cell-theory {
    background-color: #e6f7ff;
}
.timetable-grid .cell-lab {
    background-color: #f6ffed;
}
.timetable-grid .cell-empty {
    color: #aaa;
}

@media print {
    body * {
        visibility: hidden;
    }
    #view-content, #view-content * {
        visibility: visible;
    }
    #view-content {
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
    }
    @page {
        size: A4 landscape;
        margin: 1cm;
    }
    .timetable-grid {
        width: 100%;
        font-size: 11px;
    }
    .timetable-grid th, .timetable-grid td {
        padding: 4px;
    }
}
''')
