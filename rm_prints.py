with open('scheduler.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace('        if idx < 5: print(f"  Session {idx} viable choices: {len(viable)}")\n', '')
code = code.replace('            print(f"Attempt {attempt}: Seed={seed}, Feasible={result.get(\'status\') == \'success\'}")\n', '')
code = code.replace('                print(f"  Signature: {signature}")\n', '')

with open('scheduler.py', 'w', encoding='utf-8') as f:
    f.write(code)
