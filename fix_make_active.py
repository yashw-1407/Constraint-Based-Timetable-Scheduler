import re

with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Replace the click trigger with a UI re-render function
old_make_active = """async function makeActive(index) {
    try {
        await fetch('/api/timetable/variant/' + index, { method: 'POST' });
        // Refresh the list to show new active
        document.getElementById('btn-generate-multiple').click();
    } catch (e) {
        showNotification('Failed to set active alternative', 'error');
    }
}"""

new_make_active = """let lastGeneratedResult = null; // store globally when generated

async function makeActive(index) {
    try {
        await fetch('/api/timetable/variant/' + index, { method: 'POST' });
        if (lastGeneratedResult) {
            lastGeneratedResult.active_variant_index = index;
            renderAlternativesList(lastGeneratedResult);
        }
    } catch (e) {
        showNotification('Failed to set active alternative', 'error');
    }
}

function renderAlternativesList(res) {
    const altList = document.getElementById('alternatives-list');
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
}
"""

js = js.replace(old_make_active, new_make_active)

# Update the listener to use renderAlternativesList and save lastGeneratedResult
old_listener_body = """        if (res.status === 'success' || res.status === 'partial') {
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
            
        } else {"""

new_listener_body = """        if (res.status === 'success' || res.status === 'partial') {
            lastGeneratedResult = res;
            statusText.textContent = `Generated ${res.generated} unique feasible timetables out of ${res.requested} requested.`;
            statusText.style.color = 'var(--success)';
            renderAlternativesList(res);
        } else {"""

js = js.replace(old_listener_body, new_listener_body)

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(js)
print("JS fixed for makeActive!")
