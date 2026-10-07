import re

with open('scheduler.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_warn = """        if theory_demand > theory_slots_avail:
            warnings.append("WARNING: NOT ENOUGH theory room capacity!")"""
            
new_warn = """        if generic_theory_demand > theory_slots_avail:
            warnings.append("WARNING: NOT ENOUGH generic theory room capacity!")"""

code = code.replace(old_warn, new_warn)

with open('scheduler.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Fixed diagnose")
