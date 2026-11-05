"""Fix the _skipSummary flag in index.html"""
import re

path = r"c:\Users\yashw\Downloads\timetable-scheduler-02 - Copy - Copy\templates\index.html"
with open(path, 'r', encoding='utf-8') as f:
    txt = f.read()

# Insert the _skipSummary flag and update the click listener
old = "        // Flag: skip summary and go straight to generation (after user confirms)"
if old in txt:
    print("Flag already present, skipping.")
else:
    # Add flag after controls assignment
    txt = txt.replace(
        "        const controls  = document.querySelector('.generate-controls.card');",
        "        const controls  = document.querySelector('.generate-controls.card');\n\n        // Flag: skip summary and go straight to generation (after user confirms)\n        let _skipSummary = false;"
    )

    # Update the generate click listener to check the flag
    txt = txt.replace(
        "        btnGen && btnGen.addEventListener('click', async (e) => {\n            e.stopImmediatePropagation();",
        "        btnGen && btnGen.addEventListener('click', async (e) => {\n            // If confirmed, let the existing app.js listener run normally\n            if (_skipSummary) { _skipSummary = false; return; }\n\n            e.stopImmediatePropagation();"
    )

    # Update btnConf to set the flag
    txt = txt.replace(
        "            // Trigger the original generate button's default listener\n            document.getElementById('btn-generate').dispatchEvent(new MouseEvent('click', { bubbles: true }));",
        "            // Set flag so the capture listener passes through, then click\n            _skipSummary = true;\n            document.getElementById('btn-generate').dispatchEvent(new MouseEvent('click', { bubbles: true }));"
    )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(txt)
    print("Fixed: _skipSummary flag added to index.html")
