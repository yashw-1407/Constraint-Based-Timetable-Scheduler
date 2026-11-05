import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix rooms
code = re.sub(
    r"        @app\.route\('/api/rooms/<id>', methods=\['DELETE'\]\)\n *def delete_room\(id\):\n",
    "",
    code
)

# Fix sections
code = re.sub(
    r"        @app\.route\('/api/sections/<id>', methods=\['DELETE'\]\)\n *def delete_section\(id\):\n",
    "",
    code
)

# Fix batches
code = re.sub(
    r"        @app\.route\('/api/batches/<id>', methods=\['DELETE'\]\)\n *def delete_batch\(id\):\n",
    "",
    code
)

# Fix courses
code = re.sub(
    r"        @app\.route\('/api/courses/<id>', methods=\['DELETE'\]\)\n *def delete_course\(id\):\n",
    "",
    code
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Syntax errors removed!")
