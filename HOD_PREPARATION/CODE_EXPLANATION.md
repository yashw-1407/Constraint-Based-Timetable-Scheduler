# Codebase Walkthrough — CampusGrid
## Line-by-Line Technical Explanation for College Students

---

### File 1: `models.py` (Domain Data Structures)

#### 1. What is its purpose?
In Python, instead of passing messy dictionaries with keys that could be misspelled (like `"room_nam"` vs `"room_name"`), `models.py` defines **clean, strongly-typed domain classes** using Python's `@dataclass`.

#### 2. Why do we need it?
Every part of our application — the database, the solver, the Excel parser, and the web routes — needs to agree on what a "Room", a "Course", or a "TimeSlot" looks like. `models.py` is the single source of truth for our project's data vocabulary.

#### 3. Core Data Classes Explained

| Class Name | Attributes | Real-Life College Meaning |
| :--- | :--- | :--- |
| `WorkingConfig` | `working_days`, `start_time`, `end_time`, `slot_duration_minutes`, `breaks`, `lunch_start`, `lunch_end` | The college calendar rules (e.g. 9:00 AM to 5:00 PM, 60 min slots, lunch from 1:00 PM to 2:00 PM). |
| `Room` | `id`, `name`, `room_type`, `capacity`, `category` | A physical space (`THEORY_ROOM` or `LAB`) with seating capacity. |
| `Faculty` | `id`, `name` | A teacher in the department. |
| `Section` | `id`, `name`, `semester`, `division`, `strength`, `home_room_id` | A student classroom group, such as 3rd Semester Division A (60 students). |
| `Batch` | `id`, `name`, `section_id`, `strength`, `home_room_id` | A subgroup for practical labs (e.g. Section 3A divided into Batch A1 and Batch A2 of 30 students each). |
| `Course` | `id`, `name`, `code`, `section_id`, `l`, `t`, `p`, `faculty_ids`, `assistant_faculty_ids`, `room_type`, `required_room_id`, `lab_batches` | A subject syllabus. Notice `l` (Lectures), `t` (Tutorials), `p` (Practicals) credit hours! |
| `TimeSlot` | `index`, `start_time`, `end_time` | A discrete period on the timetable (e.g., Slot 0 = 09:00–10:00). |
| `ScheduleSession` | `id`, `course_id`, `faculty_ids`, `room_type`, `duration_slots`, `batch_id` | The atomic scheduling unit (a single class event to be placed on the timetable). |
| `Assignment` | `session_id`, `day`, `start_slot_index`, `room_id` | A completed placement decision: Session X is scheduled on Monday at Slot 1 in Room 101. |

#### 4. Important Code Snippet

```python
@dataclass
class Course:
    id: str
    name: str
    code: str
    section_id: str
    l: float    # Theory Lecture hours per week
    t: float    # Tutorial hours per week
    p: float    # Practical / Lab hours per week
    faculty_ids: List[str] = field(default_factory=list)
    assistant_faculty_ids: List[str] = field(default_factory=list)
    room_type: str = RoomType.THEORY_ROOM
    required_room_id: Optional[str] = None
    lab_batches: List[str] = field(default_factory=list)
```
*Why this is clever*: Real colleges use the L-T-P model (e.g., L=3, T=1, P=2). Instead of forcing the user to manually enter 5 separate lecture entries and 2 lab entries, our system automatically expands these three numbers into individual sessions!

---

### File 2: `scheduler.py` (The Scheduling Engine)

#### 1. What is its purpose?
This is the brain of the entire project. It contains the **Constraint Satisfaction Problem (CSP)** backtracking algorithm that takes all classes, teachers, rooms, and time slots and figures out a conflict-free schedule.

#### 2. Key Methods in `SchedulingEngine`

- `__init__(self, config, courses, rooms, faculty_list, sections, batches=None)`:
  Initializes lookup maps (`rooms_by_id`, `faculty_by_id`, `sections_by_id`, `batches_by_id`), generates the daily `TimeSlot` periods, and calls `_create_sessions(courses)`.

- `_create_sessions(courses)`:
  Splits each course into atomic `ScheduleSession` objects.
  - If a course has $L=3$, it creates 3 separate 1-hour theory sessions (`CS301_T0`, `CS301_T1`, `CS301_T2`).
  - If it has $P=2$, it creates a 2-hour practical session for each lab batch (`CS301_L0`, `CS301_L1`) with `duration_slots=2`.

- `_get_domain(session)`:
  Returns all legal candidate triplets: `(day, start_slot_index, room_id)`.
  It filters out impossible slots immediately! For instance, if a lab needs 2 consecutive hours, it rejects any slot that would run past the end of the day or cross the lunch break (`check_consecutive_slots`).

- `solve()`:
  Orders sessions using **MRV (Minimum Remaining Values)** and session duration (scheduling 2-hour lab sessions first, then the most constrained theory classes). Then calls `_backtrack(0)`.

- `_backtrack(idx)`:
  The recursive search function. Tries placing session `idx` into the best candidate slot. If it leads to a valid complete timetable, returns `True`. If all slots cause a conflict down the road, it unassigns and backtracks.

- `_score_candidate(session, day, start_slot_idx, room_id)`:
  The soft constraint heuristic. Scores potential placements so the algorithm tries pleasant slots first (e.g., earlier hours, balanced across days, no same subject twice in one day).

- `validate_timetable(...)`:
  An independent mathematical verification function that double-checks the final timetable against all hard constraints.

---

### File 3: `database.py` (SQLite Persistence Layer)

#### 1. What is its purpose?
Saves your college data to disk in `autoschedule.db` so you don't lose your work when the server stops or your computer restarts.

#### 2. Why do we need it?
Early prototypes kept data only in RAM. If the browser refreshed or the server restarted, everything disappeared. `database.py` provides relational SQLite persistence with tables for `config`, `rooms`, `faculty`, `sections`, `batches`, `courses`, `course_faculty`, `course_lab_batches`, `timetable_assignments`, and `timetable_metadata`.

#### 3. Important Functions
- `get_connection(db_path)`: Opens an SQLite connection with `PRAGMA foreign_keys = ON` and `row_factory = sqlite3.Row`.
- `init_db(db_path)`: Creates all tables and indexes if they do not already exist.
- `load_data(app_data, db_path)`: Reads all tables from SQLite and converts them into Python dataclass objects inside the `app_data` dictionary.
- `save_data(app_data, db_path)`: Takes the current in-memory `app_data` and writes it atomically into SQLite inside a database transaction (`with conn:`).

---

### File 4: `app.py` (Flask Web Controller)

#### 1. What is its purpose?
`app.py` is the conductor of the orchestra. It runs the HTTP web server, listens for requests from the browser, routes them to the appropriate Python functions, and sends back clean JSON responses.

#### 2. Key Code Block: Timetable Generation Endpoint

```python
@app.route('/api/generate', methods=['POST'])
def generate_timetable():
    # 1. Ensure required data exists
    if not app_data['config'] or not app_data['courses']:
        return jsonify({'error': 'Config and Courses are required to generate'}), 400

    # 2. Instantiate the CSP Scheduling Engine
    engine = SchedulingEngine(
        config=app_data['config'],
        courses=app_data['courses'],
        rooms=app_data['rooms'],
        faculty_list=app_data['faculty'],
        sections=app_data['sections'],
        batches=app_data['batches']
    )

    # 3. Solve the schedule
    result = engine.solve()

    # 4. Save state and persist to SQLite
    app_data['engine'] = engine
    app_data['result'] = result
    save_data(app_data)

    return jsonify(result)
```

---

### File 5: `excel_import.py` (Excel Import & Export)

#### 1. What is its purpose?
Allows colleges to input their timetable data in bulk using Microsoft Excel (`.xlsx`) instead of typing hundreds of entries into web forms one by one.

#### 2. Important Functions:
- `parse_excel(filepath)`: Reads 5 worksheets (`Faculty`, `Rooms`, `Sections`, `Batches`, `Courses`), normalizes column names (ignoring capitalization and extra spaces), parses data types, verifies foreign references, and returns structured objects.
- `generate_template(filepath, prefill_user_data=True)`: Generates a professionally styled Excel workbook with colored header rows and sample data so users know exactly what format to fill.

---

### File 6: `demo_data.py` (Test Scenarios)

#### 1. What is its purpose?
Provides instant, realistic test data so the project can be demonstrated or tested in seconds without needing manual data entry.

#### 2. Four Supported Scenarios:
1. `'single_section'`: 1 section, 4 faculty, 2 rooms, 5 courses (17 sessions). Perfect for a fast 2-millisecond demo.
2. `'standard'`: 4 sections (3A, 3B, 5A, 5B), 20 faculty, 8 rooms, 30 courses (68 sessions). Complete full-scale college schedule.
3. `'bottleneck'`: Severe room and faculty constraints. Tests how the algorithm copes with high constraint pressure.
4. `'infeasible'`: Deliberately requests lab sessions when 0 lab rooms exist. Demonstrates our system's intelligent diagnostic error reporting!

---

### File 7: `templates/index.html` & `static/app.js` (Frontend UI)

#### 1. Architecture:
- Single-Page Application (SPA): Tab-based interface (`Configuration`, `Rooms`, `Faculty`, `Sections`, `Courses`, `Import Excel`, `Generate`, `Timetable Views`).
- Zero Heavy Frameworks: No React, Vue, or Webpack build steps required. Runs directly in any modern web browser using standard ES6 JavaScript and CSS Grid.
- Real-Time Updates: Form submissions use `fetch()` asynchronous calls; notifications slide in dynamically; timetable grids render instantly from JSON.
