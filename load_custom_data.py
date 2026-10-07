import json
import csv
import io

raw_data = """faculty_id,name
F001,Nagaratna K
F002,Veena H
F003,Jyoti Patil
F004,Maheshgouda Patil
F005,Arundati A
F006,Megha Javoor
F007,Amit K
F008,Soumya Patil
F009,Mallikarjun Akki
F010,Pavan G
F011,Pavan
F012,Aishwarya N
F013,Sadaf S
F014,Shrushti N
F015,Sneha V
F016,Dheeraj K
F017,Shrishti G
F018,Pooja S
F019,Umadevi
F020,Narayan D G
room_id,name,type,capacity,category
R001,LHC201,LAB,35,
R002,LAB6,LAB,35,
R003,LHC306,THEORY_ROOM,70,
R004,LHC307,THEORY_ROOM,70,
R005,LHC301,THEORY_ROOM,70,
R006,LHC202,THEORY_ROOM,70,
R007,CLH310,LAB,70,
R008,CLH309,LAB,35,
section_id,name,semester,division,strength,home_room_id
S3A,3A,3,A,70,R005
S3B,3B,3,B,68,R006
S5A,5A,5,A,70,R003
S5B,5B,5,B,65,R004
batch_id,batch_name,section_id,strength
B3A1,A1,S3A,35
B3A2,A2,S3A,35
B3B1,B1,S3B,35
B3B2,B2,S3B,33
B5A1,A1,S5A,35
B5A2,A2,S5A,35
B5B1,B1,S5B,35
B5B2,B2,S5B,30
course_id,name,code,section_id,L,T,P,faculty_ids,room_type,required_room,lab_batches
C3A01,Discrete Mathematical Structures,26EMAB229,S3A,3,0,2,F001,THEORY_ROOM,,"B3A1,B3A2"
C3A02,Database Management System,26ECAC201,S3A,3,0,0,F003,THEORY_ROOM,,
C3A03,Design and Analysis of Algorithms,26ECAC202,S3A,3,0,0,F004,THEORY_ROOM,,
C3A04,Operating System Principles and Programming,26ECAC203,S3A,3,0,2,F005,THEORY_ROOM,,"B3A1,B3A2"
C3A05,Software Engineering,26ECAC204,S3A,3,0,0,F007,THEORY_ROOM,,
C3A06,Algorithms Lab,26ECAP201,S3A,0,0,3,F004,LAB,,"B3A1,B3A2"
C3A07,Database Applications Lab,26ECAP202,S3A,0,0,3,F003,LAB,,"B3A1,B3A2"
C3A08,Web Technologies Lab,26ECAP203,S3A,0,0,3,F013,LAB,R008,"B3A1,B3A2"
C3B01,Discrete Mathematical Structures,26EMAB229,S3B,3,0,2,F001,THEORY_ROOM,,"B3B1,B3B2"
C3B02,Database Management System,26ECAC201,S3B,3,0,0,F003,THEORY_ROOM,,
C3B03,Design and Analysis of Algorithms,26ECAC202,S3B,3,0,0,F010,THEORY_ROOM,,
C3B04,Operating System Principles and Programming,26ECAC203,S3B,3,0,2,F005,THEORY_ROOM,,"B3B1,B3B2"
C3B05,Software Engineering,26ECAC204,S3B,3,0,0,F007,THEORY_ROOM,,
C3B06,Algorithms Lab,26ECAP201,S3B,0,0,3,F010,LAB,,"B3B1,B3B2"
C3B07,Database Applications Lab,26ECAP202,S3B,0,0,3,F003,LAB,,"B3B1,B3B2"
C3B08,Web Technologies Lab,26ECAP203,S3B,0,0,3,F009,LAB,R008,"B3B1,B3B2"
C5A01,Deep Learning,26ECAC302,S5A,4,0,0,F015,THEORY_ROOM,,
C5A02,Cloud Computing,26ECAC301,S5A,3,0,2,F016,THEORY_ROOM,,"B5A1,B5A2"
C5A03,Parallel and GPU Computing,26ECAC304,S5A,3,0,2,F017,THEORY_ROOM,,"B5A1,B5A2"
C5A04,Cryptography and Network Security,26ECAC305,S5A,3,0,2,F018,THEORY_ROOM,,"B5A1,B5A2"
C5A05,Deep Learning Lab,26ECAP301,S5A,0,0,3,F015,LAB,,"B5A1,B5A2"
C5A06,Mini Project,22ECAW301,S5A,0,0,3,F018,LAB,R007,
C5A08,AI-Assisted Software Development,26ECSE346,S5A,1,0,3,F020,LAB,R007,
C5B01,Deep Learning,26ECAC302,S5B,4,0,0,F019,THEORY_ROOM,,
C5B02,Cloud Computing,26ECAC301,S5B,3,0,2,F016,THEORY_ROOM,,"B5B1,B5B2"
C5B03,Parallel and GPU Computing,26ECAC304,S5B,3,0,2,F017,THEORY_ROOM,,"B5B1,B5B2"
C5B04,Cryptography and Network Security,26ECAC305,S5B,3,0,2,F018,THEORY_ROOM,,"B5B1,B5B2"
C5B05,Deep Learning Lab,26ECAP301,S5B,0,0,3,F019,LAB,,"B5B1,B5B2"
C5B06,Mini Project,22ECAW301,S5B,0,0,3,F019,LAB,R007,
C5B08,AI-Assisted Software Development,26ECSE346,S5B,1,0,3,F008,LAB,R007,"""

def parse_blocks(raw):
    lines = raw.strip().split('\n')
    blocks = {}
    current_header = None
    current_lines = []
    
    for line in lines:
        if not line: continue
        if line.startswith('faculty_id') or line.startswith('room_id') or line.startswith('section_id') or line.startswith('batch_id') or line.startswith('course_id'):
            if current_header:
                blocks[current_header] = current_lines
            current_header = line
            current_lines = [line]
        else:
            current_lines.append(line)
            
    if current_header:
        blocks[current_header] = current_lines
        
    return blocks

blocks = parse_blocks(raw_data)

faculty_list = []
for row in csv.DictReader(blocks[[k for k in blocks.keys() if k.startswith('faculty_id')][0]]):
    faculty_list.append({"id": row['faculty_id'], "name": row['name']})

room_list = []
for row in csv.DictReader(blocks[[k for k in blocks.keys() if k.startswith('room_id')][0]]):
    room_list.append({
        "id": row['room_id'],
        "name": row['name'],
        "room_type": row['type'],
        "capacity": int(row['capacity']) if row['capacity'] else 0,
        "category": row.get('category', '')
    })

section_list = []
for row in csv.DictReader(blocks[[k for k in blocks.keys() if k.startswith('section_id')][0]]):
    section_list.append({
        "id": row['section_id'],
        "name": row['name'],
        "semester": int(row['semester']),
        "division": row['division'],
        "strength": int(row['strength']),
        "home_room_id": row.get('home_room_id', None)
    })

batch_list = []
for row in csv.DictReader(blocks[[k for k in blocks.keys() if k.startswith('batch_id')][0]]):
    batch_list.append({
        "id": row['batch_id'],
        "name": row['batch_name'],
        "section_id": row['section_id'],
        "strength": int(row['strength'])
    })

course_list = []
for row in csv.DictReader(blocks[[k for k in blocks.keys() if k.startswith('course_id')][0]]):
    course_list.append({
        "id": row['course_id'],
        "name": row['name'],
        "code": row['code'],
        "section_id": row['section_id'],
        "l": int(row['L']),
        "t": int(row['T']),
        "p": int(row['P']),
        "faculty_ids": [f.strip() for f in row['faculty_ids'].split(',')] if row.get('faculty_ids') else [],
        "room_type": row['room_type'],
        "required_room_id": row.get('required_room', None),
        "lab_batches": [b.strip() for b in row['lab_batches'].split(',')] if row.get('lab_batches') else []
    })

# load database.json to preserve config
with open('database.json', 'r') as f:
    db = json.load(f)

db['faculty'] = faculty_list
db['rooms'] = room_list
db['sections'] = section_list
db['batches'] = batch_list
db['courses'] = course_list

with open('database.json', 'w') as f:
    json.dump(db, f, indent=2)

print("Updated database.json successfully.")
