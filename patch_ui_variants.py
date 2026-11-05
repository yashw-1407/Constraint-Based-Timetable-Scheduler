import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

nav_html = """
            <div id="variant-navigator" style="display: none; background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; align-items: center; justify-content: space-between;">
                <div>
                    <h3 style="margin: 0; color: #0d47a1;">Timetable Alternative <span id="var-current">1</span> of <span id="var-total">3</span></h3>
                    <div style="font-size: 13px; color: #1565c0; margin-top: 5px;">Quality Score: <strong id="var-score">0</strong></div>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button id="btn-var-prev" class="btn primary">◀ Previous Option</button>
                    <button id="btn-var-next" class="btn primary">Next Option ▶</button>
                </div>
            </div>
"""

if 'variant-navigator' not in html:
    html = html.replace('<h2>Timetable Views</h2>', '<h2>Timetable Views</h2>\n' + nav_html)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("HTML patched!")

# Patch app.js to fetch metadata and handle variant buttons
with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

variant_js = """
let currentVariantIndex = 0;
let totalVariants = 0;

async function loadVariantMetadata() {
    try {
        const res = await fetch('/api/timetable/metadata');
        if (!res.ok) {
            document.getElementById('variant-navigator').style.display = 'none';
            return;
        }
        const data = await res.json();
        
        if (data.num_variants > 1) {
            document.getElementById('variant-navigator').style.display = 'flex';
            currentVariantIndex = data.active_variant_index;
            totalVariants = data.num_variants;
            
            document.getElementById('var-current').textContent = currentVariantIndex + 1;
            document.getElementById('var-total').textContent = totalVariants;
            document.getElementById('var-score').textContent = data.active_score.total || 0;
            
            document.getElementById('btn-var-prev').disabled = currentVariantIndex === 0;
            document.getElementById('btn-var-next').disabled = currentVariantIndex === totalVariants - 1;
        } else {
            document.getElementById('variant-navigator').style.display = 'none';
        }
    } catch (e) {
        document.getElementById('variant-navigator').style.display = 'none';
    }
}

document.getElementById('btn-var-prev')?.addEventListener('click', async () => {
    if (currentVariantIndex > 0) await switchVariant(currentVariantIndex - 1);
});

document.getElementById('btn-var-next')?.addEventListener('click', async () => {
    if (currentVariantIndex < totalVariants - 1) await switchVariant(currentVariantIndex + 1);
});

async function switchVariant(index) {
    try {
        await fetch('/api/timetable/variant/' + index, { method: 'POST' });
        await loadVariantMetadata();
        
        // Refresh the active view
        const activeBtn = document.querySelector('.view-btn.active');
        if (activeBtn) {
            if (activeBtn.dataset.view === 'master') {
                await renderMasterView();
            } else {
                const selector = document.getElementById('view-selector');
                if (selector.value) {
                    if (activeBtn.dataset.view === 'section') await renderSectionView(selector.value);
                    else if (activeBtn.dataset.view === 'faculty') await renderFacultyView(selector.value);
                    else if (activeBtn.dataset.view === 'room') await renderRoomView(selector.value);
                }
            }
        }
    } catch (e) {
        showNotification('Failed to switch timetable variant', 'error');
    }
}
"""

if 'loadVariantMetadata' not in js:
    js += '\n' + variant_js

    # Inject loadVariantMetadata into the views tab initialization
    js = js.replace(
        """function loadTimetableViewsInit() {""",
        """function loadTimetableViewsInit() {\n    loadVariantMetadata();"""
    )
    
    with open('static/app.js', 'w', encoding='utf-8') as f:
        f.write(js)
    print("JS patched!")
