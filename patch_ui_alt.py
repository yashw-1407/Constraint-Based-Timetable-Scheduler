import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

new_gen_tab = """        <!-- Generate Tab -->
        <section id="generate" class="tab-content">
            <h2>Generate Timetable</h2>
            <button id="btn-generate" class="btn success" style="font-size: 16px; padding: 10px 20px;">Generate Single Timetable</button>
            <button id="btn-validate" class="btn" style="font-size: 16px; padding: 10px 20px;">Validate Configuration</button>

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
            
            <div id="validation-report" style="margin-top: 30px;"></div>
        </section>"""

# Replace the whole generate section
html = re.sub(r'<!-- Generate Tab -->.*?<div id="validation-report" style="margin-top: 30px;"></div>\n\s*</section>', new_gen_tab, html, flags=re.DOTALL)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("HTML for generate tab patched!")

# Update app.js
with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Add event listener for generate multiple and render list
js_multiple = """
document.getElementById('btn-generate-multiple')?.addEventListener('click', async () => {
    const statusDiv = document.getElementById('gen-status');
    const statusText = document.getElementById('gen-status-text');
    const scoreDiv = document.getElementById('gen-score');
    const diagDiv = document.getElementById('gen-diagnostics');
    const altList = document.getElementById('alternatives-list');
    
    statusDiv.style.display = 'block';
    statusText.textContent = 'Generating alternatives... Please wait';
    statusText.style.color = '';
    scoreDiv.style.display = 'none';
    diagDiv.style.display = 'none';
    altList.innerHTML = '<p style="color: #666;">Generating...</p>';
    
    try {
        const count = document.getElementById('alt-count').value;
        const res = await fetchJSON('/api/generate-multiple', { 
            method: 'POST',
            body: JSON.stringify({ count: count })
        });
        
        if (res.status === 'success' || res.status === 'partial') {
            statusText.textContent = `Generated ${res.generated} unique feasible timetables out of ${res.requested} requested.`;
            statusText.style.color = 'var(--success)';
            
            // Render alternatives
            altList.innerHTML = '';
            res.alternatives.forEach((alt, idx) => {
                const isActive = res.active_variant_index === idx;
                
                const card = document.createElement('div');
                card.style.border = isActive ? '2px solid var(--primary)' : '1px solid #ccc';
                card.style.padding = '15px';
                card.style.borderRadius = '8px';
                card.style.background = isActive ? '#f0f7ff' : '#fff';
                
                let html = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <h3 style="margin: 0 0 5px 0;">Alternative ${alt.alternative_id} ${isActive ? '<span style="font-size: 12px; background: var(--primary); color: white; padding: 2px 6px; border-radius: 4px; margin-left: 10px;">ACTIVE</span>' : ''}</h3>
                            <div style="color: #666; font-size: 14px;">
                                ${alt.stats.total_sessions}/${alt.stats.total_sessions} sessions &bull; 
                                Seed: ${alt.seed} &bull; 
                                Time: ${alt.stats.time_ms}ms &bull; 
                                Backtracks: ${alt.stats.backtracks}
                            </div>
                            <div style="margin-top: 10px; font-weight: bold;">
                                Soft Constraint Score: ${alt.soft_score.total_score} (${alt.soft_score.percentage}%)
                            </div>
                        </div>
                        <div style="display: flex; gap: 10px;">
                            <button class="btn" onclick="document.querySelector('.tab-btn[data-target=\\'views\\']').click()">View</button>
                            ${!isActive ? `<button class="btn primary" onclick="makeActive(${idx})">Make Active</button>` : ''}
                        </div>
                    </div>
                `;
                card.innerHTML = html;
                altList.appendChild(card);
            });
            
        } else {
            statusText.textContent = `Generation Failed (Infeasible)`;
            statusText.style.color = 'var(--danger)';
            diagDiv.style.display = 'block';
            diagDiv.innerHTML = `<strong>Error:</strong> ${res.message}<br><pre>${res.diagnostics}</pre>`;
            altList.innerHTML = '<p style="color: #666;">No alternatives to display.</p>';
        }
    } catch (e) {
        statusText.textContent = 'Error: ' + e.message;
        statusText.style.color = 'var(--danger)';
    }
});

async function makeActive(index) {
    try {
        await fetch('/api/timetable/variant/' + index, { method: 'POST' });
        // Refresh the list to show new active
        document.getElementById('btn-generate-multiple').click();
    } catch (e) {
        showNotification('Failed to set active alternative', 'error');
    }
}
"""

if 'btn-generate-multiple' not in js:
    js += '\n' + js_multiple
    with open('static/app.js', 'w', encoding='utf-8') as f:
        f.write(js)
    print("JS patched!")

