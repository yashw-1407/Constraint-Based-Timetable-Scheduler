with open('scheduler.py', 'r', encoding='utf-8') as f:
    code = f.read()

patch = """result = self.solve(seed=seed)
            print(f"Attempt {attempt}: Seed={seed}, Feasible={result.get('status') == 'success'}")
            if result.get('status') == 'success':
                assigns = list(self.assignments.values())
                signature = self._create_signature(assigns)
                print(f"  Signature: {signature}")"""

code = code.replace("result = self.solve(seed=seed)", patch)

with open('scheduler.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched!")
