with open('scheduler.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace("variants.sort(key=lambda x: -x['soft_score']['total'])", "variants.sort(key=lambda x: -x['soft_score']['total_score'])")

with open('scheduler.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('scheduler.py patched')
