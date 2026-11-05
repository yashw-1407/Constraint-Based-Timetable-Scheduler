with open('scheduler.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace('viable.sort(key=lambda x: -x[0])', 'viable.sort(key=lambda x: -x[0])\n        if idx < 5: print(f"  Session {idx} viable choices: {len(viable)}")')

with open('scheduler.py', 'w', encoding='utf-8') as f:
    f.write(code)
