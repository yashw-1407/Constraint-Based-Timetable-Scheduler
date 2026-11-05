import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix master timetable
code = code.replace("if not engine or not result or result.get('status') != 'success':", 
                    "if not engine or not result or result.get('status') not in ('success', 'partial'):")

# Fix /api/timetable/variant/<index> which might also have this
code = code.replace("if not engine or not result or result.get('status') != 'success':", 
                    "if not engine or not result or result.get('status') not in ('success', 'partial'):")

# Fix metadata
code = code.replace("if not result or result.get('status') != 'success':", 
                    "if not result or result.get('status') not in ('success', 'partial'):")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("app.py status checks patched!")
