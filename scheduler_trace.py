"""
scheduler_trace.py - Observational Trace / Debug System for the Scheduler

This module records the complete decision flow of the scheduling engine
WITHOUT changing any scheduling decisions. It is purely observational.

Usage:
    from scheduler_trace import SchedulerTrace
    trace = SchedulerTrace(level=2)  # 0=off, 1=summary, 2=decisions, 3=full
    # Pass trace object to SchedulingEngine via engine.trace = trace
    # After solve, call trace.write() to save files.

Trace Levels:
    0 - Disabled (no overhead)
    1 - Summary only (sessions created, final result, room util, course summary)
    2 - Decisions (+ domain, MRV, assignments, backtracks, dead ends)
    3 - Full (+ every candidate attempt with per-constraint pass/fail)

Session Filter:
    Pass session_filter={"C3A06_L0", "Algorithms Lab", "S3A"} etc.
    When a filter is set, only matching sessions produce level 2/3 output.
    Level 1 summaries are always complete regardless of filter.
"""

import json
import os
import time
from collections import defaultdict


class SchedulerTrace:
    LEVEL_OFF = 0
    LEVEL_SUMMARY = 1
    LEVEL_DECISIONS = 2
    LEVEL_FULL = 3

    def __init__(self, level=0, session_filter=None, output_dir=None):
        self.level = level
        self.session_filter = set(session_filter) if session_filter else None
        self.output_dir = output_dir or '.'

        self._txt_lines = []
        self._json_data = {
            'run': {},
            'sessions_created': [],
            'domain_generation': [],
            'mrv_order': [],
            'candidate_attempts': [],
            'assignments': [],
            'backtracks': [],
            'dead_ends': [],
            'constraint_failures': {
                'SECTION_CONFLICT': 0,
                'BATCH_CONFLICT': 0,
                'FACULTY_CONFLICT': 0,
                'ROOM_CONFLICT': 0,
                'ROOM_TYPE_MISMATCH': 0,
                'ROOM_CAPACITY': 0,
                'REQUIRED_ROOM': 0,
                'HOME_ROOM_FILTER': 0,
                'DEDICATED_ROOM_EXCLUSION': 0,
                'CONSECUTIVE_SLOTS': 0,
            },
            'session_failure_counts': {},
            'room_utilization': [],
            'course_summary': [],
            'final_result': {}
        }
        self._candidates_tried = 0
        self._max_depth = 0

    @property
    def enabled(self):
        return self.level > 0

    def _should_trace(self, session_id=None, course_name=None,
                      section_id=None, batch_id=None):
        if not self.enabled:
            return False
        if self.session_filter is None:
            return True
        checks = [session_id, course_name, section_id, batch_id]
        return any(c in self.session_filter for c in checks if c is not None)

    def _txt(self, line=''):
        self._txt_lines.append(line)

    # ----------------------------------------------------------------
    # Session Creation (level >= 1)
    # ----------------------------------------------------------------
    def trace_session_created(self, session, course, section, batch=None):
        if self.level < 1:
            return
        home_room = getattr(section, 'home_room_id', None) if section else None
        entry = {
            'session_id': session.id,
            'course_id': session.course_id,
            'course_code': session.course_code,
            'course_name': session.course_name,
            'section_id': session.section_id,
            'batch_id': session.batch_id,
            'faculty_ids': session.faculty_ids,
            'course_type': session.course_type,
            'room_type': session.room_type,
            'duration_slots': session.duration_slots,
            'required_room_id': session.required_room_id or None,
            'home_room_id': home_room,
            'source_L': course.l,
            'source_T': course.t,
            'source_P': course.p,
        }
        self._json_data['sessions_created'].append(entry)

        self._txt('------------------------------------------------------------')
        self._txt('SESSION CREATED')
        self._txt('------------------------------------------------------------')
        self._txt(f"ID:            {session.id}")
        self._txt(f"Course:        {session.course_name} ({session.course_code})")
        self._txt(f"Course ID:     {session.course_id}")
        self._txt(f"Section:       {session.section_id}")
        self._txt(f"Type:          {session.course_type}")
        self._txt(f"Duration:      {session.duration_slots} slot(s)")
        self._txt(f"Room Type:     {session.room_type}")
        self._txt(f"Required Room: {session.required_room_id or 'None'}")
        self._txt(f"Home Room:     {home_room or 'None'}")
        self._txt(f"Batch:         {session.batch_id or 'None'}")
        self._txt(f"Faculty:       {', '.join(session.faculty_ids) if session.faculty_ids else 'None'}")
        self._txt(f"Source L/T/P:  L={course.l}, T={course.t}, P={course.p}")
        self._txt('------------------------------------------------------------')
        self._txt()

    # ----------------------------------------------------------------
    # Room Domain (level >= 2)
    # ----------------------------------------------------------------
    def trace_room_domain(self, session, room_results, strength, home_room_id):
        if self.level < 2:
            return
        if not self._should_trace(session.id, session.course_name,
                                  session.section_id, session.batch_id):
            return

        entry = {
            'session_id': session.id,
            'course_name': session.course_name,
            'batch_id': session.batch_id,
            'strength': strength,
            'home_room_id': home_room_id,
            'rooms': room_results,
        }
        self._json_data['domain_generation'].append(entry)

        self._txt(f"ROOM DOMAIN for {session.id} ({session.course_name}"
                  f"{' batch=' + session.batch_id if session.batch_id else ''}):")
        self._txt(f"  Scheduling strength: {strength}")
        self._txt(f"  Home room: {home_room_id or 'N/A'}")
        self._txt()
        for rr in room_results:
            self._txt(f"  {rr['room_id']} ({rr['room_name']})")
            self._txt(f"    type: {rr['room_type']}")
            self._txt(f"    capacity: {rr['capacity']}")
            self._txt(f"    result: {rr['result']}")
            if rr.get('reason'):
                self._txt(f"    reason: {rr['reason']}")
            self._txt()

    # ----------------------------------------------------------------
    # Domain Size (level >= 2)
    # ----------------------------------------------------------------
    def trace_domain_size(self, session, domain_size, suitable_room_count,
                          days_count):
        if self.level < 2:
            return
        if not self._should_trace(session.id, session.course_name,
                                  session.section_id, session.batch_id):
            return
        self._txt(f"DOMAIN SIZE for {session.id}: {domain_size} candidates "
                  f"({suitable_room_count} rooms x {days_count} days)")
        self._txt()

    # ----------------------------------------------------------------
    # MRV Selection (level >= 2)
    # ----------------------------------------------------------------
    def trace_mrv_selection(self, depth, selected_session, domain_size,
                            remaining_count, other_smallest=None):
        if self.level < 2:
            return
        if depth > self._max_depth:
            self._max_depth = depth

        if not self._should_trace(selected_session.id,
                                  selected_session.course_name,
                                  selected_session.section_id,
                                  selected_session.batch_id):
            return

        entry = {
            'depth': depth,
            'session_id': selected_session.id,
            'course_name': selected_session.course_name,
            'batch_id': selected_session.batch_id,
            'domain_size': domain_size,
            'remaining': remaining_count,
        }
        if other_smallest:
            entry['other_smallest'] = other_smallest
        self._json_data['mrv_order'].append(entry)

        self._txt('============================================================')
        self._txt('MRV SELECTION')
        self._txt('============================================================')
        self._txt(f"Depth: {depth}")
        self._txt(f"Selected: {selected_session.id}")
        self._txt(f"  {selected_session.course_name}"
                  f" ({selected_session.course_code})")
        if selected_session.batch_id:
            self._txt(f"  Batch: {selected_session.batch_id}")
        self._txt(f"Domain size: {domain_size}")
        self._txt(f"Remaining unassigned: {remaining_count}")
        if other_smallest:
            self._txt("Other smallest domains:")
            for sid, ds in other_smallest[:5]:
                self._txt(f"  {sid} -> {ds}")
        self._txt('============================================================')
        self._txt()

    # ----------------------------------------------------------------
    # Candidate Attempt (level >= 3)
    # ----------------------------------------------------------------
    def trace_candidate_attempt(self, depth, session, day, start_slot,
                                end_slot, room_id, score,
                                constraint_results, accepted):
        self._candidates_tried += 1
        if self.level < 3:
            return
        if not self._should_trace(session.id, session.course_name,
                                  session.section_id, session.batch_id):
            return

        entry = {
            'depth': depth,
            'session_id': session.id,
            'day': day,
            'start_slot': start_slot,
            'end_slot': end_slot,
            'room_id': room_id,
            'score': round(score, 4) if score is not None else None,
            'constraints': constraint_results,
            'accepted': accepted,
        }
        self._json_data['candidate_attempts'].append(entry)

        self._txt(f"CANDIDATE for {session.id}:")
        self._txt(f"  Day: {day}  Slots: {start_slot}-{end_slot}  Room: {room_id}")
        if score is not None:
            self._txt(f"  Score: {score:.4f}")
        self._txt("  HARD CONSTRAINTS:")
        for cname, cresult in constraint_results.items():
            self._txt(f"    {cname}: {cresult}")
        self._txt(f"  RESULT: {'ACCEPTED' if accepted else 'REJECTED'}")
        first_fail = next((k for k, v in constraint_results.items()
                           if v == 'FAIL'), None)
        if first_fail:
            self._txt(f"  FIRST FAILURE: {first_fail}")
        self._txt()

    # ----------------------------------------------------------------
    # Candidate Rejected (level >= 2, quick counter)
    # ----------------------------------------------------------------
    def trace_candidate_rejected(self, session, day, start_slot, room_id,
                                 reason):
        if self.level < 2:
            return
        self._candidates_tried += 1
        if reason in self._json_data['constraint_failures']:
            self._json_data['constraint_failures'][reason] += 1
        else:
            self._json_data['constraint_failures'][reason] = \
                self._json_data['constraint_failures'].get(reason, 0) + 1
        sid = session.id
        self._json_data['session_failure_counts'][sid] = \
            self._json_data['session_failure_counts'].get(sid, 0) + 1

    # ----------------------------------------------------------------
    # Assignment (level >= 2)
    # ----------------------------------------------------------------
    def trace_assignment(self, depth, session, day, start_slot, end_slot,
                         room_id, total_assigned, total_sessions):
        if self.level < 2:
            return
        if not self._should_trace(session.id, session.course_name,
                                  session.section_id, session.batch_id):
            return

        entry = {
            'depth': depth,
            'session_id': session.id,
            'course_name': session.course_name,
            'batch_id': session.batch_id,
            'day': day,
            'start_slot': start_slot,
            'end_slot': end_slot,
            'room_id': room_id,
            'progress': f"{total_assigned}/{total_sessions}",
        }
        self._json_data['assignments'].append(entry)

        self._txt('============================================================')
        self._txt('ASSIGNMENT')
        self._txt('============================================================')
        self._txt(f"Depth: {depth}")
        self._txt(f"Session: {session.id}")
        self._txt(f"  {session.course_name} ({session.course_code})")
        if session.batch_id:
            self._txt(f"  Batch: {session.batch_id}")
        self._txt(f"Assigned: Day={day}  Slots={start_slot}-{end_slot}"
                  f"  Room={room_id}")
        self._txt(f"Progress: {total_assigned}/{total_sessions}")
        self._txt('============================================================')
        self._txt()

    # ----------------------------------------------------------------
    # Backtrack (level >= 2)
    # ----------------------------------------------------------------
    def trace_backtrack(self, depth, session, day, start_slot, room_id,
                        backtrack_count):
        if self.level < 2:
            return
        if not self._should_trace(session.id, session.course_name,
                                  session.section_id, session.batch_id):
            return

        entry = {
            'depth': depth,
            'session_id': session.id,
            'day': day,
            'start_slot': start_slot,
            'room_id': room_id,
            'backtrack_count': backtrack_count,
        }
        self._json_data['backtracks'].append(entry)

        self._txt('============================================================')
        self._txt('BACKTRACK')
        self._txt('============================================================')
        self._txt(f"Depth: {depth}")
        self._txt(f"Session: {session.id} ({session.course_name})")
        self._txt(f"Removing: Day={day}  Slot={start_slot}  Room={room_id}")
        self._txt(f"Backtrack count: {backtrack_count}")
        self._txt('============================================================')
        self._txt()

    # ----------------------------------------------------------------
    # Dead End (level >= 1)
    # ----------------------------------------------------------------
    def trace_dead_end(self, depth, session, candidates_considered,
                       failure_breakdown):
        if self.level < 1:
            return

        entry = {
            'depth': depth,
            'session_id': session.id,
            'course_name': session.course_name,
            'batch_id': session.batch_id,
            'candidates_considered': candidates_considered,
            'failure_breakdown': failure_breakdown,
        }
        self._json_data['dead_ends'].append(entry)

        self._txt('============================================================')
        self._txt('DEAD END')
        self._txt('============================================================')
        self._txt(f"Depth: {depth}")
        self._txt(f"Session: {session.id}")
        self._txt(f"  {session.course_name} ({session.course_code})")
        if session.batch_id:
            self._txt(f"  Batch: {session.batch_id}")
        self._txt(f"Candidates considered: {candidates_considered}")
        if failure_breakdown:
            self._txt("Failure breakdown:")
            for reason, count in sorted(failure_breakdown.items(),
                                        key=lambda x: -x[1]):
                if count > 0:
                    self._txt(f"  {reason}: {count}")
        self._txt("ZERO VALID CANDIDATES")
        self._txt('============================================================')
        self._txt()

    # ----------------------------------------------------------------
    # Final Result (level >= 1)
    # ----------------------------------------------------------------
    def trace_final_result(self, status, total_sessions, assigned_count,
                           backtracks, elapsed_seconds, max_depth):
        if self.level < 1:
            return

        result = {
            'status': status,
            'total_sessions': total_sessions,
            'assigned': assigned_count,
            'unassigned': total_sessions - assigned_count,
            'backtracks': backtracks,
            'candidates_tried': self._candidates_tried,
            'elapsed_seconds': round(elapsed_seconds, 3),
            'max_depth': max(max_depth, self._max_depth),
        }
        self._json_data['final_result'] = result

        self._txt()
        self._txt('============================================================')
        self._txt('SCHEDULER FINAL RESULT')
        self._txt('============================================================')
        self._txt(f"Status:             {status}")
        self._txt(f"Total sessions:     {total_sessions}")
        self._txt(f"Assigned:           {assigned_count}")
        self._txt(f"Unassigned:         {total_sessions - assigned_count}")
        self._txt(f"Backtracks:         {backtracks}")
        self._txt(f"Candidates tried:   {self._candidates_tried}")
        self._txt(f"Elapsed time:       {elapsed_seconds:.3f} seconds")
        self._txt(f"Max search depth:   {max(max_depth, self._max_depth)}")
        self._txt('============================================================')
        self._txt()

        # Constraint failure summary
        self._txt('============================================================')
        self._txt('CONSTRAINT FAILURE SUMMARY')
        self._txt('============================================================')
        for cname, count in sorted(
                self._json_data['constraint_failures'].items(),
                key=lambda x: -x[1]):
            if count > 0:
                self._txt(f"  {cname}: {count}")
        total_failures = sum(self._json_data['constraint_failures'].values())
        self._txt(f"  TOTAL: {total_failures}")
        self._txt('============================================================')
        self._txt()

        # Top 10 sessions causing most failures
        top_sessions = sorted(
            self._json_data['session_failure_counts'].items(),
            key=lambda x: -x[1]
        )[:10]
        if top_sessions:
            self._txt('============================================================')
            self._txt('TOP 10 SESSIONS WITH MOST FAILURES')
            self._txt('============================================================')
            for i, (sid, count) in enumerate(top_sessions, 1):
                self._txt(f"  {i}. {sid} -> {count} failures")
            self._txt('============================================================')
            self._txt()

    # ----------------------------------------------------------------
    # Room Utilization (level >= 1)
    # ----------------------------------------------------------------
    def trace_room_utilization(self, rooms, room_schedule, time_slots,
                               working_days, dedicated_room_ids, sections):
        if self.level < 1:
            return

        total_slots = len(time_slots) * len(working_days)
        home_rooms = set()
        for s in sections:
            hr = getattr(s, 'home_room_id', None)
            if hr:
                home_rooms.add(hr)

        self._txt('============================================================')
        self._txt('ROOM UTILIZATION')
        self._txt('============================================================')

        for room in rooms:
            assigned_slots = 0
            sched = room_schedule.get(room.id, {})
            sessions_in_room = set()
            for day_sched in sched.values():
                assigned_slots += len(day_sched)
                sessions_in_room.update(day_sched.values())

            util_pct = (assigned_slots / total_slots * 100) if total_slots > 0 else 0

            if room.id in dedicated_room_ids:
                role = 'DEDICATED (required_room)'
            elif room.id in home_rooms:
                role = 'HOME ROOM'
            else:
                role = 'GENERIC'

            entry = {
                'room_id': room.id,
                'room_name': room.name,
                'room_type': room.room_type,
                'capacity': room.capacity,
                'role': role,
                'assigned_slots': assigned_slots,
                'total_slots': total_slots,
                'utilization_pct': round(util_pct, 1),
                'session_count': len(sessions_in_room),
            }
            self._json_data['room_utilization'].append(entry)

            self._txt(f"  {room.id} ({room.name})")
            self._txt(f"    Type: {room.room_type}  Capacity: {room.capacity}")
            self._txt(f"    Role: {role}")
            self._txt(f"    Assigned: {assigned_slots}/{total_slots} slots"
                      f" ({util_pct:.1f}%)")
            self._txt(f"    Sessions: {len(sessions_in_room)}")
            self._txt()

        self._txt('============================================================')
        self._txt()

    # ----------------------------------------------------------------
    # Course Summary (level >= 1)
    # ----------------------------------------------------------------
    def trace_course_summary(self, courses, sessions, assignments):
        if self.level < 1:
            return

        assigned_ids = set(assignments.keys()) if isinstance(assignments, dict) else set()

        course_map = {c.id: c for c in courses}
        sess_by_course = defaultdict(list)
        for s in sessions:
            sess_by_course[s.course_id].append(s)

        self._txt('============================================================')
        self._txt('COURSE / SESSION SUMMARY')
        self._txt('============================================================')

        for cid in sorted(sess_by_course.keys()):
            course = course_map.get(cid)
            if not course:
                continue
            slist = sess_by_course[cid]
            theory_sessions = [s for s in slist if s.course_type == 'THEORY']
            lab_sessions = [s for s in slist if s.course_type == 'LAB']
            theory_assigned = sum(1 for s in theory_sessions if s.id in assigned_ids)
            lab_assigned = sum(1 for s in lab_sessions if s.id in assigned_ids)

            entry = {
                'course_id': cid,
                'course_name': course.name,
                'course_code': course.code,
                'section_id': course.section_id,
                'L': course.l,
                'T': course.t,
                'P': course.p,
                'theory_sessions_created': len(theory_sessions),
                'lab_sessions_created': len(lab_sessions),
                'theory_assigned': theory_assigned,
                'lab_assigned': lab_assigned,
            }
            self._json_data['course_summary'].append(entry)

            self._txt(f"  {course.name} ({course.code}) [{course.section_id}]")
            self._txt(f"    L={course.l}  T={course.t}  P={course.p}")
            self._txt(f"    THEORY sessions: {len(theory_sessions)} created,"
                      f" {theory_assigned} assigned")
            self._txt(f"    LAB sessions:    {len(lab_sessions)} created,"
                      f" {lab_assigned} assigned")

            # Show room_type for each session
            for s in slist:
                status = 'ASSIGNED' if s.id in assigned_ids else 'UNASSIGNED'
                self._txt(f"      {s.id}: type={s.course_type}"
                          f" room_type={s.room_type}"
                          f" req_room={s.required_room_id or 'None'}"
                          f" batch={s.batch_id or 'None'}"
                          f" [{status}]")
            self._txt()

        self._txt('============================================================')
        self._txt()

    # ----------------------------------------------------------------
    # Write Output
    # ----------------------------------------------------------------
    def write(self):
        if not self.enabled:
            return

        txt_path = os.path.join(self.output_dir, 'scheduler_trace.txt')
        json_path = os.path.join(self.output_dir, 'scheduler_trace.json')

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self._txt_lines))

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self._json_data, f, indent=2, default=str)

        return txt_path, json_path
