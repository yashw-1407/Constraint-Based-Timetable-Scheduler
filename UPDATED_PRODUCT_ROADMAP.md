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
├── RBAC Enforcement [PARTIAL/BLOCKED]    ├── Manual Adjustments [BLOCKED/REGRESS] └── Mobile PWA Polish [PENDING]        └── Commercial Marketing Site [PENDING]
└── Relational Database [MISSING]         └── Schedule Versioning [MISSING]
```

---

## 2. Phase-by-Phase Status & Gap Breakdown

### Phase 1: Core Platform Foundation

| Milestone | Status | Reality in Codebase | Next Action Required |
| :--- | :---: | :--- | :--- |
| **1.1 Relational Persistence (SQLAlchemy)** | **Missing** | Still using flat-file `database.json`. No SQLAlchemy models, ORM session, or migrations exist. | Implement SQLite via SQLAlchemy ORM; support concurrent file safety and relational queries. |
| **1.2 Bulk Excel Ingestion Pipeline** | **Verified Complete** | `importer.py` validates multi-sheet workbooks (`Rooms`, `Faculty`, `Sections`, `Batches`, `Courses`) with dry-run error collection. | None for core ingestion. Secure the upload route via RBAC middleware. |
| **1.3 User Authentication & Sessions** | **Verified Complete** | PBKDF2-HMAC-SHA256 password hashing with unique salts, Flask session cookies, and Sign-In modal with quick-login buttons. | Add session cookie security flags (`HttpOnly`, `SameSite=Lax`, `Secure` in prod) and CSRF protection. |
| **1.4 Academic Terms & Departments** | **Verified Complete** | `AcademicTerm` and `Department` models with institutional header switcher operational. | Extend from metadata switching to true term partitioning of course catalogs and assignments. |
| **1.5 RBAC Endpoint Middleware** | **Partially Implemented** | User roles (`ADMIN`, `COORDINATOR`, `FACULTY`, `STUDENT`) exist in models and frontend badges, but backend endpoints lack route protection. | Create `@login_required` and `@require_role` decorators and apply to administrative/destructive endpoints. |

---

### Phase 2: Operational Workflows & Governance

| Milestone | Status | Reality in Codebase | Next Action Required |
| :--- | :---: | :--- | :--- |
| **2.1 Multi-Variant Candidate Generation** | **Verified Complete** | `scheduler.py:solve_multiple` generates diverse candidate timetables; UI comparison grid renders Pareto scores and diversity divergence. | None. Fully functional. |
| **2.2 Publishing Lifecycle State Machine** | **Verified Complete** | `DRAFT` vs `PUBLISHED` state tracking with UTC timestamps via `/api/timetable/publish` and `/api/timetable/unpublish`. | None. Fully functional. |
| **2.3 Excel Timetable Exporter** | **Verified Complete** | `exporter.py` outputs formatted multi-tab spreadsheets (`Master`, `Sections`, `Faculty`, `Rooms`) with theory/lab color coding. | None. Fully functional. |
| **2.4 Interactive Manual Adjustments** | **Blocked / Regression** | `adjuster.py` implements two-phase commit move and swap, but recent streamlining of `scheduler.py` in `8121f15` removed `_get_scheduling_strength` and `_check_hard_constraints`. | Re-implement or bridge the missing validation methods in `SchedulingEngine` to restore move and swap operations (fixes `test_16`, `test_17`). |
| **2.5 Schedule Snapshot Versioning** | **Missing** | Only a single publishing status record exists. Previous schedule iterations are overwritten upon re-generation or adjustment. | Create version snapshot table/store (`v1.0`, `v1.1`) allowing administrators to view changelogs and revert to previous versions. |

---

### Phase 3: Multi-Portal Stakeholder Experience

| Milestone | Status | Reality in Codebase | Next Action Required |
| :--- | :---: | :--- | :--- |
| **3.1 Public Student Timetable Portal** | **Verified Complete** | Dedicated read-only portal at `/portal` with section/faculty/room views, live search query filtering, and Excel export. | None. Fully functional and verified. |
| **3.2 Faculty Portal & iCalendar Feeds** | **Missing** | Dedicated instructor view (`/faculty/my-schedule`) and subscribed `.ics` calendar feed endpoints are not implemented. | Create personalized faculty view and dynamic RFC 5545 iCalendar endpoint (`/api/faculty/<id>/calendar.ics`). |
| **3.3 Change Notification System** | **Missing** | No event-driven email or webhook notification engine exists for schedule alterations. | Deferred until core stability and faculty portal are established. |

---

### Phase 4: Institutional SaaS (Deferred)

Milestones in Phase 4 (Multi-Tenant Row-Level Security, SAML 2.0 / Enterprise SSO, Celery Asynchronous Solver Worker Pools, and Commercial Marketing Website) remain **deferred**. Building multi-tenant infrastructure before completing local relational persistence and route authorization is premature.

---

## 3. Recommended Development Priorities

Based on rigorous codebase verification, the following three sequential milestones represent the highest return on investment for institutional readiness:

### Milestone A: Seam Restoration & Access Control Hardening (Immediate Next Step)
- **Objective:** Fix the current regression in manual timetable adjustments and eliminate the critical security vulnerability of unprotected administrative endpoints.
- **Scope of Work:**
  1. **Restore Engine Seam for Adjustments:** Implement or bridge `_check_hard_constraints(session, day, slot_indices, room_id)` and `_get_scheduling_strength(session)` in `scheduler.py` so that `adjuster.py` executes conflict validation cleanly. Restore 21/21 passing tests in `test_suite.py`.
  2. **Implement RBAC Middleware:** Create `@login_required` and `@require_role([UserRole.ADMIN, UserRole.COORDINATOR])` decorators in `app.py`. Enforce them across all mutation and administrative endpoints:
     - Configuration: `/api/config` (POST)
     - Resource CRUD: `/api/rooms`, `/api/faculty`, `/api/sections`, `/api/batches`, `/api/courses`
     - Solver Execution: `/api/generate`, `/api/generate-multiple`
     - Publishing & Adjustments: `/api/timetable/publish`, `/api/timetable/unpublish`, `/api/timetable/move`, `/api/timetable/swap`
     - System Maintenance: `/api/clear`, `/api/import/excel`, `/api/auth/users` (POST)
  3. **UI Role Adaptability:** In `static/app.js`, hide or disable configuration controls, clear buttons, and import modals when authenticated as `FACULTY` or `STUDENT`.
- **Estimated Effort:** Small (1 focused turn).
- **Prerequisites:** None.

---

### Milestone B: Relational Persistence & Multi-Term Schedule Partitioning
- **Objective:** Transition from flat-file JSON serialization to SQLite via SQLAlchemy, enabling true concurrent file safety and isolated academic term schedules.
- **Scope of Work:**
  1. **SQLAlchemy Schema Migration:** Define declarative models (`Institution`, `AcademicTerm`, `Department`, `Room`, `Faculty`, `Section`, `Batch`, `Course`, `TimetableAssignment`, `User`).
  2. **Multi-Term Assignment Isolation:** Add `academic_term_id` foreign key to `Course` and `TimetableAssignment`. When switching terms in the header, query and display that specific semester's independent timetable.
  3. **Automated Migration / Seed Utility:** Automatically import existing `database.json` records into SQLite on startup so existing demo datasets continue working seamlessly.
- **Estimated Effort:** Medium (1–2 focused turns).
- **Prerequisites:** Milestone A.

---

### Milestone C: Schedule Snapshot Versioning & Faculty Calendar Feeds
- **Objective:** Provide auditable change governance for schedulers and mobile calendar integration for instructors.
- **Scope of Work:**
  1. **Schedule Version History:** Implement snapshot storage (`v1.0 Published`, `v1.1 Adjusted`) capturing timestamp, user ID, note, and assignment payload. Add rollback endpoint (`POST /api/timetable/versions/<id>/restore`).
  2. **Version History Modal:** Add interactive version drawer in the Timetable Views tab showing previous publications and diff summaries.
  3. **Faculty iCalendar (`.ics`) Feed:** Generate standard RFC 5545 iCalendar feeds (`GET /api/faculty/<id>/calendar.ics`) allowing professors to subscribe to their schedule directly in Google Calendar, Outlook, and Apple Calendar.
- **Estimated Effort:** Medium (1–2 focused turns).
- **Prerequisites:** Milestone B.

---

## 4. Next Step Recommendation

**Recommendation:** Proceed immediately with **Milestone A: Seam Restoration & Access Control Hardening**.

This milestone:
1. Restores `adjuster.py` functionality and brings the test suite back to 100% passing (21/21 tests).
2. Closes the major security gap where unauthenticated visitors can delete data or trigger solver runs.
3. Requires zero architectural redesign and operates strictly within existing application structures.

*Awaiting approval to begin Milestone A implementation.*
