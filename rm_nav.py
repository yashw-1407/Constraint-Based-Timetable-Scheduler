import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace using regex
pattern = re.compile(r'<div id="variant-navigator".*?</div>\n\s*</div>\n\s*</div>\n', re.DOTALL)
html = pattern.sub('', html)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Removed from HTML")
