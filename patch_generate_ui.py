with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

old_block = """        if (res.status === 'success') {
            const stats = res.stats || {};
            statusText.textContent = `Timetable generated successfully! (${stats.total_sessions} sessions, ${stats.backtracks} backtracks, ${stats.time_ms}ms)`;
            statusText.style.color = 'var(--success)';
            scoreDiv.style.display = 'block';
            scoreDiv.innerHTML = `<strong>Soft Score: ${res.soft_score.percentage}%</strong><br>` + 
                Object.entries(res.soft_score.details).map(([k,v]) => `${k}: ${v}`).join('<br>');
        } else {"""

new_block = """        if (res.status === 'success') {
            const bestVariant = res.variants && res.variants.length > 0 ? res.variants[res.active_variant_index || 0] : res;
            const stats = bestVariant.stats || {};
            statusText.textContent = `Timetable generated successfully! (${stats.total_sessions} sessions, ${stats.backtracks} backtracks, ${stats.time_ms}ms)`;
            statusText.style.color = 'var(--success)';
            scoreDiv.style.display = 'block';
            
            let detailsHtml = '';
            if (bestVariant.soft_score && bestVariant.soft_score.details) {
                detailsHtml = Object.entries(bestVariant.soft_score.details)
                    .map(([k,v]) => `${v.description || k}: <strong>${v.score}/${v.max}</strong>`)
                    .join('<br>');
            }
            scoreDiv.innerHTML = `<strong>Soft Score: ${bestVariant.soft_score ? bestVariant.soft_score.percentage : 0}%</strong><br>` + detailsHtml;
        } else {"""

js = js.replace(old_block, new_block)

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(js)

print("app.js generation success handler patched!")
