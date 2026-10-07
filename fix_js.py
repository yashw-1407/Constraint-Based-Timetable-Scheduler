with open('static/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Replace the bad onclick
js = js.replace("""onclick="document.querySelector('.tab-btn[data-target=\\'views\\']').click()\"""", """onclick="document.querySelector('button[data-target=views]').click()\"""")

with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(js)
print("Done")
