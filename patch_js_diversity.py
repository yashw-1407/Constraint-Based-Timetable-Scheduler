import re

with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Update API call
old_fetch = """        const count = document.getElementById('alt-count').value;
        const res = await fetchJSON('/api/generate-multiple', { 
            method: 'POST',
            body: JSON.stringify({ count: count })
        });"""

new_fetch = """        const count = document.getElementById('alt-count').value;
        const divPct = document.getElementById('alt-diversity').value;
        const res = await fetchJSON('/api/generate-multiple', { 
            method: 'POST',
            body: JSON.stringify({ count: count, min_diversity_pct: divPct })
        });"""
js = js.replace(old_fetch, new_fetch)


# 2. Update status text for partial success
old_status = "statusText.textContent = `Generated ${res.generated} unique feasible timetables out of ${res.requested} requested.`;"
new_status = "statusText.textContent = `Generated ${res.generated} unique diverse feasible timetables out of ${res.requested} requested.`;"
js = js.replace(old_status, new_status)


# 3. Update the card HTML
old_card = """        let html = `
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
                    <button class="btn" onclick="document.querySelector('button[data-target=views]').click()">View</button>
                    ${!isActive ? `<button class="btn primary" onclick="makeActive(${idx})">Make Active</button>` : ''}
                </div>
            </div>
        `;"""

new_card = """        const divDisplay = alt.diversity_pct === 'Base' ? 'Base' : `${alt.diversity_pct}%`;
        const changedDisplay = alt.diversity_pct === 'Base' ? '' : `Changed: ${alt.changed_assignments}/${alt.stats.total_sessions} sessions &bull; `;
        
        let html = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h3 style="margin: 0 0 5px 0; font-size: 1.1em;">Alternative ${alt.alternative_id} ${isActive ? '<span style="font-size: 12px; background: var(--primary); color: white; padding: 2px 6px; border-radius: 4px; margin-left: 10px;">ACTIVE</span>' : ''}</h3>
                    
                    <div style="margin-top: 10px;">
                        ${alt.stats.total_sessions}/${alt.stats.total_sessions} sessions
                    </div>
                    <div style="margin-top: 5px; font-weight: bold;">
                        Soft Constraint Score: ${alt.soft_score.percentage}% (${alt.soft_score.total_score})
                    </div>
                    <div style="margin-top: 5px; color: #2c3e50;">
                        Diversity: ${divDisplay}
                    </div>
                    <div style="color: #666; font-size: 13px; margin-top: 5px;">
                        ${changedDisplay}Seed: ${alt.seed} &bull; Time: ${alt.stats.time_ms} ms &bull; Backtracks: ${alt.stats.backtracks}
                    </div>
                </div>
                <div style="display: flex; gap: 10px; margin-top: 5px;">
                    <button class="btn" onclick="document.querySelector('button[data-target=views]').click()">View</button>
                    ${!isActive ? `<button class="btn primary" onclick="makeActive(${idx})">Make Active</button>` : ''}
                </div>
            </div>
        `;"""

js = js.replace(old_card, new_card)

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(js)
print("app.js updated")

