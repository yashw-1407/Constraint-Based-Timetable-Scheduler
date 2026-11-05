# AutoSchedule: Phased Product Implementation Roadmap

**Architecture Strategy:** Evolutionary Migration from Standalone Engine to Enterprise SaaS  
**Delivery Framework:** 4 Distinct Phases with Strict Dependency Sequencing  
**Guiding Principle:** Protect and build around the verified pure-Python CSP core engine.

---

## 1. Roadmap Overview & Timeline Phasing

```
[Phase 1: Core Platform MVP] ──> [Phase 2: Operational Workflows] ──> [Phase 3: Stakeholder Portals] ──> [Phase 4: Enterprise SaaS]
├── Relational DB (SQLAlchemy)    ├── Excel / PDF Exporters          ├── Student Schedule Portal       ├── Multi-Tenant DB Schema
├── Data Import Pipeline (Excel)  ├── Manual Drag-and-Drop Editor    ├── Faculty Portal & Calendar     ├── SSO / SAML 2.0 Auth
├── Term & Department Hierarchy   ├── Schedule Publishing Lifecycle  ├── Mobile PWA Experience         ├── Audit Logging Engine
└── User Auth & Session Security  └── Multi-Variant Candidate UI     └── Notification Dispatch Engine  └── Commercial Billing & Tiering
```

---

## 2. Phase 1: Essential Core Platform MVP (Foundation & Data Ingestion)

*Objective:* Convert the localized single-file demo application into an authenticated, durable, relational multi-department scheduler with automated data import.

### 1.1 Relational Persistence Migration
- **Technical Work:**
  - Replace flat-file `database.json` with SQLAlchemy ORM abstraction.
  - Support SQLite for zero-config local development and PostgreSQL for production deployments.
  - Create formal relational schemas: `institutions`, `academic_terms`, `departments`, `rooms`, `faculty`, `sections`, `batches`, `courses`, `assignments`.
  - Implement Alembic database migrations to enable seamless future schema evolution.
- **Dependency:** In progress for future PostgreSQL cloud release.

### 1.2 Bulk Excel & CSV Import Pipeline [COMPLETED & VERIFIED]
- **Technical Work:**
  - Implemented server-side Excel ingestion service in `importer.py` using `openpyxl`.
  - Provided standardized Excel template generator (`/api/import/template`) containing sheets for Rooms, Faculty, Sections, Batches, and Courses.
  - Built front-end Import Modal (`#modal-import`) with file upload, ingestion mode (replace/append), and dry-run validation error report.
  - Referential integrity checks catch foreign key mismatches, duplicate codes, and invalid L-T-P ratios before database insertion. Verified in `test_12`.
- **Value:** Reduces institutional setup time from hours of manual entry to under 5 minutes.

### 1.3 User Authentication & Basic Session Security [COMPLETED & VERIFIED]
- **Technical Work:**
  - Implemented secure user authentication with salted PBKDF2-HMAC-SHA256 password hashing (100,000 iterations).
  - Built session management with role-based identities (`ADMIN`, `COORDINATOR`, `FACULTY`, `STUDENT`).
  - Seeded initial credentials (`admin` / `admin123`, `coordinator` / `coord123`, `faculty` / `faculty123`).
  - Integrated Header User Badge and Sign-In modal (`#modal-auth`) with quick-switch demo accounts. Verified in `test_21`.
- **Value:** Prevents unauthorized tampering and establishes user accountability.

### 1.4 Academic Hierarchy (Terms & Departments) [COMPLETED & VERIFIED]
- **Technical Work:**
  - Introduced `AcademicTerm` (`id`, `name`, `academic_year`, `semester_type`, `is_active`) and `Department` (`id`, `name`, `code`).
  - Added active Term Switcher dropdown in the institutional header.
  - Synchronized publishing metadata with active term activation. Verified in `test_18` and `test_19`.
- **Value:** Allows institutions to store past terms for accreditation and prepare future schedules concurrently.

---

## 3. Phase 2: Operational Workflows & Timetable Publishing

*Objective:* Provide schedulers with candidate comparison, interactive manual adjustments, schedule publishing governance, and formatted export files.

### 2.1 Excel & Vector PDF Schedule Exporters [COMPLETED & VERIFIED]
- **Technical Work:**
  - Built server-side Excel workbook generator in `exporter.py` (`/api/export/excel`) creating multi-tab spreadsheets:
    - Master Grid sheet.
    - Individual Section schedules formatted with cell borders and theory/lab fills.
    - Faculty schedules.
    - Room schedules.
  - Dedicated `@media print` optimization for crisp printable institutional schedules. Verified in `test_13`.
- **Value:** Delivers the primary output expected by academic registrars and college notice boards.

### 2.2 Interactive Manual Adjustment Canvas [COMPLETED & VERIFIED]
- **Technical Work:**
  - Built interactive session relocation modal in `adjuster.py` and `app.js`.
  - Created backend validation endpoint `/api/timetable/validate-move`:
    - Evaluates whether moving a session violates any of the 6 hard constraints.
    - Highlights valid candidate slots in green; highlights conflict collisions with detailed diagnostic explanations.
  - Created atomic move (`/api/timetable/move`) and two-phase commit swap (`/api/timetable/swap`) endpoints. Verified in `test_16` and `test_17`.
- **Value:** Empowers administrators to handle real-world adjustments without breaking conflict guarantees.

### 2.3 Schedule Publishing Lifecycle & Versioning [COMPLETED & VERIFIED]
- **Technical Work:**
  - Implemented schedule lifecycle states (`DRAFT` vs `PUBLISHED`) with atomic UTC timestamps.
  - Created `/api/timetable/publish` and `/api/timetable/unpublish` endpoints.
  - Dynamic status chips in header and views toolbar. Verified in `test_15`.
- **Value:** Protects campus stakeholders from seeing work-in-progress scheduling experiments.

### 2.4 Multi-Candidate Variant Comparison [COMPLETED & VERIFIED]
- **Technical Work:**
  - Connected `/api/generate-multiple` engine to the candidate comparison grid (`#variants-grid`).
  - Presents candidate alternatives with Pareto diversity divergence and soft quality scores:
    - Faculty Workload Balance.
    - Student Free Period Minimization.
    - Subject Daily Spread.
    - Room Utilization Efficiency.
  - Allows coordinator to activate preferred candidates with one click. Verified in `test_14`.
- **Value:** Transforms timetable generation from an opaque black box into an executive decision support tool.

---

## 4. Phase 3: Multi-Portal Stakeholder Experience

*Objective:* Expand access to faculty and students through dedicated, lightweight, mobile-responsive consumer interfaces.

### 4.1 Student Class Timetable Portal [COMPLETED & VERIFIED]
- **Technical Work:**
  - Created public/student route `/portal` (`templates/portal.html`) requiring zero administrative permissions.
  - 3-click selector: View by Section, View by Faculty, View by Room, or Master View.
  - Real-time search query box to locate courses, rooms, or instructors instantly.
  - Displays published status notice and provides one-click Excel download and print options. Verified in `test_20`.
- **Value:** Eliminates student confusion and paper schedule distribution bottlenecks.

### 4.2 Faculty Portal & Subscribed Calendar Feeds
- **Technical Work:**
  - Create instructor view `/faculty/my-schedule` filtered to authenticated instructor.
  - Implement dynamic iCalendar (`.ics`) feed endpoint allowing professors to subscribe to their teaching schedule in Google Calendar, Outlook, and Apple Calendar.
  - Any administrative room change automatically updates the professor's phone calendar.
- **Value:** Drastically reduces missed lectures and faculty room confusion.

### 4.3 Change Notification System
- **Technical Work:**
  - Event-driven webhook / email dispatcher triggering on timetable publication or manual adjustments.
  - Sends targeted digest alerts to affected faculty: *"Notice: Your CS301 lab on Friday has been relocated from Room 101 to Lab 2."*
- **Value:** Provides proactive communication during initial add/drop weeks.

---

## 5. Phase 4: Multi-Tenant Enterprise Commercial SaaS

*Objective:* Enable cloud hosting, commercial monetization, institutional single sign-on, and cross-campus deployment.

### 5.1 Multi-Tenant Database Architecture
- **Technical Work:**
  - Transition persistence model to multi-tenant row-level security (RLS) in PostgreSQL or schema-per-tenant isolation.
  - Tenant resolution via subdomain (e.g., `kle.autoschedule.com`, `mit.autoschedule.com`).
  - Total logical and data isolation between competing universities.
- **Value:** Enables AutoSchedule to operate as a scalable, commercially viable B2B SaaS platform.

### 5.2 Enterprise Single Sign-On (SSO / SAML 2.0 / OAuth2)
- **Technical Work:**
  - Integrate SAML 2.0 and OpenID Connect (OIDC) protocols.
  - Support institutional identity providers: Microsoft Azure AD / Office 365, Google Workspace for Education, and Okta.
  - Automatic provisioning of faculty and student roles from campus directory groups.
- **Value:** Mandatory security prerequisite for enterprise university procurement.

### 5.3 Asynchronous Solver Queue & Worker Pool
- **Technical Work:**
  - Decouple scheduling engine execution from web server threads using Celery / Redis Queue.
  - Spin up dedicated compute worker nodes for executing large-scale campus solves (500+ courses across multiple schools).
  - Stream real-time solver telemetry to browser using WebSockets or Server-Sent Events (SSE).
- **Value:** Prevents web server degradation during peak scheduling season.

### 5.4 Public Commercial Marketing Website
- **Technical Work:**
  - Build public marketing website matching Hallmark design system.
  - Pages: Feature tour, Algorithm Whitepaper, Interactive Demo Request, Case Studies, Pricing Calculator.
  - Lead capture integration with CRM (HubSpot / PostHog).
- **Value:** Drives organic institutional inbound discovery and commercial sales pipeline.

---

## 6. Implementation Prioritization Matrix

| Phase | Milestone Name | Technical Complexity | Business Value | Prerequisites |
| :---: | :--- | :---: | :---: | :--- |
| **1.1** | Relational Database (SQLAlchemy) | Medium | Critical | None |
| **1.2** | Excel & CSV Import Pipeline | Medium | Critical | Phase 1.1 |
| **1.3** | User Authentication & Sessions | Medium | High | Phase 1.1 |
| **1.4** | Term & Department Hierarchy | Low | High | Phase 1.1 |
| **2.1** | Excel & PDF Timetable Exports | Medium | Critical | Phase 1.1 |
| **2.2** | Manual Drag-and-Drop Editor | High | High | Phase 2.1 |
| **2.3** | Publishing Lifecycle (Draft/Pub) | Low | High | Phase 1.4 |
| **2.4** | Multi-Variant Comparison UI | Medium | Medium | Phase 1.1 |
| **3.1** | Student Timetable Portal | Low | High | Phase 2.3 |
| **3.2** | Faculty Portal & iCal Feeds | Medium | High | Phase 2.3 |
| **3.3** | Change Notification Dispatch | Medium | Medium | Phase 3.2 |
| **4.1** | Multi-Tenancy Architecture | High | Critical for SaaS | Phase 1.1 |
| **4.2** | Enterprise SSO / SAML | High | High | Phase 4.1 |
| **4.3** | Asynchronous Solver Worker Pool| High | High | Phase 1.1 |
| **4.4** | Public Commercial Website | Low | Commercial Growth | None |

