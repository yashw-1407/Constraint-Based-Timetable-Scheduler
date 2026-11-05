import re

with open('static/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the missing backticks caused by powershell escaping
text = re.sub(r'let rRoom = .*?;', 'let rRoom = `<span>Room: ${a.room_name}</span>`;', text)
text = re.sub(r'let rFac = .*?;', 'let rFac = `<span>Faculty: ${facs}</span>`;', text)

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(text)
print('Fixed syntax error')
