import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Add diversity dropdown
old_div = """            <h2>Generate Alternatives</h2>
            <div style="margin-bottom: 15px;">
                <label for="alt-count" style="display: block; margin-bottom: 5px;">Number of alternatives:</label>
                <select id="alt-count" style="padding: 8px; width: 150px; font-size: 16px;">
                    <option value="1">1</option>
                    <option value="3">3</option>
                    <option value="5" selected>5</option>
                    <option value="10">10</option>
                </select>
            </div>"""
            
new_div = """            <h2>Generate Alternatives</h2>
            <div style="display: flex; gap: 20px; margin-bottom: 15px;">
                <div>
                    <label for="alt-count" style="display: block; margin-bottom: 5px;">Number of alternatives:</label>
                    <select id="alt-count" style="padding: 8px; width: 150px; font-size: 16px;">
                        <option value="1">1</option>
                        <option value="3">3</option>
                        <option value="5" selected>5</option>
                        <option value="10">10</option>
                    </select>
                </div>
                <div>
                    <label for="alt-diversity" style="display: block; margin-bottom: 5px;">Minimum Diversity:</label>
                    <select id="alt-diversity" style="padding: 8px; width: 150px; font-size: 16px;">
                        <option value="10">10%</option>
                        <option value="20">20%</option>
                        <option value="25" selected>25%</option>
                        <option value="30">30%</option>
                        <option value="40">40%</option>
                        <option value="50">50%</option>
                    </select>
                </div>
            </div>"""

html = html.replace(old_div, new_div)
with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("index.html updated")

