import re

with open('scheduler.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add backtrack limit
old_bt = """    def _backtrack(self, idx: int) -> bool:
        if idx == len(self.sessions):
            return True"""
            
new_bt = """    def _backtrack(self, idx: int) -> bool:
        if self.backtrack_count > 50000:
            return False
        if idx == len(self.sessions):
            return True"""
            
code = code.replace(old_bt, new_bt)
with open('scheduler.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Added backtrack limit")
