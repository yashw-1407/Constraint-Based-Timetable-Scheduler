"""
Feasibility analysis of the demo dataset.

This script checks whether a valid timetable is theoretically possible
under the hard constraints, WITHOUT running the backtracking solver.
It performs:
  1. Time-slot generation verification
  2. Room capacity vs section strength analysis
  3. Room suitability analysis (which rooms can serve which sessions)
  4. Per-section load vs available slots
  5. Per-faculty load vs available slots
  6. Lab consecutive-slot availability
  7. Faculty conflict bottleneck analysis
  8. Quick greedy assignment test (non-backtracking)
"""
import sys
from collections import defaultdict, Counter
from demo_data import get_demo_data
from time_slots import generate_time_slots
from constraints import check_consecutive_slots, check_room_suitability, check_room_capacity
from models import CourseType, ScheduleSession

demo = get_demo_data()
config = demo['config']
rooms = demo['rooms']
faculty = demo['faculty']
sections = demo['sections']
courses = demo['courses']

# ==========================================================================
# 1. TIME SLOTS
# ==========================================================================
slots = generate_time_slots(config)
print("=" * 60)
print("1. TIME SLOTS")
print(f"   Days: {config.working_days}")
print(f"   Working hours: {config.start_time} - {config.end_time}")
print(f"   Slot duration: {config.slot_duration_minutes} min")
print(f"   Lunch: {config.lunch_start} - {config.lunch_end}")
print(f"   Extra breaks: {config.breaks}")
print(f"   Generated {len(slots)} slots per day:")
for s in slots:
    print(f"     [{s.index}] {s.start_time} - {s.end_time}")

# Check lab-consecutive availability (2-slot blocks)
consecutive_starts = []
for i in range(len(slots) - 1):
    if slots[i + 1].start_time == slots[i].end_time:
        consecutive_starts.append(i)
print(f"   2-consecutive-slot start indices: {consecutive_starts}")

# ==========================================================================
# 2. SESSION BREAKDOWN
# ==========================================================================
print("\n" + "=" * 60)
print("2. SESSION BREAKDOWN")
total_theory = 0
total_lab_slots = 0
sessions = []
for c in courses:
    if c.course_type == CourseType.THEORY:
        n = c.weekly_hours
        total_theory += n
        for i in range(n):
            sessions.append(ScheduleSession(
                id=f"{c.id}_T{i}", course_id=c.id, course_name=c.name,
                course_code=c.code, course_type=c.course_type,
                section_id=c.section_id, faculty_id=c.faculty_id,
                room_type=c.room_type, required_room_id=c.required_room_id,
                session_index=i, duration_slots=1
            ))
    elif c.course_type == CourseType.LAB:
        dur = c.lab_duration_hours or 2
        total_lab_slots += dur
        sessions.append(ScheduleSession(
            id=f"{c.id}_L0", course_id=c.id, course_name=c.name,
            course_code=c.code, course_type=c.course_type,
            section_id=c.section_id, faculty_id=c.faculty_id,
            room_type=c.room_type, required_room_id=c.required_room_id,
            session_index=0, duration_slots=dur
        ))

print(f"   Total sessions: {len(sessions)}")
print(f"   Theory sessions (1-slot each): {total_theory}")
print(f"   Lab sessions: {len(sessions) - total_theory}  (total lab slots: {total_lab_slots})")
print(f"   Total slot-equivalents: {total_theory + total_lab_slots}")

# ==========================================================================
# 3. ROOM ANALYSIS
# ==========================================================================
print("\n" + "=" * 60)
print("3. ROOM ANALYSIS")
theory_rooms = [r for r in rooms if r.room_type == 'THEORY_ROOM']
lab_rooms = [r for r in rooms if r.room_type == 'LAB']
print(f"   Theory rooms: {len(theory_rooms)}  -> {[r.id + '(cap=' + str(r.capacity) + ')' for r in theory_rooms]}")
print(f"   Lab rooms: {len(lab_rooms)}  -> {[r.id + '(cap=' + str(r.capacity) + ')' for r in lab_rooms]}")

slots_per_day = len(slots)
num_days = len(config.working_days)
total_week_slots = slots_per_day * num_days
theory_room_capacity = len(theory_rooms) * total_week_slots
lab_room_capacity = len(lab_rooms) * total_week_slots
print(f"   Theory room-slot capacity: {len(theory_rooms)} x {total_week_slots} = {theory_room_capacity}")
print(f"   Lab room-slot capacity: {len(lab_rooms)} x {total_week_slots} = {lab_room_capacity}")
print(f"   Theory demand: {total_theory}  {'OK' if total_theory <= theory_room_capacity else 'INSUFFICIENT!'}")
print(f"   Lab demand: {total_lab_slots}  {'OK' if total_lab_slots <= lab_room_capacity else 'INSUFFICIENT!'}")

# ==========================================================================
# 4. ROOM SUITABILITY + CAPACITY FOR EACH SESSION
# ==========================================================================
print("\n" + "=" * 60)
print("4. ROOM SUITABILITY PER SESSION")
sections_by_id = {s.id: s for s in sections}
problem_sessions = []
for sess in sessions:
    suitable = []
    section = sections_by_id.get(sess.section_id)
    for r in rooms:
        if check_room_suitability(sess, r) and check_room_capacity(r, section):
            suitable.append(r.id)
    if not suitable:
        problem_sessions.append(sess)
        print(f"   *** NO SUITABLE ROOM for {sess.id} (section={sess.section_id} strength={section.strength if section else '?'}, room_type={sess.room_type})")
if not problem_sessions:
    print("   All sessions have at least one suitable room.")

# ==========================================================================
# 5. PER-SECTION LOAD
# ==========================================================================
print("\n" + "=" * 60)
print("5. PER-SECTION LOAD")
for sec in sections:
    sec_sessions = [s for s in sessions if s.section_id == sec.id]
    sec_slots = sum(s.duration_slots for s in sec_sessions)
    sec_labs = [s for s in sec_sessions if s.course_type == CourseType.LAB]
    print(f"   {sec.id}: {len(sec_sessions)} sessions, {sec_slots} slot-equivalents / {total_week_slots} available"
          f"  {'OK' if sec_slots <= total_week_slots else 'OVERLOADED!'}"
          f"  (labs: {len(sec_labs)} totalling {sum(s.duration_slots for s in sec_labs)} slots)")

# ==========================================================================
# 6. PER-FACULTY LOAD
# ==========================================================================
print("\n" + "=" * 60)
print("6. PER-FACULTY LOAD")
faculty_by_id = {f.id: f for f in faculty}
fac_loads = defaultdict(list)
for s in sessions:
    fac_loads[s.faculty_id].append(s)

for fid, fsessions in sorted(fac_loads.items()):
    fname = faculty_by_id[fid].name
    total_fslots = sum(s.duration_slots for s in fsessions)
    sections_taught = set(s.section_id for s in fsessions)
    # Per-day max: at most slots_per_day slots per day
    # But ALSO: each section this faculty teaches can block the same slot
    print(f"   {fid} ({fname}): {total_fslots} slots, sections: {sections_taught}")
    # Check if total slots > available
    if total_fslots > total_week_slots:
        print(f"     *** OVERLOADED! {total_fslots} > {total_week_slots}")

# ==========================================================================
# 7. FACULTY CONFLICT BOTTLENECK
# ==========================================================================
print("\n" + "=" * 60)
print("7. FACULTY CONFLICT BOTTLENECK (per-day analysis)")
print("   (Faculty teaching N section-slots on same day requires N distinct timeslots)")
for fid, fsessions in sorted(fac_loads.items()):
    fname = faculty_by_id[fid].name
    total_fslots = sum(s.duration_slots for s in fsessions)
    # Minimum days needed = ceil(total_fslots / slots_per_day)
    import math
    min_days = math.ceil(total_fslots / slots_per_day)
    daily_max = slots_per_day
    print(f"   {fid} ({fname}): {total_fslots} slots, needs min {min_days} days (have {num_days})"
          f"  {'OK' if min_days <= num_days else 'IMPOSSIBLE!'}")

# ==========================================================================
# 8. SECTION+FACULTY JOINT CONSTRAINT
# ==========================================================================
print("\n" + "=" * 60)
print("8. SECTION + FACULTY JOINT CONSTRAINT CHECK")
# The real bottleneck: each section needs its sessions in non-overlapping slots,
# AND each faculty needs their sessions in non-overlapping slots.
# So for a section, on each day, slots are exclusive.
# For a faculty teaching two sections, each slot can serve only one section.
# This is the actual constraint that might cause infeasibility.

# Check: can we find a valid day-assignment (ignoring rooms) for all sessions?
# This is equivalent to graph coloring where days*slots are colors.
print("   Running greedy day-slot assignment (ignoring rooms)...")

# Build assignment: for each session, find a (day, slot_start) that doesn't
# conflict with section or faculty.
section_used = defaultdict(set)  # section_id -> set of (day, slot_idx) used
faculty_used = defaultdict(set)  # faculty_id -> set of (day, slot_idx) used

# Sort: labs first (most constrained), then by faculty load (most loaded first)
sorted_sessions = sorted(sessions,
    key=lambda s: (-s.duration_slots, -sum(x.duration_slots for x in fac_loads[s.faculty_id]))
)

assigned = {}
failed = []

for sess in sorted_sessions:
    placed = False
    for day in config.working_days:
        if sess.duration_slots == 1:
            possible_starts = range(slots_per_day)
        else:
            possible_starts = [i for i in consecutive_starts
                               if i + sess.duration_slots <= slots_per_day]

        for start in possible_starts:
            slot_set = set(range(start, start + sess.duration_slots))

            # Check section conflict
            sec_day_used = {s for (d, s) in section_used[sess.section_id] if d == day}
            if slot_set & sec_day_used:
                continue

            # Check faculty conflict
            fac_day_used = {s for (d, s) in faculty_used[sess.faculty_id] if d == day}
            if slot_set & fac_day_used:
                continue

            # Place it
            for sl in slot_set:
                section_used[sess.section_id].add((day, sl))
                faculty_used[sess.faculty_id].add((day, sl))
            assigned[sess.id] = (day, start)
            placed = True
            break

        if placed:
            break

    if not placed:
        failed.append(sess)

print(f"   Greedy result: {len(assigned)}/{len(sessions)} placed, {len(failed)} failed")
if failed:
    print("   FAILED sessions:")
    for s in failed:
        fname = faculty_by_id[s.faculty_id].name
        print(f"     {s.id} section={s.section_id} faculty={s.faculty_id}({fname}) dur={s.duration_slots}")
    print("\n   NOTE: Greedy failure does NOT prove infeasibility (greedy != optimal).")
    print("   But it suggests the search space is tight.")
else:
    print("   Greedy (ignoring rooms) found a placement for ALL sessions.")
    print("   The problem is FEASIBLE ignoring rooms.")
    print("   Now checking if rooms can also be assigned...")

    # Try assigning rooms
    room_used = defaultdict(set)  # room_id -> set of (day, slot_idx)
    room_assigned = {}
    room_failed = []

    for sess in sorted_sessions:
        day, start = assigned[sess.id]
        slot_set = set(range(start, start + sess.duration_slots))
        section = sections_by_id.get(sess.section_id)

        placed = False
        for r in rooms:
            if not check_room_suitability(sess, r):
                continue
            if not check_room_capacity(r, section):
                continue
            r_day_used = {s for (d, s) in room_used[r.id] if d == day}
            if slot_set & r_day_used:
                continue
            # Assign room
            for sl in slot_set:
                room_used[r.id].add((day, sl))
            room_assigned[sess.id] = r.id
            placed = True
            break

        if not placed:
            room_failed.append(sess)

    print(f"   Room assignment: {len(room_assigned)}/{len(sessions)} placed, {len(room_failed)} failed")
    if room_failed:
        print("   FAILED room assignments:")
        for s in room_failed:
            day, start = assigned[s.id]
            section = sections_by_id.get(s.section_id)
            print(f"     {s.id} day={day} slot={start} room_type={s.room_type} "
                  f"section_strength={section.strength if section else '?'}")
    else:
        print("   *** FULL FEASIBILITY CONFIRMED: All sessions placed with rooms! ***")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
