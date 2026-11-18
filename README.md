# Constraint-Based Academic Timetable Scheduling System

An academic timetable scheduling system powered by a **Constraint Satisfaction Problem (CSP) Backtracking Solver**.

Persisted with **SQLite**, providing conflict-free timetable generation with configurable working hours, break periods, theory/lab rooms, faculty assignments, and batch-wise scheduling.

---

## Quick Start

### 1-Click / 1-Tap Launch (Recommended)
Simply double-click:
- **`run.bat`** (or **`START.bat`**) in this folder, or
- The **Academic Timetable Scheduler** shortcut on your Desktop!

It will automatically:
1. Detect Python and verify/install required dependencies (`Flask`, `openpyxl`).
2. Start the local Flask web server.
3. Automatically launch your default web browser tab to `http://127.0.0.1:5001`.

---

### Manual Launch (Command Line)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the application
python app.py

# 3. Open in your browser
http://127.0.0.1:5001
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
├── docs/                          # In-depth architectural & technical documentation
├── templates/
│   └── index.html                 # Single-page web UI
└── static/
    ├── app.js                     # Clean frontend controller & grid renderer
    └── style.css                  # UI styling
```

---

## Technical Documentation

Comprehensive system and algorithm documentation is available in the [`docs/`](docs/) directory:

- [Project Overview](docs/PROJECT_OVERVIEW.md) — Problem statement, manual challenges, and core solutions.
- [System Architecture](docs/ARCHITECTURE.md) — Three-tier design, data flow diagrams, and REST APIs.
- [Algorithm Explained](docs/ALGORITHM_EXPLAINED.md) — CSP modeling, MRV heuristics, and hard/soft constraint scoring.
- [Database Explained](docs/DATABASE_EXPLAINED.md) — SQLite schema, 12 tables, foreign keys, and persistence.
- [Complete Workflow](docs/COMPLETE_WORKFLOW.md) — Step-by-step tracing from browser interaction to database commits.
- [Technical Q&A / FAQ](docs/TECHNICAL_FAQ.md) — 50+ in-depth technical questions and answers.
- [Live Demo Guide](docs/DEMO_GUIDE.md) — Step-by-step demonstration runbook with fallback strategies.
- [Project Limitations](docs/PROJECT_LIMITATIONS.md) — Identified architectural trade-offs and future scope.

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
