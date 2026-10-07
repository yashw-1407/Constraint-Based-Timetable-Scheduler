import re

with open('scheduler_trace.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add TRACE logic
trace_init = """    def __init__(self, config, courses, rooms, faculty_list, sections, batches=None):
        self.TRACE = True
        self.trace_logs = []"""
        
code = re.sub(r'    def __init__\(self, config: WorkingConfig, courses: List\[Course\], rooms: List\[Room\], faculty_list: List\[Faculty\], sections: List\[Section\], batches: List\[Batch\]=None\):', 
              trace_init + '\n' + r'    def __init__(self, config: WorkingConfig, courses: List[Course], rooms: List[Room], faculty_list: List[Faculty], sections: List[Section], batches: List[Batch]=None):', code)

# We can just write a separate script that imports scheduler and does the analysis externally and injects a few prints.
# That might be simpler than regex patching a huge file.
