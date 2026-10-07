# Constraint-Based Academic Timetable Scheduling Engine

A working prototype that generates academic timetables using **Constraint Satisfaction Problem (CSP) with Backtracking**. This is NOT a fake/static UI — the timetable is generated from input data using a real scheduling algorithm.

## Quick Start

```bash
# 1. Install dependencies
pip install flask==3.0.3

# 2. Run the application
cd timetable-scheduler
python app.py

# 3. Open in browser
# http://127.0.0.1:5000

# 4. Demo workflow:
#    Click "Load Demo Data" → Go to "Generate" tab → Click "Generate Timetable"
#    → Go to "Timetable Views" tab → Browse Master/Section/Faculty/Room views
```

## Project Structure

```
timetable-scheduler/
├── models.py            # Data models (dataclasses)
├── time_slots.py        # Dynamic time-slot generation
├── constraints.py       # Hard constraint checking functions
├── soft_constraints.py  # Soft constraint scoring (quality metrics)
├── scheduler.py         # CSP backtracking engine (CORE)
├── demo_data.py         # Built-in demonstration dataset
├── app.py               # Flask web application + REST API
├── requirements.txt     # Python dependencies
├── templates/
│   └── index.html       # Single-page frontend
└── static/
    ├── style.css         # Styling
    └── app.js            # Frontend JavaScript (vanilla, no frameworks)
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Browser (Frontend)                     │
│  index.html + style.css + app.js                        │
│  Tabs: Config | Rooms | Faculty | Sections | Courses    │
│        | Generate | Timetable Views                      │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API (JSON)
┌──────────────────────┴──────────────────────────────────┐
│                  Flask (app.py)                           │
│  Routes: /api/config, /api/rooms, /api/faculty,          │
│          /api/sections, /api/courses, /api/generate,     │
│          /api/timetable/*, /api/validation,               │
│          /api/load-demo, /api/clear                      │
├──────────────────────────────────────────────────────────┤
│              SchedulingEngine (scheduler.py)              │
│  CSP Backtracking with MRV + Value Ordering              │
├──────────────────────────────────────────────────────────┤
│  time_slots.py │ constraints.py │ soft_constraints.py    │
│  models.py     │ demo_data.py                            │
└──────────────────────────────────────────────────────────┘
```

## Algorithm: CSP with Backtracking

### CSP Formulation

| CSP Element   | Timetable Mapping |
|---------------|-------------------|
| **Variables** | Each required class meeting (ScheduleSession). E.g., "Data Structures for section 3A, session 1 of 4" |
| **Domains**   | Cartesian product of (day × time_slot × room) for each session |
| **Constraints** | Hard constraints that must ALL be satisfied |

### Hard Constraints

1. **Section conflict**: A section cannot have two classes at the same time
2. **Faculty conflict**: A faculty member cannot teach two classes simultaneously
3. **Room conflict**: A room cannot host two classes at the same time
4. **Room suitability**: Labs must use lab rooms, theory must use theory rooms
5. **Room capacity**: Room capacity ≥ section strength (when both specified)
6. **Lab consecutive slots**: Multi-period labs must occupy temporally adjacent slots (no break between them)

### Soft Constraints (Quality Metrics, scored out of 100)

1. **Subject distribution** (20 pts): Spread subjects across different days
2. **No same subject same day** (15 pts): Avoid teaching the same subject twice to a section on the same day
3. **Minimize student gaps** (15 pts): Reduce free periods between classes
4. **Faculty workload target** (15 pts): Keep faculty weekly hours near 20h
5. **Faculty daily balance** (10 pts): Even daily workload distribution
6. **Consecutive faculty limit** (15 pts): Avoid >3 consecutive classes for a faculty member
7. **Room utilization** (10 pts): Even usage across rooms

### Search Strategy

```
solve():
    1. Create sessions from courses
       - Theory: weekly_hours separate 1-slot sessions
       - Lab: 1 session of lab_duration_hours consecutive slots
    
    2. Order sessions by MRV heuristic:
       - Labs first (larger duration = more constrained)
       - Then by number of suitable rooms (fewer = more constrained)
    
    3. Call _backtrack(0)

_backtrack(idx):
    if idx == len(sessions): return True   # All assigned!
    
    session = sessions[idx]
    domain = all valid (day, slot, room) combinations
    
    # Filter by hard constraints
    viable = [(score, day, slot, room) for each domain value
              where all hard constraints pass]
    
    # Sort by soft preference (better options first)
    viable.sort(descending by score)
    
    for each (day, slot, room) in viable:
        assign(session, day, slot, room)
        if _backtrack(idx + 1): return True
        unassign(session)  # Backtrack
    
    return False  # No valid assignment
```

### Complexity Analysis

- **Worst case**: O(d^n) where d = domain size, n = number of sessions
- **Practical**: MRV heuristic + value ordering dramatically prunes the search tree
- **Demo dataset**: 56 sessions solved in ~20ms with 0 backtracks
- **Safety limits**: MAX_BACKTRACKS = 500,000 and MAX_TIME_SECONDS = 30

### Why NOT Other Algorithms

| Algorithm | Why Not Used |
|-----------|-------------|
| Round Robin, SJF, FCFS, Priority Scheduling | CPU scheduling algorithms — wrong problem domain |
| AI/ML | Not required; CSP is a classical, explainable approach |
| Genetic Algorithm | More complex, harder to explain, non-deterministic |
| Integer Linear Programming | Requires external solver library |

CSP with backtracking is the standard academic approach for constraint satisfaction problems. It is:
- **Correct**: Guaranteed to find a solution if one exists
- **Explainable**: Every step can be traced and justified
- **Complete**: Will exhaust the entire search space if no solution exists

## Data Model

### WorkingConfig
Working hours configuration with dynamic time-slot generation.

### Room
Has ID, name, type (THEORY_ROOM or LAB), capacity, and optional category.

### Faculty
ID and name. Faculty assignment is INPUT — the scheduler does NOT decide who teaches.

### Section
ID, name, semester, division, strength.

### Course
Links a subject to a section and faculty. Key fields:
- `course_type`: THEORY or LAB
- `weekly_hours`: For theory = number of 1-hour sessions/week. For lab = 1.
- `lab_duration_hours`: Explicit duration (e.g., 2 hours). NOT derived from credits.

### Time Slot Generation
Slots are NOT hardcoded. They are dynamically derived from:
- Working start/end time
- Slot duration
- Break periods
- Lunch period

Algorithm walks from start_time to end_time, skipping any blocked periods.

## Demo Dataset

- **Semesters**: 3rd, 5th
- **Sections**: 3A, 3B, 5A, 5B
- **Faculty**: 8 members (shared across sections for realistic constraints)
- **Rooms**: 4 theory rooms + 2 labs
- **Courses**: 4 theory subjects + 1 lab per section = 20 courses → 56 sessions

## Views

1. **Master Timetable**: All scheduled entries in a flat table
2. **Section View**: Day × Time grid for one section
3. **Faculty View**: Day × Time grid for one faculty member
4. **Room View**: Day × Time grid for one room
5. **Validation Report**: Post-generation hard constraint verification

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/config` | Get/set working configuration |
| GET/POST | `/api/rooms` | List/add rooms |
| DELETE | `/api/rooms/<id>` | Delete a room |
| GET/POST | `/api/faculty` | List/add faculty |
| DELETE | `/api/faculty/<id>` | Delete a faculty member |
| GET/POST | `/api/sections` | List/add sections |
| DELETE | `/api/sections/<id>` | Delete a section |
| GET/POST | `/api/courses` | List/add courses |
| DELETE | `/api/courses/<id>` | Delete a course |
| GET | `/api/time-slots` | Get dynamically generated time slots |
| POST | `/api/generate` | Run the scheduler |
| GET | `/api/timetable/master` | Master timetable view |
| GET | `/api/timetable/section/<id>` | Section grid view |
| GET | `/api/timetable/faculty/<id>` | Faculty grid view |
| GET | `/api/timetable/room/<id>` | Room grid view |
| GET | `/api/validation` | Post-generation validation |
| POST | `/api/load-demo` | Load built-in demo dataset |
| POST | `/api/clear` | Clear all data |

## Tech Stack

- **Backend**: Python 3, Flask 3.0.3
- **Frontend**: Vanilla HTML/CSS/JavaScript (no frameworks)
- **Algorithm**: CSP with Backtracking
- **Storage**: In-memory (no database)
- **Dependencies**: Flask only

## Known Limitations

### IMPLEMENTED
- Hard constraint enforcement (section, faculty, room, suitability, capacity, consecutive)
- Soft constraint scoring (7 metrics)
- Dynamic time-slot generation
- Multiple timetable views
- Post-generation validation
- Demo data loading

### NOT IMPLEMENTED (Future Scope)
- Database persistence
- User authentication
- Elective/optional courses
- Multi-batch lab sessions
- Export to PDF/Excel
- Multiple timetable comparison
- Manual session override/pinning
- Undo/redo
