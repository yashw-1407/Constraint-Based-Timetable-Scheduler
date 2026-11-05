# AutoSchedule: Comprehensive Functionality Matrix

**Version:** 2.0.0 Architecture Review  
**Target:** Institutional Scheduling Platform Readiness  
**Evaluation Standard:** Zero fabrication. Strict separation of UI appearance vs. actual backend/database capabilities.

---

## 1. Classification Key

- **Status 1 — Fully implemented and tested:** Code exists, verified via automated test suite, fully operational in production.
- **Status 2 — Implemented but not fully verified:** Backend and frontend wired, but edge cases or multi-scenario verification incomplete.
- **Status 3 — Partially implemented:** Significant portions of the logic exist, but key components, filters, or behaviors are unfinished.
- **Status 4 — UI only:** Visual controls exist on the frontend, but trigger no functional logic or connect to stub endpoints.
- **Status 5 — Completely missing:** Feature is absent from the current codebase.
- **Status 6 — Not applicable:** Excluded by architectural scope or category definition.

---

## 2. Feature-by-Feature Functionality Matrix

| Feature / Capability | Status | Current Implementation State | Required Backend Work | Required Frontend Work | Required Database Work |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **Working Hours & Slot Engine** | **1** | Full configuration of days, times, durations, and break intervals via `/api/config`. Tested in `test_03`. | None for standard uniform slots. Add support for day-specific variations if needed. | None. Clean pill and time input controls operating. | None. Persisted in `database.json`. |
| **Room Resource Management** | **1** | CRUD operations with capacity, type, category via `/api/rooms`. Tested in `test_08`. | Add department and building location fields. | Add building/block selector to workbench form. | Add `building_id`, `department_id` to Room model. |
| **Faculty Resource Management** | **1** | CRUD operations for instructor names and IDs via `/api/faculty`. Tested in `test_08`. | Add max weekly workload cap and email/department fields. | Add workload target input and department picker. | Add `max_hours`, `department_id`, `email` to Faculty model. |
| **Section & Batch Cohorts** | **1** | Section and Batch CRUD with semester and division via `/api/sections`, `/api/batches`. Tested in `test_08`. | None for standard cohorts. Add support for combined section lectures. | Add combined section cohort UI builder. | Add `parent_program_id`, `academic_term_id` to Section. |
| **Course & L-T-P Curriculum** | **1** | Multi-attribute course definitions with L-T-P credit hours and batch mapping via `/api/courses`. Tested in `test_08`. | Add elective basket and parallel course group support. | Add elective group builder in course entry form. | Add `is_elective`, `basket_id` to Course model. |
| **CSP Backtracking Engine** | **1** | Deterministic backtracking solver with MRV variable ordering and forward checking in `scheduler.py`. Tested in `test_05`. | None for core algorithm. Add asynchronous worker wrapper for long solves. | Add progress polling indicator for background solver jobs. | None. In-memory assignment state. |
| **Hard Constraint Validation** | **1** | Validates all 6 hard constraints (section, faculty, room, consecutive, type, capacity) in `constraints.py`. Tested in `test_06`. | None. Comprehensive rule checking implemented. | Formatted validation report presentation. | None. Evaluates active assignment graph. |
| **Soft Constraint Scoring** | **1** | Evaluates 7 quality metrics (faculty balance, student gaps, subject spread, room utilization) in `soft_constraints.py`. Tested in `test_05`. | Allow dynamic user weighting of soft rules via API. | Add constraint weight sliders or priority toggles. | Store constraint weight preferences in config table. |
| **Multi-Scenario Demo Loader** | **1** | 4 scenario presets (standard, bottleneck, infeasible, single section) via `/api/load-demo`. Tested in `test_02`. | None. All 4 scenarios verified and functional. | None. Scenario dropdown selector operational. | None. Ingests mock objects into persistence. |
| **Timetable Views (Master, Section, Faculty, Room)** | **1** | Multi-dimensional timetable grids rendered with sticky headers and responsive touch scroll. Tested in `test_07`. | Add server-side pagination for master grid with >15 sections. | Add cohort search/filter bar and collapsible day rows. | None. Formatted from active assignments. |
| **Print Optimization** | **1** | Dedicated `@media print` CSS rules optimizing timetable for A4 landscape document printing. | None. Browser-level printing operational. | Add print view options (toggle room/faculty metadata). | None. |
| **Pre-Generate Summary Audit** | **1** | Computes total weekly course hours vs. available slot capacity via `/api/summary`. Tested in `test_04`. | Add detailed breakdown of room capacity deficits by type. | Add visual deficit meter (e.g. red highlight when lab hours exceed lab slots). | None. Computed dynamically. |
| **Multi-Variant Generation** | **2** | Backend endpoint `/api/generate-multiple` generates alternative candidate schedules, but lacks UI presentation. | Verify tie-breaking logic and variant diversity scoring. | Build candidate comparison UI (Variant A vs. Variant B side-by-side). | Store generated variants in temporary run cache. |
| **Infeasible Diagnostics** | **2** | Solver outputs text log of conflicting variables when infeasible via `/api/generate`. Tested in `test_09`. | Structure diagnostic output into structured JSON entities (conflicting session, blocked rooms, clashing faculty). | Build visual conflict resolver highlighting exact clash points. | None. Computed during solver failure. |
| **Manual Timetable Adjustments** | **5** | Schedulers cannot manually drag-and-drop or swap sessions after generation. | Implement `/api/timetable/move-session` and `/api/timetable/swap-sessions` with live constraint re-validation. | Build interactive drag-and-drop timetable grid using HTML5 Drag and Drop or SortableJS. | Record manual overrides and user lock flags in assignment records. |
| **Session Pinning & Locking** | **3** | `required_room_id` locks rooms, but fixing sessions to specific day/time slots is unsupported. | Add `locked_day` and `locked_slot_index` attributes to `ScheduleSession` and enforce as pre-assignments. | Add pin/lock icons to timetable cells and course form fields. | Add `is_pinned`, `pinned_day`, `pinned_slot` to CourseComponent/Session. |
| **Excel & CSV Import Pipeline** | **5** | No bulk import functionality exists. Administrators must input all data manually. | Implement Excel/CSV parsing service with OpenPyXL; add column mapper and dry-run validation endpoints. | Build multi-step import modal (Upload -> Map Columns -> Validate -> Confirm). | Create staging table for uploaded raw data before database commit. |
| **Excel & PDF Export Pipeline** | **5** | Timetable can only be printed via browser; cannot be exported as `.xlsx` or vector `.pdf`. | Implement Excel export service using OpenPyXL generating multi-tab workbooks; implement PDF export. | Add "Export Excel" and "Export PDF" buttons in Timetable Views header. | None. Generated on-the-fly from timetable state. |
| **Academic Term Hierarchy** | **5** | Flat data structure. Historical and future semesters cannot coexist. | Refactor models to nest all courses, sections, and timetables under `AcademicYear` and `SemesterTerm`. | Build Term Switcher dropdown in application header. | Implement relational schema: `academic_years`, `terms`, `departments`. |
| **Departmental Partitioning** | **5** | All rooms, courses, and faculty belong to a single global scope. | Add `department_id` foreign keys; implement department-filtered view endpoints. | Add Department selector and view filters. | Add `departments` table with coordinator assignments. |
| **Timetable Publishing Workflow** | **5** | Only one global schedule exists; no distinction between draft and published. | Add schedule lifecycle states (`DRAFT`, `UNDER_REVIEW`, `APPROVED`, `PUBLISHED`). | Build Publishing Control Center with status badge and release buttons. | Add `status`, `published_at`, `approved_by` to Timetable records. |
| **User Authentication & RBAC** | **5** | Application is completely open; zero login screens or session management. | Implement JWT or session-based authentication; define RBAC middleware (`ADMIN`, `COORDINATOR`, `FACULTY`, `STUDENT`). | Build Login, Forgot Password, and Profile screens; conditional UI by role. | Implement `users`, `roles`, `user_roles`, `user_permissions` tables. |
| **Faculty & Student Portals** | **5** | Non-administrative stakeholders have no dedicated, clean, read-only portals. | Build lightweight, mobile-first endpoints (`/portal/my-schedule`, `/portal/student-view`). | Create simplified, dedicated web views for students and faculty without administrative chrome. | Link student enrollment records to specific section/batch IDs. |
| **Audit Logging & History** | **5** | Data edits occur silently without tracking who changed what or when. | Implement audit interceptor logging all state mutations (`INSERT`, `UPDATE`, `DELETE`, `GENERATE`). | Build Audit Log viewer with timestamps, author identity, and change diffs. | Create `audit_logs` table storing entity, action, author, diff payload. |
| **Public Marketing Website** | **5** | Domain loads directly into administrative single-page application. | Build public routing (`/`, `/features`, `/pricing`, `/demo`, `/contact`) serving marketing content. | Design and build high-conversion, professional public landing pages matching Hallmark design system. | Create `leads` table to capture contact and demo requests. |
| **Multi-Tenancy & SaaS Isolation** | **5** | Single local `database.json` file. Multi-institution hosting unsupported. | Refactor persistence layer for tenant isolation (tenant ID column or schema-per-tenant). | Multi-tenant subdomains (e.g. `kle.autoschedule.com`) or tenant switcher. | Migrate from flat JSON file to PostgreSQL with row-level security or schema isolation. |
| **Asynchronous Task Queue** | **5** | Generation runs synchronously within the Flask HTTP thread. Long solves risk HTTP timeouts. | Integrate Celery or Redis Queue for background solve execution with task ID and status polling. | Implement websocket or polling progress bar showing solver iterations and elapsed time. | Create `scheduling_jobs` table tracking status, progress, and execution stats. |

---

## 3. Technical Work Summary by Architectural Tier

### Tier 1: Backend Engineering Requirements
1. **Asynchronous Solver Execution:** Decouple `engine.solve()` from the HTTP request cycle using a task queue to prevent worker thread blocking.
2. **Data Ingestion Service:** Build an extensible parser for Excel (`.xlsx`) and CSV files with pre-flight schema verification and foreign-key integrity checking.
3. **Authentication & Authorization Engine:** Implement secure password hashing (Argon2 / bcrypt), session/JWT issuance, and role-based route guard decorators.
4. **Export Rendering Engine:** Generate downloadable Excel workbooks with formatted cell borders and color-coding, alongside vector PDF timetables.

### Tier 2: Frontend Engineering Requirements
1. **Data Import Wizard:** Multi-step modal component for file drop, column mapping, dry-run error display, and batch ingest.
2. **Interactive Schedule Canvas:** Enable manual drag-and-drop slot reassignments with immediate feedback against hard constraints.
3. **Dedicated Portals:** Separate administrative management views from student and faculty consumer timetable portals.
4. **Public Marketing Presence:** Public landing page detailing institutional value proposition, features, architecture, and demo requests.

### Tier 3: Database & Persistence Requirements
1. **Relational Database Migration:** Replace `database.json` flat-file with a robust relational database (SQLite for local standalone, PostgreSQL for cloud SaaS) managed via SQLAlchemy ORM.
2. **Hierarchical Academic Schema:** Introduce entities for `Institutions`, `Campuses`, `AcademicYears`, `Terms`, `Departments`, and `Programs`.
3. **Timetable Versioning & State:** Store timestamped schedule runs with version numbers, lifecycle statuses (`DRAFT`, `PUBLISHED`), and change logs.
