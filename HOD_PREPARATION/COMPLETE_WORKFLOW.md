# Complete Application Workflow — CampusGrid
## End-to-End Execution Traces from Browser Click to Database

---

### Step 1: User Opens the Application in the Browser

```
User navigates to http://127.0.0.1:5001
```

```mermaid
sequenceDiagram
    autonumber
    Browser->>Flask: GET /
    Flask-->>Browser: 200 OK (templates/index.html)
    Browser->>Flask: GET /static/style.css
    Flask-->>Browser: 200 OK (style.css)
    Browser->>Flask: GET /static/app.js
    Flask-->>Browser: 200 OK (app.js)
    Note over Browser: DOMContentLoaded Event Fires
    Browser->>Flask: GET /api/config
    Flask-->>Browser: Returns working_days, start_time, end_time, slot_duration, lunch
    Browser->>Flask: GET /api/summary
    Flask-->>Browser: Returns {rooms: 8, faculty: 20, sections: 4, courses: 30, generated: true}
    Note over Browser: UI populates header badge "System Active" and fills Configuration tab
```

1. Browser requests `http://127.0.0.1:5001`.
2. Flask route `@app.route('/')` serves `index.html`.
3. The browser parses HTML and pulls `static/style.css` and `static/app.js`.
4. Inside `app.js`, initialization functions trigger:
   - `loadConfig()`: Calls `GET /api/config` to populate working hours forms.
   - `fetchSummary()`: Calls `GET /api/summary` to refresh dashboard counts.
   - Sets the active tab to `Configuration`.

---

### Step 2: User Loads Demo Data

```
User selects "Standard Scenario" dropdown and clicks "Load Demo Data"
```

```mermaid
sequenceDiagram
    autonumber
    User->>Browser: Selects "Standard" & clicks "Load Demo Data"
    Browser->>Flask: POST /api/load-demo {scenario: "standard"}
    Note over Flask: app.py calls demo_data.get_demo_data('standard')
    Note over Flask: Populates app_data dict with 8 rooms, 20 faculty, 4 sections, 30 courses
    Flask->>DB: database.save_data(app_data)
    Note over DB: Atomically commits all rows to autoschedule.db
    Flask-->>Browser: 200 OK {status: "success", summary: {...}}
    Browser->>Browser: showNotification("Demo data loaded successfully")
    Browser->>Flask: GET /api/rooms, GET /api/faculty, GET /api/sections, GET /api/courses
    Browser-->>User: Tables instantly refresh with loaded courses, teachers, and rooms
```

1. Browser fires `fetchJSON('/api/load-demo', {method: 'POST', body: JSON.stringify({scenario: 'standard'})})`.
2. `app.py` invokes `get_demo_data('standard')` from `demo_data.py`.
3. `get_demo_data()` returns pure Python dataclasses for 8 classrooms/labs, 20 faculty, 4 sections, and 30 courses.
4. `database.save_data(app_data)` updates `autoschedule.db` atomically inside a thread lock.
5. Flask responds with `200 OK`. The client UI displays a green success toast and refreshes all table views.

---

### Step 3: User Adds or Edits Academic Information

```
User clicks "Courses" tab -> Fills form (L=3, T=0, P=2, selects Dr. Sharma, selects Lab 1) -> Clicks "Save Course"
```

1. Browser gathers form inputs and submits `POST /api/courses`.
2. `app.py` validates required fields (`code`, `name`, `section_id`, `l`, `t`, `p`).
3. Instantiates `Course` dataclass and appends it to `app_data['courses']`.
4. Calls `save_data(app_data)` to write changes immediately to SQLite.
5. Returns `201 Created` with the newly assigned course id.
6. `app.js` updates the Courses table and updates the dependency dropdowns in real time.

---

### Step 4: User Imports Timetable Data via Excel

```
User downloads template -> Enters data in Excel -> Uploads timetable.xlsx
```

```mermaid
sequenceDiagram
    autonumber
    User->>Browser: Selects .xlsx file & clicks "Upload and Import"
    Browser->>Flask: POST /api/import-excel (multipart/form-data)
    Note over Flask: Saves uploaded file to temporary path
    Flask->>ExcelParser: excel_import.parse_excel(temp_path)
    Note over ExcelParser: Reads 5 worksheets: Faculty, Rooms, Sections, Batches, Courses
    Note over ExcelParser: Normalizes headers & validates foreign key references
    ExcelParser-->>Flask: Returns parsed domain dataclasses + error list
    Note over Flask: Overwrites app_data with imported entities
    Flask->>DB: database.save_data(app_data)
    Note over Flask: Deletes temp uploaded file
    Flask-->>Browser: 200 OK {status: "success", imported: {rooms: 8, faculty: 20, ...}}
    Browser-->>User: Displays green success banner and refreshes all tables
```

1. Browser sends `.xlsx` file via `FormData` to `/api/import-excel`.
2. `excel_import.py` opens workbook using OpenPyXL (`data_only=True`).
3. Validates that all 5 sheets exist and verifies references (e.g., that courses reference valid faculty IDs and section IDs).
4. Returns parsed `Room`, `Faculty`, `Section`, `Batch`, and `Course` lists.
5. `save_data(app_data)` persists the imported college structure to `autoschedule.db`.

---

### Step 5: User Clicks "Generate Timetable"

```
User opens "Generate" tab and clicks the blue "Generate Timetable" button
```

```mermaid
sequenceDiagram
    autonumber
    User->>Browser: Clicks "Generate Timetable"
    Browser->>Browser: Show loading spinner / disable button
    Browser->>Flask: POST /api/generate
    Note over Flask: Checks prerequisites (Config and Courses exist)
    Note over Flask: Instantiates SchedulingEngine(config, courses, rooms, ...)
    Note over Flask: Calls engine.solve()
    Note over Solver: 1. _create_sessions(): Splits 30 courses into 68 sessions
    Note over Solver: 2. Sorts sessions: (-duration_slots, MRV domain_size)
    Note over Solver: 3. Runs recursive _backtrack(0)
    Note over Solver: 4. Evaluates soft constraints: compute_soft_score()
    Solver-->>Flask: Returns status='success', 68 assignments, stats, soft_score
    Flask->>DB: save_data(app_data) (Saves assignments to timetable_assignments table)
    Flask-->>Browser: JSON response {status: "success", stats: {...}, soft_score: {...}}
    Browser->>Browser: Hide spinner, render Stats cards (Time: 34ms, Backtracks: 0)
    Browser->>Browser: Render Soft Score Breakdown (75.0% Quality Score)
    Browser->>Flask: GET /api/validation
    Flask-->>Browser: Returns {valid: true, conflicts: []}
    Browser-->>User: Displays "Audit Passed: 0 Conflicts Detected"
```

1. Browser displays a loading spinner and calls `POST /api/generate`.
2. `SchedulingEngine` decomposes all courses into discrete `ScheduleSession` units based on L-T-P.
3. Sessions are sorted so the hardest items (multi-hour labs and sessions with fewest free slots) are placed first.
4. `_backtrack(0)` finds a mathematically proven conflict-free placement across all working days and rooms.
5. `compute_soft_score()` calculates the 7 quality metrics (0–100%).
6. `save_data()` writes the resulting timetable assignments to `autoschedule.db`.
7. `app.js` updates the KPI cards (execution time, backtracks, total sessions, soft score).
8. Immediately calls `/api/validation` to run an independent audit and verify 0 conflicts!

---

### Step 6: User Views the Timetable Across Different Dimensions

```
User navigates to "Timetable Views" tab
```

The application provides **4 distinct perspectives** on the same underlying schedule:

#### 1. Master View (`/api/timetable/master`)
- Displays all scheduled sessions across the entire department in a flat, sortable table.
- Columns: Day, Time, Section, Course Name, Type, Faculty, Room.

#### 2. By Section View (`/api/timetable/section/<section_id>`)
- User selects Section (e.g. `Section 3A`).
- The server constructs a 2D grid:
  - **Rows (Y-axis)**: Working Days (Monday through Friday).
  - **Columns (X-axis)**: Daily Time Slots (09:00–10:00, 10:00–11:00, etc.).
  - **Lunch break**: Rendered as a distinct vertical gray column.
  - Each cell shows the course code, subject name, teacher name, and assigned room.

#### 3. By Faculty View (`/api/timetable/faculty/<faculty_id>`)
- User selects a teacher (e.g. `Dr. Sharma`).
- Generates that teacher's personalized weekly schedule. Allows teachers to see their exact daily lecture hours, free periods, and lab sessions at a glance.

#### 4. By Room View (`/api/timetable/room/<room_id>`)
- User selects a classroom or lab (e.g. `Computer Lab 1`).
- Generates the room's weekly occupancy matrix. Essential for lab technicians and estate managers to check room availability.

#### 5. Print Timetable
- User clicks the **"Print Timetable"** button.
- CSS print media queries (`@media print`) strip away navigation bars, buttons, and forms, producing a clean, high-resolution timetable document suitable for printing or saving as PDF!
