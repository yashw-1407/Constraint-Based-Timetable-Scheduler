import re

with open("static/app.js", "r", encoding="utf-8") as f:
    content = f.read()

# Populate course_assistant_faculty
populate_replacement = """        const facSelect = document.getElementById('course_faculty');
        facSelect.innerHTML = '<option value="">Select Faculty</option>';
        faculty.forEach(f => facSelect.innerHTML += `<option value="${f.id}">${f.name}</option>`);
        
        const asstFacSelect = document.getElementById('course_assistant_faculty');
        if (asstFacSelect) {
            asstFacSelect.innerHTML = '';
            faculty.forEach(f => asstFacSelect.innerHTML += `<option value="${f.id}">${f.name}</option>`);
        }"""
content = re.sub(
    r"const facSelect = document\.getElementById\('course_faculty'\);\s*facSelect\.innerHTML = '<option value=\"\">Select Faculty</option>';\s*faculty\.forEach\(f => facSelect\.innerHTML \+= `<option value=\"\$\{f\.id\}\">\$\{f\.name\}</option>`\);",
    populate_replacement,
    content
)

# Read course_assistant_faculty in submit
submit_replacement = """    const facSelect = document.getElementById('course_faculty');
    const facultyIds = Array.from(facSelect.selectedOptions).map(opt => opt.value).filter(val => val !== "");
    
    const asstFacSelect = document.getElementById('course_assistant_faculty');
    const assistantFacultyIds = asstFacSelect ? Array.from(asstFacSelect.selectedOptions).map(opt => opt.value).filter(val => val !== "") : [];"""
content = re.sub(
    r"const facSelect = document\.getElementById\('course_faculty'\);\s*const facultyIds = Array\.from\(facSelect\.selectedOptions\)\.map\(opt => opt\.value\);",
    submit_replacement,
    content
)

# Update payload for add course
payload_replacement = """        p: parseFloat(document.getElementById('course_p').value),
        faculty_ids: facultyIds,
        assistant_faculty_ids: assistantFacultyIds,"""
content = re.sub(
    r"p: parseFloat\(document\.getElementById\('course_p'\)\.value\),\s*faculty_ids: facultyIds,",
    payload_replacement,
    content
)

with open("static/app.js", "w", encoding="utf-8") as f:
    f.write(content)

print("Patched app.js")
