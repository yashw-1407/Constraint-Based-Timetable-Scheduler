import json

# Fix database
with open('database.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

for c in db['courses']:
    if c['id'] in ['C3A06', 'C3A07', 'C3A08', 'C3B06', 'C3B07', 'C3B08']:
        if 'lab_batches' in c and len(c['lab_batches']) == 0:
            if 'A' in c['section_id']:
                c['lab_batches'] = ['B3A1', 'B3A2']
            elif 'B' in c['section_id']:
                c['lab_batches'] = ['B3B1', 'B3B2']

with open('database.json', 'w', encoding='utf-8') as f:
    json.dump(db, f, indent=2)

# Fix app.js
with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

import re

# We need to manually populate lab_batches correctly in editItem.
# Find the editItem function.
edit_item_replacement = """    // Populate form fields
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
    }"""

js = re.sub(
    r"    // Populate form fields\s*for \(const key in item\) \{.*?\n        \}\n    \}",
    edit_item_replacement,
    js,
    flags=re.DOTALL
)

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(js)

print("Fixed edit bug and restored DB!")
