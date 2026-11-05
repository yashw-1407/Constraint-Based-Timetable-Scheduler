import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

new_gen_tab = """<!-- Generate Tab -->
        <section id="generate" class="tab-content">
            <h2>Generate Timetable</h2>
            <div class="generate-controls">
                <button id="btn-generate" class="btn success" style="font-size: 16px; padding: 10px 20px;">Generate Single Timetable</button>
                <button id="btn-validate" class="btn" style="font-size: 16px; padding: 10px 20px;">Validate Configuration</button>
            </div>
            
            <div id="generate-status" style="margin-top: 20px; display: none;">
                <h3 id="gen-status-text"></h3>
                <div id="gen-score" style="background: #e8f5e9; padding: 15px; border-radius: 5px; margin-top: 10px; display: none;"></div>
                <div id="gen-diagnostics" style="background: #ffebee; padding: 15px; border-radius: 5px; margin-top: 10px; display: none; color: #d32f2f;"></div>
            </div>

            <hr style="margin: 30px 0; border: 0; border-top: 1px solid #ccc;">

            <h2>Generate Alternatives</h2>
            <div style="margin-bottom: 15px;">
                <label for="alt-count" style="display: block; margin-bottom: 5px;">Number of alternatives:</label>
                <select id="alt-count" style="padding: 8px; width: 150px; font-size: 16px;">
                    <option value="1">1</option>
                    <option value="3">3</option>
                    <option value="5" selected>5</option>
                    <option value="10">10</option>
                </select>
            </div>
            <button id="btn-generate-multiple" class="btn primary" style="font-size: 16px; padding: 10px 20px;">Generate Alternatives</button>
            
            <div id="gen-status" style="margin-top: 20px; display: none;">
                <h3 id="gen-status-text"></h3>
                <div id="gen-score" style="background: #e8f5e9; padding: 15px; border-radius: 5px; margin-top: 10px; display: none;"></div>
                <div id="gen-diagnostics" style="background: #ffebee; padding: 15px; border-radius: 5px; margin-top: 10px; display: none;"></div>
            </div>

            <hr style="margin: 30px 0; border: 0; border-top: 1px solid #ccc;">

            <h2>Generated Alternatives</h2>
            <div id="alternatives-list" style="display: flex; flex-direction: column; gap: 15px;">
                <p style="color: #666;">No alternatives generated yet.</p>
            </div>

            <div id="validation-report" style="display: none; margin-top: 20px;">
                <h3>Validation Report</h3>
                <div id="val-content"></div>
            </div>
        </section>"""

html = re.sub(r'<!-- Generate Tab -->.*?</section>', new_gen_tab, html, flags=re.DOTALL)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("HTML for generate tab patched successfully!")
