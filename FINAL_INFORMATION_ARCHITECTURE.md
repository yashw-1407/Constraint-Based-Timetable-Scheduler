# AutoSchedule: Final Information Architecture & Page Hierarchy

**Architecture Blueprint:** Multi-Portal Academic Scheduling Platform  
**Target Domains:** Higher Education Institutions, Technical Colleges, K-12 School Systems  
**Design Principle:** Strict separation of administrative control, stakeholder consumption, and commercial discovery.

---

## 1. High-Level Portal Separation

AutoSchedule separates into **5 dedicated functional planes**, each designed for a specific user journey and security boundary:

```
                                  AutoSchedule Platform
                                            │
        ┌───────────────────┬───────────────┴───────────────┬───────────────────┐
        │                   │                               │                   │
1. Public Marketing   2. Institutional Admin        3. Faculty Portal   4. Student Portal
   (Prospective)      (Timetable Coordinators)       (Instructors)       (Learners)
                            │
                      5. Platform Ops
                         (Superadmins)
```

---

## 2. Portal 1: Public Marketing & Commercial Website

*Audience:* University Deans, Registrars, Department Heads, IT Directors, Academic Evaluators.  
*Primary Objective:* Communicate product capability, algorithmic rigor, commercial pricing, and capture institutional demo leads.

### Page Hierarchy & Route Map

| Route | Page Name | Primary Purpose & User Journey |
| :--- | :--- | :--- |
| `/` | **Platform Overview (Homepage)** | High-impact institutional landing page showcasing the deterministic CSP engine, core benefits (zero clash guarantee, sub-second solves), animated schedule preview, and social proof. |
| `/features` | **Engine & Features Deep Dive** | Detailed breakdown of hard constraint guarantees, soft preference scoring, multi-room partitioning, and automated batch scheduling. |
| `/technology` | **Algorithm & Architecture** | Academic and technical justification: Explaining why CSP backtracking beats Genetic Algorithms and ILP; formal (X, D, C) mathematical model; curriculum mappings (DAA, OS, DBMS, DMS). |
| `/solutions/universities` | **Higher Education Solutions** | Focuses on multi-section cohorts, lab batch splitting across partitioned facilities, and faculty workload caps. |
| `/solutions/schools` | **K-12 & High School Solutions** | Focuses on teacher substitution, uniform bell schedules, and fixed homeroom constraints. |
| `/pricing` | **Institutional Licensing** | Transparent tier matrix: Department Starter, Campus Standard, and Multi-Campus Enterprise with annual seat and term volume models. |
| `/request-demo` | **Institutional Consultation** | Interactive demo booking form collecting campus size, student count, and ERP integration requirements. |
| `/docs` | **Platform Documentation** | Setup guides, CSV/Excel schema definitions, API reference, and administrator manuals. |

---

## 3. Portal 2: Institutional Administration Application

*Audience:* Timetable Coordinators, Academic Deans, Department Registrars.  
*Primary Objective:* End-to-end academic asset configuration, constraint management, automated generation, manual override, and schedule publishing.

### Navigation Shell & Layout
- **Global Header:** Institutional branding, Active Academic Term switcher (`Fall 2026-27`), System health badge, Notification center, User profile.
- **Primary Sidebar Navigation:** Grouped into 4 functional modules:
  1. Overview (Dashboard)
  2. Academic Assets (Setup & Curriculum)
  3. Schedule Operations (Solver & Analysis)
  4. Governance (Publishing, Users, Audit)

### Page Hierarchy & Route Map

```
/app
├── /dashboard                    -> Operational Command Center
├── /setup
│   ├── /calendar                 -> Working Days, Operating Hours, Breaks
│   ├── /departments              -> Academic Departments & Divisions
│   ├── /rooms                    -> Lecture Classrooms & Lab Facilities
│   ├── /faculty                  -> Instructors & Teaching Load Caps
│   ├── /sections                 -> Student Cohorts & Lab Practical Batches
│   └── /courses                  -> Course Catalog & L-T-P Credit Rules
├── /data-management
│   ├── /import                   -> Excel & CSV Multi-Step Ingestion Wizard
│   ├── /export                   -> Institutional Data & Backup Export
│   └── /integrity-check          -> Orphaned Entity & Constraint Sanity Check
├── /solver
│   ├── /workspace                -> Solver Execution & Parameter Controls
│   ├── /variants                 -> Candidate Comparison (A vs. B Scoring)
│   └── /diagnostics              -> Infeasibility & Conflict Trace Graph
├── /timetables
│   ├── /master                   -> Comprehensive Multi-Cohort Institutional Grid
│   ├── /by-section               -> Filtered Cohort Schedule Ledger
│   ├── /by-faculty               -> Individual Instructor Workload Schedule
│   ├── /by-room                  -> Physical Room Occupancy Matrix
│   └── /manual-editor            -> Drag-and-Drop Slot Override Canvas
└── /governance
    ├── /publishing               -> Schedule State Lifecycle (Draft -> Published)
    ├── /access-control           -> Administrator Roles & Permissions (RBAC)
    └── /audit-trail              -> Immutable Event Log of Changes & Edits
```

### Key Page User Journeys

1. **`/app/dashboard` (Operational Command Center):**
   - *Journey:* Scheduler logs in -> Sees active semester status -> Views resource counts (48 courses, 12 rooms, 24 faculty) -> Inspects capacity utilization gauge (78% slot load) -> Identifies 2 unassigned courses -> One-click shortcut to complete assignment.

2. **`/app/data-management/import` (Excel/CSV Ingestion Wizard):**
   - *Journey:* User drops Excel file from campus ERP -> System auto-detects sheets (Faculty, Rooms, Courses) -> User maps column headers with instant preview -> System runs dry-run validation (catches 1 missing room code) -> User corrects and confirms bulk ingest.

3. **`/app/solver/workspace` (Scheduling Engine):**
   - *Journey:* User selects target term -> Configures constraint priority weights (e.g. emphasize minimizing student gaps) -> Clicks "Execute Solver" -> Live visual progress shows variables being bound -> Solver completes in 45ms -> Displays soft quality score (88%) and variant comparison shortcut.

4. **`/app/timetables/manual-editor` (Interactive Override Canvas):**
   - *Journey:* Dean requests moving Dr. Sharma's Wednesday lecture to Thursday -> Scheduler drags session on grid -> System runs live constraint check in background -> Indicates valid drop target in green / clashing slots in red -> User drops session -> System logs manual override note.

5. **`/app/governance/publishing` (Publishing Lifecycle Control):**
   - *Journey:* Schedule passes departmental review -> Admin clicks "Promote to Approved" -> Academic Dean enters digital sign-off -> Admin clicks "Publish Schedule" -> Status changes to `PUBLISHED` -> Schedule immediately becomes visible on Student and Faculty portals.

---

## 4. Portal 3: Faculty Portal

*Audience:* Professors, Associate Professors, Laboratory Instructors, Teaching Assistants.  
*Primary Objective:* View personal teaching schedule, inspect allocated lecture halls/labs, sync with personal calendar, and request room/slot swaps.

### Page Hierarchy & Route Map

| Route | Page Name | Primary Purpose & User Journey |
| :--- | :--- | :--- |
| `/faculty/my-schedule` | **Personal Teaching Schedule** | Clean, mobile-responsive weekly grid displaying confirmed teaching commitments, course codes, section names, and room locations. |
| `/faculty/calendar-sync` | **iCal / Google Calendar Feed** | Generates a persistent subscribed calendar feed (.ics) for automated calendar sync to Apple Calendar, Outlook, and Google Calendar. |
| `/faculty/workload` | **Teaching Load Summary** | Visual summary of weekly lecture vs. practical contact hours, student counts, and gap distributions. |
| `/faculty/swap-requests` | **Schedule Adjustment Requests** | Formal workflow allowing an instructor to request a peer room/slot exchange, routed to the timetable coordinator for administrative approval. |

---

## 5. Portal 4: Student & Public Schedule Portal

*Audience:* Enrolled Students, Parents, Campus Visitors.  
*Primary Objective:* Zero-friction, mobile-optimized lookup of current class timetables without administrative clutter.

### Page Hierarchy & Route Map

| Route | Page Name | Primary Purpose & User Journey |
| :--- | :--- | :--- |
| `/portal` | **Class Schedule Lookup** | Clean selector: Select Degree Program -> Select Semester -> Select Section / Batch. Instant rendering of active weekly schedule. |
| `/portal/section/<id>` | **Direct Cohort Timetable** | Shareable, bookmarkable permalink for class cohorts (e.g. `autoschedule.edu/portal/section/CS_3A`). |
| `/portal/room-occupancy` | **Campus Room Availability** | Public directory showing which classrooms and study labs are currently free during campus hours for student study groups. |
| `/portal/export` | **Student Schedule Download** | One-click download of personal section schedule as a mobile wallpaper image, printable PDF, or subscribed iCal feed. |

---

## 6. Portal 5: Platform Superadmin (Multi-Tenant Management)

*Audience:* Platform Site Reliability Engineers (SREs), SaaS Operations Team.  
*Primary Objective:* Manage institutional tenants, platform provisioning, global billing, and system telemetric health.

### Page Hierarchy & Route Map

| Route | Page Name | Primary Purpose & User Journey |
| :--- | :--- | :--- |
| `/admin/tenants` | **Institutional Tenant Directory** | Manage university customer tenants (e.g., KLE Technological University, MIT, Stanford), domain mappings, and license seat allocations. |
| `/admin/telemetry` | **Solver Performance Analytics** | Global telemetry tracking average solve times, constraint failure frequencies, backtrack depths, and computational engine memory footprints. |
| `/admin/backups` | **System Backups & Disaster Recovery** | Manage automated point-in-time database backups, snapshot restoration, and multi-region data replication. |
| `/admin/audit` | **Cross-Tenant Security Audit** | Security monitoring of login anomalies, rate-limit triggers, and administrative credential changes. |

