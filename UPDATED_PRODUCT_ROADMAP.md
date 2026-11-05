# AutoSchedule: Updated Product Implementation Roadmap

**Architecture Strategy:** Grounded Evolutionary Advancement of Institutional Academic Scheduling  
**Guiding Principle:** Prioritize a functional, cohesive academic scheduling product over premature enterprise infrastructure. Maintain the integrity of the verified pure-Python CSP core engine.

---

## 1. Roadmap Status Overview

Based on empirical verification of the repository (November 2026):

```
[Phase 1: Core Platform Foundation] ────> [Phase 2: Operational Workflows] ────> [Phase 3: Multi-Portal Experience] ────> [Phase 4: Institutional SaaS]
├── Excel Bulk Ingest [VERIFIED]          ├── Multi-Variant Candidates [VERIFIED]  ├── Student Schedule Portal [VERIFIED]  ├── Multi-Tenant DB Schema [PENDING]
├── Academic Hierarchy [VERIFIED]         ├── Publishing Lifecycle [VERIFIED]     ├── Faculty Portal & iCal [PENDING]     ├── SSO / SAML 2.0 Auth [PENDING]
├── User Auth (PBKDF2) [VERIFIED]         ├── Excel Timetable Export [VERIFIED]    ├── Change Alert Dispatch [PENDING]     ├── Asynchronous Solver Pool [PENDING]
├── RBAC Enforcement [VERIFIED COMPLETE]  ├── Manual Adjustments [VERIFIED COMPL]  └── Mobile PWA Polish [PENDING]        └── Commercial Marketing Site [PENDING]
└── Relational DBMS (SQLAlchemy) [VERIF]  └── Schedule Versioning [VERIFIED COMPL]
```

---

## 2. Phase-by-Phase Status & Gap Breakdown

### Phase 1: Core Platform Foundation

| Milestone | Status | Reality in Codebase | Next Action Required |
| :--- | :---: | :--- | :--- |
| **1.1 Relational Persistence (SQLAlchemy)** | **Verified Complete** | SQLite primary persistence layer via SQLAlchemy ORM (`autoschedule.db`), Flask-Migrate integration, and safe JSON migration utility. | None. Verified complete with 10 dedicated DBMS integration tests. |
| **1.2 Bulk Excel Ingestion Pipeline** | **Verified Complete** | `importer.py` validates multi-sheet workbooks with dry-run error collection. Protected by RBAC. | None for core ingestion. Fully functional. |
| **1.3 User Authentication & Sessions** | **Verified Complete** | PBKDF2-HMAC-SHA256 password hashing with unique salts, Flask session cookies, HttpOnly/SameSite flags, and CSRF protection. | Maintain secret key environment variable in production. |
| **1.4 Academic Terms & Departments** | **Verified Complete** | `AcademicTerm` and `Department` models with institutional header switcher and relational term partitioning operational. | None. Fully functional. |
| **1.5 RBAC Endpoint Middleware** | **Verified Complete** | Server-side `@login_required` and `@require_role(...)` decorators guard all operational endpoints (401/403 responses). | None. Verified complete with 20 targeted tests. |

---

### Phase 2: Operational Workflows & Governance

| Milestone | Status | Reality in Codebase | Next Action Required |
| :--- | :---: | :--- | :--- |
| **2.1 Multi-Variant Candidate Generation** | **Verified Complete** | `scheduler.py:solve_multiple` generates diverse candidate timetables; UI comparison grid renders Pareto scores and diversity divergence. | None. Fully functional. |
| **2.2 Publishing Lifecycle State Machine** | **Verified Complete** | `DRAFT` vs `PUBLISHED` state tracking with UTC timestamps via `/api/timetable/publish` and `/api/timetable/unpublish`. | None. Fully functional. |
| **2.3 Excel Timetable Exporter** | **Verified Complete** | `exporter.py` outputs formatted multi-tab spreadsheets (`Master`, `Sections`, `Faculty`, `Rooms`) with theory/lab color coding. | None. Fully functional. |
| **2.4 Interactive Manual Adjustments** | **Verified Complete** | `adjuster.py` dry-run validation, atomic moves, and atomic swaps with duration, room suitability, capacity, and hard constraints. | None. Verified complete with 41 passing automated tests. |
| **2.5 Schedule Snapshot Versioning** | **Pending (Milestone C)** | Single active publishing status record exists. Previous schedule iterations are overwritten upon re-generation. | Create version snapshot table/store (`v1.0`, `v1.1`) allowing administrators to view changelogs and revert versions. |

---

### Phase 3: Multi-Portal Stakeholder Experience

| Milestone | Status | Reality in Codebase | Next Action Required |
| :--- | :---: | :--- | :--- |
| **3.1 Public Student Timetable Portal** | **Verified Complete** | Dedicated read-only portal at `/portal` with section/faculty/room views, live search query filtering, and Excel export. | None. Fully functional and verified. |
| **3.2 Faculty Portal & iCalendar Feeds** | **Pending (Milestone C)** | Dedicated instructor view (`/faculty/my-schedule`) and subscribed `.ics` calendar feed endpoints are not implemented. | Create personalized faculty view and dynamic RFC 5545 iCalendar endpoint (`/api/faculty/<id>/calendar.ics`). |
| **3.3 Change Notification System** | **Deferred** | No event-driven email or webhook notification engine exists for schedule alterations. | Deferred until core stability and faculty portal are established. |

---

### Phase 4: Institutional SaaS (Deferred)

Milestones in Phase 4 (Multi-Tenant Row-Level Security, SAML 2.0 / Enterprise SSO, Celery Asynchronous Solver Worker Pools, and Commercial Marketing Website) remain **deferred**. Building multi-tenant infrastructure before completing local relational persistence and multi-term partitioning is premature.

---

## 3. Recommended Development Priorities

With **Milestone A complete and verified**, the development path proceeds to the next sequential milestones:

### Milestone A: Seam Restoration & Access Control Hardening [COMPLETED & VERIFIED]
- **Status:** **Completed & Verified**.
- **Delivered:**
  1. Restored engine seam for manual adjustments (`_get_scheduling_strength`, `_check_hard_constraints`, `_get_session_duration`).
  2. Integrated room suitability and cohort capacity verification into session swaps.
  3. Implemented server-side authentication and role-based authorization middleware (`@login_required`, `@require_role`).
  4. Implemented anti-CSRF token verification on cookie-authenticated mutation endpoints.
  5. Enforced session cookie security flags and 16MB file upload ceiling.
  6. Added 20 automated tests in `test_milestone_a.py`. All 41 tests pass (100% pass rate).

---

### Milestone B: Relational Persistence & DBMS Integration [COMPLETED & VERIFIED]
- **Status:** **Completed & Verified**.
- **Delivered:**
  1. Implemented normalized relational schema in `db_models.py` (14 tables, foreign keys with ON DELETE CASCADE rules, unique constraints, composite indexes).
  2. Implemented SQLite as default primary persistence layer in `autoschedule.db` with support for PostgreSQL via `DATABASE_URL`.
  3. Created `migrate_json_to_db.py` data migration engine with dry-run mode, timestamped backups, duplicate detection, and referential integrity verification.
  4. Decoupled in-memory solver dataclasses from relational models while providing transactional persistence and rollback protection.
  5. Produced academic demonstration deliverables: `DATABASE_DESIGN.md` (with Mermaid ER diagram), `DATABASE_SETUP.md` (PowerShell operations), and `DBMS_DEMONSTRATION.md` (real SQL queries, joins, aggregations, EXPLAIN QUERY PLAN benchmarks).
  6. Added 10 automated integration tests in `test_dbms_integration.py`. All 51 platform tests pass.

---

### Milestone C: Schedule Snapshot Versioning & Faculty Calendar Feeds [COMPLETED & VERIFIED]
- **Status:** **Completed & Verified**.
- **Delivered:**
  1. Implemented snapshot version listing (`GET /api/timetable/versions`), named snapshot capture (`POST /api/timetable/versions/snapshot`), and atomic rollback (`POST /api/timetable/versions/<id>/restore`) in `database.py` and `app.py`.
  2. Integrated interactive "Version History" modal (`#modal-version-history`) into Timetable Views with quality score badges, session counts, and one-click rollback.
  3. Created `calendar_feed.py` implementing RFC 5545 iCalendar stream generation (`GET /api/faculty/<id>/calendar.ics`) with recurring events (`RRULE:FREQ=WEEKLY`), course details, room allocations, and access control.
  4. Added "Subscribe Calendar (.ics)" button across administrative and public portal faculty schedule views.
  5. Added 10 automated integration tests in `test_milestone_c.py`. All 61 platform tests pass (100% pass rate).

---

## 4. Next Step Recommendation

**Recommendation:** The core academic scheduling platform (Milestones A, B, and C) is now fully realized, robust, and verified with 61 automated tests. The next logical enhancements are:
1. **Milestone D: Faculty Self-Service Portal & Change Notification System:**
   - Dedicated authenticated faculty portal (`/faculty/dashboard`) showing individual weekly workload metrics, room details, and student rosters.
   - Schedule change alert logs summarizing moved or rescheduled sessions.
2. **Milestone E: Institutional Multi-Department Reporting:**
   - Dean/HOD cross-department resource utilization summaries and conflict-free room sharing dashboards.
