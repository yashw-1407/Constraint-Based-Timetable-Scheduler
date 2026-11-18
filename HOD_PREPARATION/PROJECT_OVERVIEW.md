# CampusGrid — Project Overview
## Constraint-Based Academic Timetable Scheduling System

---

### 1. What Problem Are We Solving?

Every semester in an engineering college, the Head of Department (HOD) and timetable coordinators face a logistical nightmare: **building the academic timetable**.

Imagine trying to schedule:
- **60+ weekly lectures and lab sessions**
- Across **4 semesters/sections** (e.g., 3A, 3B, 5A, 5B)
- Involving **20 faculty members**
- Using **8 physical rooms** (classrooms and specialized computer/hardware labs)
- Over **5 working days** (Monday to Friday, 9:00 AM to 5:00 PM)

#### The Core Problem:
If done by hand on paper or an Excel sheet, humans inevitably run into collisions:
1. **Faculty Clash**: Prof. Sharma is scheduled to teach *Data Structures* to Section 3A and *Operating Systems* to Section 5A at the exact same hour on Tuesday morning.
2. **Room Clash**: Two different classes show up at Room 101 at 10:00 AM.
3. **Student Section Clash**: Section 3A is assigned two different classes in the same time slot.
4. **Lab Batch Clash**: Batch A1 and Batch A2 have labs scheduled without enough lab rooms or faculty assistants.
5. **Physical Impossibility**: A 2-hour practical lab is scheduled across the lunch break (e.g., 12:30 PM to 2:30 PM when lunch is 1:00 PM to 2:00 PM).

---

### 2. Why Is Manual Timetable Creation Difficult?

In computer science, academic timetabling is proven to be **NP-Complete** (Nondeterministic Polynomial-time Complete). 

#### A. Combinatorial Explosion
If you have:
- 70 class sessions to schedule
- 35 possible time slots in a week (7 periods/day $\times$ 5 days)
- 8 rooms

The total number of possible combinations to test is:
$$(35 \times 8)^{70} = 280^{70} \approx 10^{171}$$

There are only about $10^{80}$ atoms in the observable universe! Even a supercomputer testing every combination one-by-one would take billions of years.

#### B. The Domino Effect
When a coordinator makes a timetable manually:
- They place Class A on Monday at 9:00 AM.
- After 4 hours of work, on Thursday at 3:00 PM, they realize Dr. Gupta has no free room.
- Changing one single class forces them to erase and move 15 other classes — like pulling a block from a Jenga tower.

#### C. Conflicting Objectives (Hard vs. Soft Constraints)
- **Hard Constraints** (Non-negotiable): No double-booking of teachers, rooms, or students.
- **Soft Constraints** (Quality & Comfort): Don't give students 3 idle hours between classes; don't give teachers 4 continuous hours of lecture without rest; don't put the same difficult math subject twice on Monday. Humans struggle to satisfy hard constraints, let alone optimize soft ones.

---

### 3. What Is Our Proposed Solution?

Our project, **CampusGrid**, is an automated academic scheduling platform built on:
1. **Constraint Satisfaction Problem (CSP)** mathematical modeling.
2. **Backtracking Search** with intelligent heuristics (**Minimum Remaining Values / MRV** and **Least Constraining Value**).
3. **Domain Filtering & Forward Pruning** (eliminating impossible slots before exploring them).
4. **SQLite Persistence Engine** for data durability.
5. **Lightweight Flask Backend & Responsive Single-Page UI** requiring zero external cloud services.

Instead of blind trial and error, our algorithm:
1. Identifies the hardest, most constrained sessions first (e.g., 2-hour practical lab sessions requiring specific computer labs).
2. Calculates the remaining legal slots for each session.
3. Places sessions one by one, immediately detecting conflicts.
4. Backtracks intelligently as soon as a branch is proven dead, pruning millions of invalid branches in milliseconds.
5. Computes a comprehensive **Soft Constraint Quality Score (0–100%)** evaluating student idle gaps, teacher workload balance, and room utilization.

---

### 4. Who Benefits From It?

| Stakeholder | Real-Life Benefit |
| :--- | :--- |
| **HOD / Dean** | Eliminates weeks of manual coordination; generates a provably conflict-free schedule in under 1 second. |
| **Timetable Committee** | Bulk import faculty, room, and course data via Excel (`.xlsx`), click one button to generate, and export printable timetables. |
| **Faculty Members** | Guaranteed zero overlapping classes; workload balanced evenly across days; avoids more than 3 consecutive teaching hours. |
| **Students** | Zero room clashes; minimal idle gap periods between classes; theory and lab batches run smoothly in parallel. |

---

### 5. Verified Codebase Features

Here is what is **actually implemented** in our source code (no exaggerations):

- **Configurable College Working Hours**: Configure active days (e.g. Mon–Fri or Mon–Sat), day start time, day end time, period slot duration (e.g. 60 mins), custom break periods, and dedicated lunch windows.
- **Room Management**: Support for `THEORY_ROOM` and `LAB`, seating capacity checks, and building/department categories.
- **Faculty Directory**: Unique faculty IDs and names.
- **Academic Sections & Sub-Batches**: Configure semester, division, class student strength, and sub-batches (e.g., Section 3A divided into A1, A2 for practicals).
- **L-T-P Course Model**: Supports standard university Lecture (L), Tutorial (T), and Practical (P) credit hours. Theory hours automatically translate into 1-hour sessions; practical hours translate into contiguous multi-slot lab sessions for sub-batches with primary and assistant faculty.
- **Excel Bulk Import & Export**: One-click download of a pre-formatted Excel template (`timetable_import_template.xlsx`) and bulk upload parsing 5 worksheets (`Faculty`, `Rooms`, `Sections`, `Batches`, `Courses`).
- **Interactive Multi-View Timetable Viewer**:
  - **Master View**: Complete department grid of all scheduled sessions.
  - **By Section View**: Weekly timetable grid filtered by semester/division.
  - **By Faculty View**: Weekly timetable grid filtered for an individual teacher.
  - **By Room View**: Weekly timetable grid showing occupancy of any classroom or lab.
- **Conflict Validation Engine**: An independent mathematical audit (`/api/validation`) verifying zero faculty overlaps, zero room overlaps, zero section overlaps, room suitability, and capacity compliance.
- **Quality Scoring Dashboard**: Soft constraint score broken down across 7 criteria with progress bars and percentage calculations.
- **Built-In Demo Scenarios**: Instant one-click testing using `Standard`, `Single Section`, `Bottleneck`, or `Infeasible` datasets.
