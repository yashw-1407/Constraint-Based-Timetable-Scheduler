# AutoSchedule — Relational DBMS Demonstration & SQL Query Reference

This document demonstrates the relational database management system capabilities of AutoSchedule using live SQL queries executed against `autoschedule.db`.

---

## 1. Basic Data Manipulation (CRUD)

### 1.1 Create: Insert a New Room
```sql
INSERT INTO rooms (id, name, room_type, capacity, category, department_id)
VALUES ('R305', 'Embedded Systems Lab', 'LAB', 36, 'Hardware Lab', 'dept_ece');
```

### 1.2 Read: Retrieve Department Rooms
```sql
SELECT id, name, room_type, capacity, category
FROM rooms
WHERE department_id = 'dept_ece';
```

### 1.3 Update: Modify Room Capacity
```sql
UPDATE rooms
SET capacity = 40
WHERE id = 'R305';
```

### 1.4 Delete: Remove Room
```sql
DELETE FROM rooms
WHERE id = 'R305';
```

---

## 2. Multi-Table JOIN Queries

### 2.1 Course Hierarchy: Courses, Cohorts, Departments, and Instructors
Demonstrates joining four relational tables (`courses`, `sections`, `departments`, `course_faculty`, and `faculty`) with multi-instructor string aggregation:

```sql
SELECT 
    c.code AS course_code,
    c.name AS course_name,
    s.name AS section_name,
    s.semester AS semester,
    COALESCE(d.name, 'Cross-Department') AS department_name,
    c.l AS lecture_hours,
    c.p AS lab_hours,
    GROUP_CONCAT(f.name, ', ') AS assigned_instructors
FROM courses c
JOIN sections s ON c.section_id = s.id
LEFT JOIN departments d ON s.department_id = d.id
LEFT JOIN course_faculty cf ON c.id = cf.course_id
LEFT JOIN faculty f ON cf.faculty_id = f.id
GROUP BY c.id
ORDER BY s.semester, c.code;
```

**Sample Output:**
```text
course_code | course_name             | section_name | semester | department_name                  | lecture_hours | lab_hours | assigned_instructors
CS301       | Data Structures         | 3A           | 3        | Computer Science & Engineering   | 3.0           | 0.0       | Dr. Sarah Jenkins
CS302       | Discrete Mathematics    | 3A           | 3        | Computer Science & Engineering   | 3.0           | 0.0       | Prof. Michael Chen
CS303       | Digital Logic Design    | 3A           | 3        | Computer Science & Engineering   | 3.0           | 0.0       | Dr. Priya Sharma
CS304       | Data Structures Lab     | 3A           | 3        | Computer Science & Engineering   | 0.0           | 3.0       | Dr. Sarah Jenkins
```

---

### 2.2 Operational Timetable Schedule JOIN
Resolves session ID, course title, room name, and section name for Monday classes:

```sql
SELECT 
    a.day,
    a.start_slot_index AS slot,
    c.code AS course_code,
    c.name AS course_name,
    r.name AS room_name,
    s.name AS section_name,
    f.name AS lead_faculty
FROM timetable_assignments a
JOIN courses c ON a.course_id = c.id
JOIN rooms r ON a.room_id = r.id
JOIN sections s ON a.section_id = s.id
LEFT JOIN course_faculty cf ON (c.id = cf.course_id AND cf.is_assistant = 0)
LEFT JOIN faculty f ON cf.faculty_id = f.id
WHERE a.academic_term_id = 'term_2026_fall' AND a.day = 'Monday'
GROUP BY a.id
ORDER BY a.start_slot_index, r.name;
```

---

## 3. Analytical Aggregations & Institutional Metrics

### 3.1 Faculty Weekly Workload (Teaching Hours Distribution)
Aggregates scheduled weekly contact hours per faculty member to verify compliance with institutional workload policies:

```sql
SELECT 
    f.id AS faculty_id,
    f.name AS faculty_name,
    COUNT(DISTINCT c.id) AS course_count,
    ROUND(SUM(c.l + c.t + c.p), 1) AS weekly_teaching_hours
FROM faculty f
LEFT JOIN course_faculty cf ON f.id = cf.faculty_id
LEFT JOIN courses c ON cf.course_id = c.id
GROUP BY f.id
ORDER BY weekly_teaching_hours DESC;
```

**Sample Output:**
```text
faculty_id | faculty_name        | course_count | weekly_teaching_hours
FAC001     | Dr. Sarah Jenkins   | 2            | 6.0
FAC002     | Prof. Michael Chen  | 2            | 6.0
FAC003     | Dr. Priya Sharma    | 2            | 6.0
FAC004     | Prof. David Wilson  | 2            | 6.0
FAC005     | Dr. Anita Desai     | 2            | 6.0
FAC006     | Prof. James Miller  | 2            | 6.0
FAC007     | Dr. Robert Taylor   | 2            | 6.0
FAC008     | Prof. Sunita Rao    | 2            | 6.0
```

---

### 3.2 Classroom & Laboratory Utilization Rate
Calculates room utilization percentages across a standard 40-slot weekly schedule (5 days × 8 slots/day):

```sql
SELECT 
    r.id AS room_id,
    r.name AS room_name,
    r.room_type,
    r.capacity,
    COUNT(a.id) AS occupied_slots,
    ROUND((COUNT(a.id) * 100.0) / 40.0, 1) AS utilization_percentage
FROM rooms r
LEFT JOIN timetable_assignments a ON r.id = a.room_id AND a.academic_term_id = 'term_2026_fall'
GROUP BY r.id
ORDER BY occupied_slots DESC;
```

**Sample Output:**
```text
room_id | room_name      | room_type   | capacity | occupied_slots | utilization_percentage
R101    | Room 101       | THEORY_ROOM | 60       | 13             | 32.5%
R102    | Room 102       | THEORY_ROOM | 60       | 12             | 30.0%
R201    | Room 201       | THEORY_ROOM | 60       | 12             | 30.0%
R202    | Room 202       | THEORY_ROOM | 60       | 11             | 27.5%
L101    | Computing Lab  | LAB         | 30       | 6              | 15.0%
L102    | Hardware Lab   | LAB         | 30       | 6              | 15.0%
```

---

### 3.3 Cohort Double-Booking & Clash Verification
Audits the operational schedule to guarantee that no student section has more than one session scheduled in the same time slot:

```sql
SELECT 
    a.academic_term_id,
    a.day,
    a.start_slot_index,
    a.section_id,
    COUNT(*) AS simultaneous_sessions
FROM timetable_assignments a
WHERE a.academic_term_id = 'term_2026_fall'
GROUP BY a.academic_term_id, a.day, a.start_slot_index, a.section_id
HAVING simultaneous_sessions > 1;
```

**Expected Result:** Empty set (0 rows). Confirms absolute enforcement of cohort disjointness constraints.

---

## 4. Query Optimization & `EXPLAIN QUERY PLAN`

AutoSchedule indexes high-frequency query paths to prevent sequential table scans during interactive timetable adjustments and portal queries.

### 4.1 Room Slot Collision Check (Optimized with Composite Index)
Execution plan inspection on the composite index `idx_assign_term_day_slot_room`:

```sql
EXPLAIN QUERY PLAN
SELECT id, session_id, room_id
FROM timetable_assignments
WHERE academic_term_id = 'term_2026_fall' 
  AND day = 'Monday' 
  AND start_slot_index = 0 
  AND room_id = 'R101';
```

**Query Plan Output:**
```text
SEARCH timetable_assignments USING INDEX idx_assign_term_day_slot_room (academic_term_id=? AND day=? AND start_slot_index=? AND room_id=?)
```
*Complexity:* $O(\log N)$ logarithmic index lookup instead of an $O(N)$ full table scan.

---

### 4.2 Section Slot Lookup (Optimized with Composite Index)
Execution plan inspection on `idx_assign_term_section_day_slot`:

```sql
EXPLAIN QUERY PLAN
SELECT id, session_id, course_id
FROM timetable_assignments
WHERE academic_term_id = 'term_2026_fall' 
  AND section_id = 'sec_3a'
  AND day = 'Tuesday' 
  AND start_slot_index = 2;
```

**Query Plan Output:**
```text
SEARCH timetable_assignments USING INDEX idx_assign_term_section_day_slot (academic_term_id=? AND section_id=? AND day=? AND start_slot_index=?)
```

---

## 5. ACID Transaction Demonstrations

### 5.1 Atomic Two-Phase Timetable Swap
Ensures that swapping two sessions between rooms or time slots is committed atomically:

```sql
BEGIN TRANSACTION;

-- Relocate Session A
UPDATE timetable_assignments 
SET day = 'Tuesday', start_slot_index = 3, room_id = 'R102'
WHERE academic_term_id = 'term_2026_fall' AND session_id = 'CS301_3A_L0';

-- Relocate Session B
UPDATE timetable_assignments 
SET day = 'Monday', start_slot_index = 0, room_id = 'R101'
WHERE academic_term_id = 'term_2026_fall' AND session_id = 'CS302_3A_L0';

-- Both changes commit together
COMMIT;
```

### 5.2 Rollback Protection on Foreign Key Violation
Demonstrates SQLite's transaction rollback preserving database consistency:

```sql
BEGIN TRANSACTION;

-- Valid insertion
INSERT INTO rooms (id, name, room_type) VALUES ('R999', 'Temporary Annex', 'THEORY_ROOM');

-- Attempted invalid insertion referencing non-existent section
-- Fails due to PRAGMA foreign_keys=ON;
INSERT INTO batches (id, name, section_id) VALUES ('B999', 'Orphan Batch', 'nonexistent_section_id');

-- On failure:
ROLLBACK;

-- Verify that R999 was not persisted
SELECT count(*) FROM rooms WHERE id = 'R999'; -- Returns 0
```

