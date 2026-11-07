# Constraint-Based Academic Timetable Scheduling System

An academic timetable scheduling system powered by a **Constraint Satisfaction Problem (CSP) Backtracking Solver**.

Persisted with **SQLite**, providing conflict-free timetable generation with configurable working hours, break periods, theory/lab rooms, faculty assignments, and batch-wise scheduling.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the application
python app.py

# 3. Open in your browser
http://127.0.0.1:5000
```

### Walkthrough
1. **Configuration**: Choose a demo scenario (e.g. Standard, Bottleneck, Single Section) and click **Load Demo Data** (or configure working days, hours, lunch, and breaks manually).
2. **Review Data**: Inspect Rooms, Faculty, Sections/Batches, and Courses tabs.
3. **Import Excel (Optional)**: Download the provided `.xlsx` template, edit it with your college details, and upload it to import directly into SQLite.
4. **Generate**: Click **Generate Timetable** to run the CSP solver.
5. **Timetable Views**: Switch between Master View, By Section, By Faculty, and By Room grids, or print the schedule.

---

## Clean Project Structure

```
Constraint-Based-Timetable-Scheduler/
│
├── app.py                         # Flask web application & REST API routes
├── database.py                    # SQLite persistence layer (autoschedule.db)
├── models.py                      # Clean domain models & dataclasses
├── scheduler.py                   # Time-slots, CSP backtracking engine, constraints, views
├── demo_data.py                   # Pre-configured demo datasets for test cases
├── excel_import.py                # Excel workbook importer & template exporter
│
├── autoschedule.db                # SQLite database file
├── timetable_import_template.xlsx # Excel template for bulk import
├── requirements.txt               # Dependencies (flask, openpyxl)
├── README.md                      # Documentation
│
├── templates/
│   └── index.html                 # Single-page web UI
└── static/
    ├── app.js                     # Clean frontend controller & grid renderer
    └── style.css                  # UI styling
```

---

## Key Features

- **SQLite Relational Persistence**: Zero JSON files; all entities and generated schedules are stored in relational SQLite tables.
- **Dynamic Time Slots**: Slot durations, lunch intervals, and tea/extra breaks dynamically determine scheduling periods.
- **CSP Backtracking with MRV**: Uses the Minimum Remaining Values heuristic and forward checking to prune search space efficiently (<1s typical runtime).
- **Hard Constraints Enforced**:
  1. Section conflict (no simultaneous theory sessions)
  2. Batch conflict (no batch double-booking; separate batches can run labs concurrently)
  3. Faculty conflict (no faculty clashes)
  4. Room conflict (no room clashes)
  5. Room suitability & capacity (theory rooms vs labs, capacity check)
  6. Consecutive multi-slot lab scheduling
- **Soft Constraint Quality Scoring**: Evaluates subject distribution across days, student gap minimization, balanced faculty workload, and even room utilization.
- **Four Schedule Views**: Master grid, Section grid, Faculty grid, and Room grid with print support.
