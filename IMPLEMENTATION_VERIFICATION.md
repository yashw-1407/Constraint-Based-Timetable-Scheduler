# AutoSchedule: Implementation Verification Report

**Date:** November 2026  
**Repository Branch:** `redesign-v2`  
**Execution Standard:** Zero fabrication. Strict source-code inspection and executable test evidence.

---

## 1. Executive Summary

This verification audit independently examines the source code, backend API endpoints, database persistence mechanisms, frontend integration, and runtime test results of the AutoSchedule repository.

Testing was conducted directly against the live application and test suite. Key findings:
- **Core Functionality Operational:** The pure-Python CSP engine, multi-candidate generation, Excel import/export pipelines, academic term switcher, public student portal, and password authentication are functional.
- **Active Regression Identified:** Commit `8121f15` ("Refactor backend: simplify CSP scheduler and Flask routes, remove bloat") streamlined `scheduler.py`, but removed internal helper methods (`_check_hard_constraints` and `_get_scheduling_strength`). Consequently, `adjuster.py` currently raises `AttributeError` on session move/swap operations, causing 2 of 21 tests (`test_16` and `test_17`) to fail with HTTP 500 errors.
- **Security Vulnerability Identified:** While user authentication with PBKDF2-HMAC-SHA256 password hashing and session cookies exists, **zero backend route protection is enforced**. Destructive and administrative endpoints (`/api/clear`, `/api/rooms`, `/api/courses`, `/api/generate`, `/api/timetable/publish`, `/api/import/excel`) accept requests from unauthenticated guests without session or role verification.
- **Persistence Architecture:** Relational database and SQLAlchemy migration are **completely absent**. All data is persisted to a single flat JSON file (`database.json`) with an atomic temporary file replacement pattern (`os.replace`).

---

## 2. Feature-by-Feature Verification

### 2.1 Relational Database and SQLAlchemy Migration
- **Actual Implementation:** Missing. The persistence layer in `database.py` relies on `json.dump` and `json.load` against a single flat file (`database.json`). No SQLAlchemy models, ORM engines, or migration scripts exist in the repository.
- **Backend Endpoints:** None.
- **Frontend Integration:** N/A.
- **Database Persistence:** Single flat-file JSON with file lock (`threading.Lock()`) and atomic rename (`os.replace`).
- **Authorization & Access:** None.
- **Error Handling:** Basic `try/except` in `load_data` with standard console warning.
- **Automated Test Coverage:** None.
- **Runtime Behavior:** Functional for single-process local demo datasets, but lacks ACID transaction isolation, indexes, foreign key enforcement, and relational querying.
- **Classification:** **Missing**.

### 2.2 Excel/CSV Import Pipeline
- **Actual Implementation:** Implemented in `importer.py` using `openpyxl`.
- **Backend Endpoints:**
  - `GET /api/import/template`: Generates a formatted starter workbook with sheets for Rooms, Faculty, Sections, Batches, and Courses.
  - `POST /api/import/excel`: Parses uploaded `.xlsx` files, performs foreign key and schema validation, and merges (`append`) or replaces (`replace`) existing data.
- **Frontend Integration:** Modal dialog (`#modal-import` in `templates/index.html`) wired in `static/app.js` with mode toggles and error feedback display.
- **Database Persistence:** Validated records populate `app_data` and are written to `database.json`.
- **Authorization & Access:** **Unprotected**. Any unauthenticated client can upload workbooks and overwrite institutional data.
- **Error Handling:** Granular error collection reporting sheet names, row numbers, duplicate primary keys, missing foreign keys, and invalid L-T-P ratios.
- **Automated Test Coverage:** Verified in `test_11_excel_import_template_generation` and `test_12_excel_bulk_import_validation` (Passing).
- **Runtime Behavior:** Verified. Correctly parses multi-sheet workbooks and rejects malformed rows.
- **Classification:** **Verified Complete (Pending Route Authorization)**.

### 2.3 User Authentication and Session Management
- **Actual Implementation:** `models.py` defines `User` and `UserRole`. `database.py` implements `hash_password` and `verify_password` using Python's standard `hashlib.pbkdf2_hmac` with SHA-256 and 100,000 iterations.
- **Backend Endpoints:**
  - `GET /api/auth/me`: Returns current session identity and authentication state.
  - `POST /api/auth/login`: Verifies username and salted hash; initializes Flask `session['user']`.
  - `POST /api/auth/logout`: Clears session.
  - `GET /api/auth/users` & `POST /api/auth/users`: Lists and registers users.
- **Frontend Integration:** Header user status badge (`#header-user-badge`), Sign In button (`#btn-auth-action`), and Sign In modal (`#modal-auth`) with quick login buttons for Admin, Coordinator, and Faculty.
- **Database Persistence:** Users stored in `database.json` under `"users"` array with 64-character hex hash and salt.
- **Authorization & Access:** Login flow manages session cookies. Route `/api/auth/users` is not protected against unauthenticated user creation.
- **Error Handling:** Returns HTTP 400 for missing fields, HTTP 401 for invalid credentials.
- **Automated Test Coverage:** Verified in `test_21_user_authentication_flow` and real-browser Playwright automation (Passing).
- **Runtime Behavior:** Login, session persistence, header badge updates, and logout execute reliably.
- **Classification:** **Verified Complete**.

### 2.4 Role-Based Access Control (RBAC)
- **Actual Implementation:** Role enum defined in `models.py` (`ADMIN`, `COORDINATOR`, `FACULTY`, `STUDENT`). User objects hold a role property.
- **Backend Endpoints:** No operational routes enforce role permissions. No `@require_role` or `@login_required` decorators exist.
- **Frontend Integration:** Badge displays `${username} (${role})`. However, no UI tabs or controls are conditionally hidden or disabled based on role.
- **Database Persistence:** Roles stored in `database.json`.
- **Authorization & Access:** **Unenforced**. Faculty and unauthenticated guests have identical API capabilities to Administrators.
- **Error Handling:** None (no authorization denial logic exists).
- **Automated Test Coverage:** Test 21 verifies role property assignment; no access control denial tests exist.
- **Runtime Behavior:** Roles exist as data labels, but not as functional access gates.
- **Classification:** **Partially Implemented (Data Model Present, Enforcement Missing)**.

### 2.5 Academic Terms and Departments
- **Actual Implementation:** `models.py` defines `AcademicTerm` (`id`, `name`, `academic_year`, `semester_type`, `is_active`) and `Department` (`id`, `name`, `code`). Seeded with defaults in `database.py`.
- **Backend Endpoints:**
  - `GET /api/terms`: Returns term list and `active_term_id`.
  - `POST /api/terms/activate/<id>`: Sets active term and updates publishing metadata.
  - `GET /api/departments`: Returns registered academic departments.
- **Frontend Integration:** Dropdown selectors (`#header-term-select` in `index.html` and `#portal-term-select` in `portal.html`) allow dynamic switching.
- **Database Persistence:** Persisted in `database.json`.
- **Authorization & Access:** Unrestricted.
- **Error Handling:** Returns HTTP 404 on invalid term ID.
- **Automated Test Coverage:** Verified in `test_18_academic_terms_management` and `test_19_department_hierarchy` (Passing).
- **Runtime Behavior:** Term switcher updates active term metadata. Note: timetable sessions and courses are not yet filtered or partitioned by academic term.
- **Classification:** **Verified Complete (Hierarchy and Switching Operational)**.

### 2.6 Excel Timetable Export
- **Actual Implementation:** `exporter.py` generates an institutional multi-tab spreadsheet using `openpyxl`.
- **Backend Endpoints:** `GET /api/export/excel`.
- **Frontend Integration:** "Export Excel" buttons in `templates/index.html` views toolbar and `templates/portal.html`.
- **Database Persistence:** Formatted on-the-fly from active assignments.
- **Authorization & Access:** Publicly accessible.
- **Error Handling:** Returns HTTP 400 with JSON error message if timetable is not generated.
- **Automated Test Coverage:** Verified in `test_13_excel_timetable_export` (Passing).
- **Runtime Behavior:** Generates a 4-tab workbook (`Master Timetable`, `Sections`, `Faculty`, `Rooms`) with borders, headers, and color-coded theory/lab cells.
- **Classification:** **Verified Complete**.

### 2.7 Manual Timetable Adjustments
- **Actual Implementation:** `adjuster.py` implements two-phase commit move and swap algorithms (`validate_move`, `execute_move`, `execute_swap`).
- **Backend Endpoints:**
  - `POST /api/timetable/validate-move`: Dry-run conflict check.
  - `POST /api/timetable/move`: Relocates a session.
  - `POST /api/timetable/swap`: Atomically swaps two sessions.
- **Frontend Integration:** Interactive session adjustment modal (`#modal-move-session`) triggered by clicking session cards on timetable grids.
- **Database Persistence:** Modifications update assignments and call `save_data(app_data)`.
- **Authorization & Access:** Unrestricted.
- **Error Handling:** Conflict codes (`SECTION_CONFLICT`, `FACULTY_CONFLICT`, `ROOM_CONFLICT`, `SLOT_OUT_OF_BOUNDS`).
- **Automated Test Coverage:** Tested in `test_16` and `test_17` (Currently FAILING).
- **Runtime Behavior:** **Regression Detected**. Due to refactoring in commit `8121f15`, `SchedulingEngine` lacks `_get_scheduling_strength` and `_check_hard_constraints`, raising `AttributeError` on move validation and swap.
- **Classification:** **Blocked / Broken by Recent Refactor**.

### 2.8 Conflict Validation
- **Actual Implementation:** `constraints.py` provides independent validation functions (`check_section_conflict`, `check_faculty_conflict`, `check_room_conflict`, `check_consecutive_slots`, `check_room_suitability`, `check_room_capacity_by_strength`, `validate_timetable`).
- **Backend Endpoints:** `GET /api/validation`.
- **Frontend Integration:** "Validate Timetable" button on Generate tab displays structured banner and conflict list.
- **Database Persistence:** Validates in-memory assignment state.
- **Authorization & Access:** Publicly accessible.
- **Error Handling:** Returns HTTP 400 if no timetable exists; returns `{valid: false, conflicts: [...]}` on collision.
- **Automated Test Coverage:** Verified in `test_06_post_generation_hard_constraints_validation` (Passing).
- **Runtime Behavior:** Verified. Evaluates active assignments against all 6 hard constraints.
- **Classification:** **Verified Complete**.

### 2.9 Schedule Publishing Lifecycle
- **Actual Implementation:** `app.py` manages publishing state (`status`, `is_published`, `published_at`, `term`).
- **Backend Endpoints:**
  - `GET /api/timetable/status`: Returns current publishing state.
  - `POST /api/timetable/publish`: Transitions state to `PUBLISHED` with UTC timestamp.
  - `POST /api/timetable/unpublish`: Reverts state to `DRAFT`.
- **Frontend Integration:** Header status chip (`Draft` vs `Published`), views toolbar lifecycle badge, and Publish/Unpublish buttons.
- **Database Persistence:** Persisted in `database.json`.
- **Authorization & Access:** Unrestricted.
- **Error Handling:** Returns HTTP 400 if publishing is attempted without a generated timetable.
- **Automated Test Coverage:** Verified in `test_15_publishing_lifecycle` (Passing).
- **Runtime Behavior:** State toggles between `DRAFT` and `PUBLISHED` cleanly.
- **Classification:** **Verified Complete**.

### 2.10 Schedule Versioning
- **Actual Implementation:** Missing. The application maintains only a single active publishing record. Previous schedule iterations, historical snapshots, and rollback histories are overwritten upon re-generation or adjustment.
- **Backend Endpoints:** None (`/api/timetable/versions` does not exist).
- **Frontend Integration:** None.
- **Database Persistence:** No version archive in `database.json`.
- **Automated Test Coverage:** None.
- **Runtime Behavior:** Historical versions cannot be compared or restored.
- **Classification:** **Partially Implemented (Single-state tracking only; true versioning missing)**.

### 2.11 Multiple Timetable Candidates
- **Actual Implementation:** `scheduler.py` implements `solve_multiple` utilizing random seed perturbations and Jaccard distance penalties for diversity.
- **Backend Endpoints:**
  - `POST /api/generate-multiple`: Generates candidate schedules meeting a diversity threshold.
  - `POST /api/timetable/variant/<index>`: Activates chosen candidate.
  - `GET /api/timetable/metadata`: Returns candidate counts and scores.
- **Frontend Integration:** Candidate comparison grid (`#variants-grid`) displaying quality score, diversity divergence percentage, soft constraint breakdown chips, "Inspect Views" and "Activate" buttons.
- **Database Persistence:** Variants persisted in `database.json` under `result['variants']`.
- **Authorization & Access:** Unrestricted.
- **Error Handling:** Bounds checking on variant index; returns HTTP 400 for invalid indices.
- **Automated Test Coverage:** Verified in `test_14_multi_variant_generation_and_selection` (Passing).
- **Runtime Behavior:** Generates diverse candidates, renders comparison cards, and switches active variant cleanly.
- **Classification:** **Verified Complete**.

### 2.12 Student Timetable Portal
- **Actual Implementation:** `templates/portal.html` rendered via `GET /portal` in `app.py`.
- **Backend Endpoints:** Consumes `/api/timetable/master`, `/api/timetable/status`, `/api/terms`, `/api/time-slots`, `/api/config`.
- **Frontend Integration:** Standalone, clean interface without administrative navigation. Provides Section, Faculty, Room, and Master view tabs, real-time search box, Excel download, and print view.
- **Database Persistence:** Reads active published schedule.
- **Authorization & Access:** Fully public (intended for student and guest access).
- **Error Handling:** Displays clean empty-state notices when schedule is draft or unconfigured.
- **Automated Test Coverage:** Verified in `test_20_public_student_portal` (Passing).
- **Runtime Behavior:** Renders timetable grids and filters courses and faculty in real-time.
- **Classification:** **Verified Complete**.

---

## 3. Discrepancy Analysis

Comparing the source code against prior planning and audit documents surfaces several discrepancies:

| Topic | Claim in Prior Documentation | Actual Source Code Reality | Severity |
| :--- | :--- | :--- | :--- |
| **Relational Database** | Listed as Milestone 1.1 in `PRODUCT_ROADMAP.md` as "Phase 1: Core Platform MVP". | No SQLAlchemy, SQLite, or PostgreSQL code exists. Storage remains flat `database.json`. | **High** |
| **Role-Based Access Control** | Marked as "COMPLETED & VERIFIED" in `PRODUCT_ROADMAP.md` and `FUNCTIONALITY_MATRIX.md`. | RBAC exists only as a data field on `User` models and a visual badge in the UI. Zero endpoints enforce `@require_role` or block unauthorized actions. | **Critical** |
| **Manual Adjustments** | Marked as "COMPLETED & VERIFIED" in `PRODUCT_ROADMAP.md`. | Currently broken by commit `8121f15`, which removed required engine methods. Tests 16 and 17 fail with HTTP 500 errors. | **High** |
| **Schedule Versioning** | Grouped under Milestone 2.3 ("Publishing Lifecycle & Versioning"). | Only a single publishing status object exists. No historical versions, snapshots, or rollback capabilities exist. | **Medium** |
| **Academic Term Scope** | Listed as Milestone 1.4 ("Term & Department Hierarchy"). | Active term switching works, but schedule entities are not partitioned by term. Switching to "Spring" does not load a separate course catalog or schedule. | **Medium** |

---

## 4. Integration Testing Results

Execution of full end-to-end user workflows yielded the following empirical results:

```
Workflow 1: Admin Authentication                      -> PASS (200 OK, session cookie set)
Workflow 2: Configure Academic Term                   -> PASS (200 OK, term switch metadata updated)
Workflow 3: Create Resources (Rooms/Faculty)          -> PASS (200 OK, persisted to database.json)
Workflow 4: Download Import Template                  -> PASS (200 OK, 5 sheets present in XLSX)
Workflow 5: Ingest Excel Dataset                      -> PASS (200 OK, courses/rooms imported)
Workflow 6: Generate Multiple Candidates              -> PASS (200 OK, diverse candidates generated)
Workflow 7: Compare & Select Variant                  -> PASS (200 OK, variant activated)
Workflow 8: Validate Manual Move                      -> FAIL (500 Internal Server Error, AttributeError)
Workflow 9: Hard Constraint Collision Detection       -> FAIL (Blocked by Workflow 8 failure)
Workflow 10: Publish Timetable                        -> PASS (200 OK, status: PUBLISHED)
Workflow 11: Access via Student Portal                -> PASS (200 OK, read-only view accessible)
Workflow 12: Export Timetable to Excel                -> PASS (200 OK, multi-tab XLSX generated)

Data Survival Across Restart                          -> PASS (Assignments and config persist in database.json)
```

---

## 5. Security Assessment

1. **Default Credentials:**
   - Default seeded accounts: `admin`, `coordinator`, `faculty`.
   - Credentials are documented in quick-login UI buttons for demonstration. Production deployments must enforce credential rotation on first boot.
2. **Password Storage:**
   - Uses `hashlib.pbkdf2_hmac('sha256', password, salt, 100000)`.
   - Salt is uniquely generated (16 bytes hex) per user.
   - Hash output is 64 hex characters (256-bit). Standard meets OWASP password storage recommendations.
3. **Session Security:**
   - Flask client-side signed session cookies using secret key.
   - In `app.py`, secret key defaults to a hardcoded string if `SECRET_KEY` environment variable is not set. Must require environment variable in production.
   - Session cookies lack explicit `HttpOnly`, `Secure`, and `SameSite` flag configuration.
4. **CSRF Protection:**
   - **Missing**. Flask-WTF or CSRF tokens are not utilized on JSON API endpoints. State-changing `POST`, `PUT`, `DELETE` routes rely solely on `Content-Type: application/json`.
5. **Unauthorized API Access & RBAC Enforcement:**
   - **Critical Vulnerability**: Operational endpoints lack authentication and authorization decorators. An unauthenticated guest or malicious script can execute:
     - `POST /api/clear` (wipes all data)
     - `POST /api/generate` (triggers heavy compute)
     - `POST /api/timetable/publish` (changes public schedule)
     - `POST /api/import/excel` (injects arbitrary data)
6. **File Upload Validation:**
   - Excel upload verifies file extension (`.xlsx`, `.xlsm`) and validates internal sheet names and data structures via `openpyxl`.
   - Rejects non-spreadsheet payloads with HTTP 400.
7. **Destructive Operations:**
   - `/api/clear` performs complete data reset. Frontend requires confirmation modal, but API endpoint has no protection or confirmation requirement.

---

## 6. Recommendations for Next Milestone

The findings indicate that **infrastructure complexity (such as full PostgreSQL multi-tenancy or Celery worker pools) should not be started while basic route protection and the manual adjustment engine remain incomplete**.

The immediate priority must be resolving the core platform seams:
1. **Restore Manual Adjustment Engine Seam**: Align `adjuster.py` with `scheduler.py` so move and swap validations execute conflict checks without `AttributeError`.
2. **Implement RBAC Middleware**: Add `@login_required` and `@require_role([UserRole.ADMIN, UserRole.COORDINATOR])` across all operational routes.
3. **Relational Database Migration (SQLite/SQLAlchemy)**: Replace `database.json` with formal SQLite persistence to provide proper transaction boundaries and enable multi-term schedule partitioning.
