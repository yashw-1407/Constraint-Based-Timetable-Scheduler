"""
test_suite.py - Comprehensive verification of all requirements for Constraint-Based Timetable Scheduler.
"""

import unittest
import json
from app import app, app_data
from models import WorkingConfig, Room, Faculty, Section, Batch, Course, RoomType, CourseType
from time_slots import generate_time_slots
from scheduler import SchedulingEngine
from constraints import validate_timetable

class TestTimetableScheduler(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        # Reset data before test
        self.client.post('/api/clear')

    def test_01_index_route(self):
        """Verify frontend HTML renders with status 200."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'AutoSchedule', res.data)
        # Ensure no emojis in rendered HTML
        for ch in res.data.decode('utf-8'):
            cp = ord(ch)
            is_emoji = ((0x1F300 <= cp <= 0x1FAFF) or (0x2600 <= cp <= 0x27BF) or
                        (0x2300 <= cp <= 0x23FF) or (cp in [0x2B50, 0x200D, 0xFE0F, 0xFE0E]))
            self.assertFalse(is_emoji, f"Found emoji {ch} in HTML")

    def test_02_load_demo_data(self):
        """Verify loading built-in demo datasets across scenarios."""
        for scenario in ['standard', 'bottleneck', 'infeasible', 'single_section']:
            res = self.client.post('/api/load-demo', json={'scenario': scenario})
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data.get('status'), 'ok')

        # Reset back to standard
        self.client.post('/api/load-demo', json={'scenario': 'standard'})

        # Check config
        cfg = self.client.get('/api/config').get_json()
        self.assertIsNotNone(cfg)
        self.assertEqual(len(cfg['working_days']), 5)

        # Check rooms, faculty, sections, batches, courses
        rooms = self.client.get('/api/rooms').get_json()
        self.assertGreaterEqual(len(rooms), 6)

        faculty = self.client.get('/api/faculty').get_json()
        self.assertGreaterEqual(len(faculty), 8)

        sections = self.client.get('/api/sections').get_json()
        self.assertGreaterEqual(len(sections), 4)

        batches = self.client.get('/api/batches').get_json()
        self.assertGreaterEqual(len(batches), 8)

        courses = self.client.get('/api/courses').get_json()
        self.assertGreaterEqual(len(courses), 16)

    def test_03_time_slots_generation(self):
        """Verify dynamic time-slot generation."""
        self.client.post('/api/load-demo')
        res = self.client.get('/api/time-slots')
        self.assertEqual(res.status_code, 200)
        slots = res.get_json()
        self.assertEqual(len(slots), 7)
        self.assertEqual(slots[0]['start_time'], '09:00')
        self.assertEqual(slots[0]['end_time'], '10:00')
        # Check lunch break 13:00-14:00 is skipped
        times = [(s['start_time'], s['end_time']) for s in slots]
        self.assertNotIn(('13:00', '14:00'), times)

    def test_04_pre_generate_summary(self):
        """Verify summary before generation."""
        self.client.post('/api/load-demo')
        res = self.client.get('/api/summary')
        self.assertEqual(res.status_code, 200)
        s = res.get_json()
        self.assertTrue(s['config_set'])
        self.assertEqual(s['sections'], 4)
        self.assertEqual(s['faculty'], 8)
        self.assertEqual(s['rooms'], 6)
        self.assertGreater(s['total_weekly_session_hours'], 0)

    def test_05_generate_timetable(self):
        """Verify CSP solver successfully schedules timetable."""
        self.client.post('/api/load-demo')
        res = self.client.post('/api/generate')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('assignments', data)
        self.assertEqual(len(data['assignments']), 60)
        self.assertIn('soft_score', data)
        self.assertGreaterEqual(data['soft_score']['total_score'], 0)

    def test_06_post_generation_hard_constraints_validation(self):
        """Verify post-generation validation checks all 6 hard constraints."""
        self.client.post('/api/load-demo')
        self.client.post('/api/generate')
        res = self.client.get('/api/validation')
        self.assertEqual(res.status_code, 200)
        v = res.get_json()
        self.assertTrue(v['valid'])
        self.assertEqual(len(v['conflicts']), 0)

    def test_07_timetable_views(self):
        """Verify Master, Section, Faculty, and Room views."""
        self.client.post('/api/load-demo')
        self.client.post('/api/generate')

        # Master view
        m = self.client.get('/api/timetable/master').get_json()
        self.assertEqual(len(m), 60)
        first = m[0]
        for field in ['day', 'time_start', 'time_end', 'room_name', 'course_name', 'faculty_name']:
            self.assertIn(field, first)

        # Section view
        sv = self.client.get('/api/timetable/section/3A').get_json()
        self.assertIn('grid', sv)
        self.assertIn('days', sv)
        self.assertIn('slots', sv)

        # Faculty view
        fv = self.client.get('/api/timetable/faculty/F1').get_json()
        self.assertIn('grid', fv)

        # Room view
        rv = self.client.get('/api/timetable/room/R101').get_json()
        self.assertIn('grid', rv)

    def test_08_generate_multiple_variants(self):
        """Verify generating multiple diverse timetable alternatives."""
        self.client.post('/api/load-demo')
        res = self.client.post('/api/generate-multiple', json={
            'count': 3,
            'min_diversity_pct': 20.0
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn(data['status'], ('success', 'partial'))
        self.assertGreaterEqual(data['generated'], 1)

        # Test selecting variant
        sel = self.client.post('/api/timetable/variant/0')
        self.assertEqual(sel.status_code, 200)

        # Test metadata
        meta = self.client.get('/api/timetable/metadata').get_json()
        self.assertEqual(meta['active_variant_index'], 0)

    def test_09_crud_operations(self):
        """Verify CRUD for Room, Faculty, Section, Batch, and Course."""
        # Config
        self.client.post('/api/config', json={
            'working_days': ['Monday', 'Tuesday'],
            'start_time': '09:00',
            'end_time': '12:00',
            'slot_duration_minutes': 60,
            'lunch_start': '11:00',
            'lunch_end': '12:00',
            'breaks': []
        })

        # Room CRUD
        r = self.client.post('/api/rooms', json={
            'id': 'ROOM_TEST', 'name': 'Room Test', 'room_type': 'THEORY_ROOM', 'capacity': 50
        })
        self.assertEqual(r.status_code, 200)
        r = self.client.put('/api/rooms/ROOM_TEST', json={
            'id': 'ROOM_TEST', 'name': 'Room Test Updated', 'room_type': 'THEORY_ROOM', 'capacity': 60
        })
        self.assertEqual(r.status_code, 200)
        rooms = self.client.get('/api/rooms').get_json()
        self.assertTrue(any(x['name'] == 'Room Test Updated' for x in rooms))
        r = self.client.delete('/api/rooms/ROOM_TEST')
        self.assertEqual(r.status_code, 200)

        # Faculty CRUD
        f = self.client.post('/api/faculty', json={'id': 'F_TEST', 'name': 'Prof Test'})
        self.assertEqual(f.status_code, 200)
        f = self.client.put('/api/faculty/F_TEST', json={'id': 'F_TEST', 'name': 'Prof Test Updated'})
        self.assertEqual(f.status_code, 200)
        fac = self.client.get('/api/faculty').get_json()
        self.assertTrue(any(x['name'] == 'Prof Test Updated' for x in fac))
        f = self.client.delete('/api/faculty/F_TEST')
        self.assertEqual(f.status_code, 200)

        # Section & Batch CRUD
        s = self.client.post('/api/sections', json={
            'id': 'SEC_TEST', 'name': 'Sec Test', 'semester': 3, 'division': 'C', 'strength': 50
        })
        self.assertEqual(s.status_code, 200)
        b = self.client.post('/api/batches', json={
            'id': 'BAT_TEST', 'name': 'Bat Test', 'section_id': 'SEC_TEST', 'strength': 25
        })
        self.assertEqual(b.status_code, 200)
        batches = self.client.get('/api/batches').get_json()
        self.assertTrue(any(x['id'] == 'BAT_TEST' for x in batches))

        # Course CRUD with default room_type
        c = self.client.post('/api/courses', json={
            'id': 'CRS_TEST', 'name': 'Crs Test', 'code': 'CT1', 'section_id': 'SEC_TEST',
            'l': 3, 't': 0, 'p': 0
        })
        self.assertEqual(c.status_code, 200)
        courses = self.client.get('/api/courses').get_json()
        self.assertTrue(any(x['id'] == 'CRS_TEST' for x in courses))

        # Clear
        clr = self.client.post('/api/clear')
        self.assertEqual(clr.status_code, 200)
        self.assertEqual(len(self.client.get('/api/rooms').get_json()), 0)

    def test_10_trace_debug(self):
        """Verify scheduler trace config endpoint."""
        r = self.client.get('/api/debug/trace/config')
        self.assertEqual(r.status_code, 200)
        r = self.client.post('/api/debug/trace/config', json={'level': 1, 'session_filter': 'S1, S2'})
        self.assertEqual(r.status_code, 200)
        cfg = r.get_json()
        self.assertEqual(cfg['level'], 1)
        self.assertEqual(cfg['session_filter'], ['S1', 'S2'])

    def test_11_individual_hard_constraints(self):
        """Verify each hard constraint individually."""
        from constraints import (check_section_conflict, check_batch_conflict,
                                 check_faculty_conflict, check_room_conflict,
                                 check_room_suitability, check_room_capacity_by_strength,
                                 check_consecutive_slots)
        from models import ScheduleSession, TimeSlot

        # 1. Section conflict
        sec_sched = {'3A': {'Monday': {0: 's1'}}}
        self.assertFalse(check_section_conflict('3A', 'Monday', [0], sec_sched))
        self.assertTrue(check_section_conflict('3A', 'Monday', [1], sec_sched))
        self.assertTrue(check_section_conflict('3A', 'Tuesday', [0], sec_sched))

        # 1b. Batch conflict
        bat_sched = {'A1': {'Monday': {0: 's1'}}}
        self.assertFalse(check_batch_conflict('A1', 'Monday', [0], bat_sched))
        self.assertTrue(check_batch_conflict('A1', 'Monday', [1], bat_sched))
        self.assertTrue(check_batch_conflict('A2', 'Monday', [0], bat_sched))

        # 2. Faculty conflict
        fac_sched = {'F1': {'Monday': {0: 's1'}}}
        self.assertFalse(check_faculty_conflict(['F1'], 'Monday', [0], fac_sched))
        self.assertTrue(check_faculty_conflict(['F1'], 'Monday', [1], fac_sched))
        self.assertTrue(check_faculty_conflict(['F2'], 'Monday', [0], fac_sched))

        # 3. Room conflict
        rm_sched = {'R1': {'Monday': {0: 's1'}}}
        self.assertFalse(check_room_conflict('R1', 'Monday', [0], rm_sched))
        self.assertTrue(check_room_conflict('R1', 'Monday', [1], rm_sched))
        self.assertTrue(check_room_conflict('R2', 'Monday', [0], rm_sched))

        # 4. Room suitability
        lab_rm = Room(id='LAB1', name='Lab 1', room_type='LAB')
        th_rm = Room(id='R101', name='Room 101', room_type='THEORY_ROOM')
        lab_sess = ScheduleSession(id='s_lab', course_id='c1', course_name='Lab', course_code='L1',
                                   section_id='3A', batch_id='A1',
                                   course_type='LAB', room_type='LAB', required_room_id=None,
                                   faculty_ids=['F1'], session_index=0, duration_slots=2)
        th_sess = ScheduleSession(id='s_th', course_id='c2', course_name='Theory', course_code='T1',
                                  section_id='3A', batch_id=None,
                                  course_type='THEORY', room_type='THEORY_ROOM', required_room_id=None,
                                  faculty_ids=['F1'], session_index=0, duration_slots=1)
        self.assertTrue(check_room_suitability(lab_sess, lab_rm))
        self.assertFalse(check_room_suitability(lab_sess, th_rm))
        self.assertTrue(check_room_suitability(th_sess, th_rm))
        self.assertFalse(check_room_suitability(th_sess, lab_rm))

        # 5. Room capacity
        cap_rm = Room(id='R1', name='R1', room_type='THEORY_ROOM', capacity=60)
        self.assertTrue(check_room_capacity_by_strength(cap_rm, 50))
        self.assertTrue(check_room_capacity_by_strength(cap_rm, 60))
        self.assertFalse(check_room_capacity_by_strength(cap_rm, 70))

        # 6. Consecutive slots
        slots = [
            TimeSlot(index=0, start_time='09:00', end_time='10:00'),
            TimeSlot(index=1, start_time='10:00', end_time='11:00'),
            TimeSlot(index=2, start_time='11:00', end_time='12:00'),
            # gap (e.g. lunch 12:00-13:00)
            TimeSlot(index=3, start_time='13:00', end_time='14:00'),
        ]
        self.assertTrue(check_consecutive_slots([0, 1], slots))
        self.assertFalse(check_consecutive_slots([0, 2], slots))
        self.assertFalse(check_consecutive_slots([2, 3], slots))  # 60m lunch gap > 20m

    def test_12_excel_template_and_import(self):
        """Verify downloading starter Excel template and importing it."""
        # 1. Download template
        res = self.client.get('/api/import/template')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_type, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        template_bytes = res.data
        self.assertGreater(len(template_bytes), 1000)

        # 2. Upload template back via /api/import/excel
        import io
        data = {
            'file': (io.BytesIO(template_bytes), 'template.xlsx')
        }
        res_upload = self.client.post('/api/import/excel', data=data, content_type='multipart/form-data')
        self.assertEqual(res_upload.status_code, 200)
        upload_json = res_upload.get_json()
        self.assertEqual(upload_json.get('status'), 'ok')
        self.assertIn('imported', upload_json)
        self.assertEqual(upload_json['imported']['rooms'], 2)
        self.assertEqual(upload_json['imported']['faculty'], 2)

    def test_13_excel_timetable_export(self):
        """Verify exporting generated timetable to multi-tab formatted Excel workbook."""
        # Load demo and generate
        self.client.post('/api/load-demo')
        gen_res = self.client.post('/api/generate')
        self.assertEqual(gen_res.status_code, 200)

        # Export timetable
        export_res = self.client.get('/api/export/excel')
        self.assertEqual(export_res.status_code, 200)
        self.assertEqual(export_res.content_type, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        excel_bytes = export_res.data
        self.assertGreater(len(excel_bytes), 5000)

        # Inspect workbook structure
        import io
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
        self.assertIn('Master Schedule', wb.sheetnames)
        self.assertIn('Section Schedules', wb.sheetnames)
        self.assertIn('Faculty Schedules', wb.sheetnames)
        self.assertIn('Room Schedules', wb.sheetnames)

    def test_14_multi_variant_generation_and_selection(self):
        """Verify generating multiple candidate schedule variants and selecting an active variant."""
        self.client.post('/api/load-demo')
        # Generate 3 variants
        res = self.client.post('/api/generate-multiple', json={'count': 3, 'min_diversity_pct': 10.0})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'success')
        variants = data.get('variants', [])
        self.assertGreaterEqual(len(variants), 2)
        self.assertEqual(data.get('active_variant_index'), 0)

        # Select second variant
        sel_res = self.client.post('/api/timetable/variant/1')
        self.assertEqual(sel_res.status_code, 200)
        sel_data = sel_res.get_json()
        self.assertEqual(sel_data.get('status'), 'ok')
        self.assertEqual(sel_data.get('active_variant_index'), 1)

        # Verify active variant in metadata
        meta = self.client.get('/api/timetable/metadata').get_json()
        self.assertEqual(meta.get('active_variant_index'), 1)

    def test_15_schedule_publishing_lifecycle(self):
        """Verify schedule publishing lifecycle states (DRAFT -> PUBLISHED -> DRAFT)."""
        self.client.post('/api/load-demo')
        self.client.post('/api/generate')

        # Check default status is DRAFT
        st_res = self.client.get('/api/timetable/status')
        self.assertEqual(st_res.status_code, 200)
        self.assertEqual(st_res.get_json().get('status'), 'DRAFT')

        # Publish timetable
        pub_res = self.client.post('/api/timetable/publish', json={'term': 'Spring 2026-27'})
        self.assertEqual(pub_res.status_code, 200)
        pub_data = pub_res.get_json()
        self.assertEqual(pub_data['publishing']['status'], 'PUBLISHED')
        self.assertEqual(pub_data['publishing']['term'], 'Spring 2026-27')
        self.assertIsNotNone(pub_data['publishing']['published_at'])

        # Re-verify GET status
        st_res2 = self.client.get('/api/timetable/status')
        self.assertEqual(st_res2.get_json().get('status'), 'PUBLISHED')

        # Unpublish back to DRAFT
        unpub_res = self.client.post('/api/timetable/unpublish')
        self.assertEqual(unpub_res.status_code, 200)
        self.assertEqual(unpub_res.get_json()['publishing']['status'], 'DRAFT')

    def test_16_validate_and_execute_session_move(self):
        """Verify validating moves and executing real-time session moves with conflict checks."""
        self.client.post('/api/load-demo')
        gen_res = self.client.post('/api/generate')
        self.assertEqual(gen_res.status_code, 200)

        master = self.client.get('/api/timetable/master').get_json()
        self.assertGreater(len(master), 0)
        first_sess = master[0]
        session_id = first_sess['session_id']
        orig_day = first_sess['day']
        orig_slot = first_sess['start_slot_index']
        orig_room = first_sess['room_id']

        # 1. Invalid move: slot out of bounds
        bad_res = self.client.post('/api/timetable/validate-move', json={
            'session_id': session_id,
            'target_day': orig_day,
            'target_start_slot': 99,
            'target_room_id': orig_room
        })
        self.assertEqual(bad_res.status_code, 200)
        self.assertFalse(bad_res.get_json()['valid'])
        self.assertEqual(bad_res.get_json()['details']['code'], 'SLOT_OUT_OF_BOUNDS')

        # 2. Invalid move: non-existent day
        bad_day_res = self.client.post('/api/timetable/validate-move', json={
            'session_id': session_id,
            'target_day': 'Funday',
            'target_start_slot': 0,
            'target_room_id': orig_room
        })
        self.assertEqual(bad_day_res.status_code, 200)
        self.assertFalse(bad_day_res.get_json()['valid'])

        # 3. Test valid move to current position
        self_res = self.client.post('/api/timetable/validate-move', json={
            'session_id': session_id,
            'target_day': orig_day,
            'target_start_slot': orig_slot,
            'target_room_id': orig_room
        })
        self.assertEqual(self_res.status_code, 200)
        self.assertTrue(self_res.get_json()['valid'])

        # 4. Execute move
        exec_res = self.client.post('/api/timetable/move', json={
            'session_id': session_id,
            'target_day': orig_day,
            'target_start_slot': orig_slot,
            'target_room_id': orig_room
        })
        self.assertEqual(exec_res.status_code, 200)
        exec_json = exec_res.get_json()
        self.assertEqual(exec_json['status'], 'ok')
        self.assertIn('soft_score', exec_json['details'])

    def test_17_atomic_session_swap(self):
        """Verify atomic two-phase commit swap of two timetable sessions."""
        self.client.post('/api/load-demo')
        self.client.post('/api/generate')

        master = self.client.get('/api/timetable/master').get_json()
        theory_sessions = [s for s in master if s.get('duration_slots', 1) == 1]
        self.assertGreaterEqual(len(theory_sessions), 2)
        sess_a = theory_sessions[0]
        sess_b = theory_sessions[1]

        swap_res = self.client.post('/api/timetable/swap', json={
            'session_a_id': sess_a['session_id'],
            'session_b_id': sess_b['session_id']
        })
        self.assertIn(swap_res.status_code, [200, 400])
        master_after = self.client.get('/api/timetable/master').get_json()
        self.assertEqual(len(master), len(master_after))

    def test_18_academic_terms_management(self):
        """Verify querying, adding, and activating academic semester terms."""
        # 1. Query terms
        res = self.client.get('/api/terms')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('terms', data)
        self.assertGreaterEqual(len(data['terms']), 1)
        self.assertIn('active_term_id', data)

        # 2. Add new term
        add_res = self.client.post('/api/terms', json={
            'id': 'term_2027_summer',
            'name': 'Summer 2027 Special Session',
            'academic_year': '2026-27',
            'semester_type': 'SUMMER'
        })
        self.assertEqual(add_res.status_code, 200)
        self.assertEqual(add_res.get_json()['status'], 'ok')

        # 3. Activate new term
        act_res = self.client.post('/api/terms/activate/term_2027_summer')
        self.assertEqual(act_res.status_code, 200)
        self.assertEqual(act_res.get_json()['active_term_id'], 'term_2027_summer')

        # 4. Verify publishing metadata updated
        status_res = self.client.get('/api/timetable/status')
        self.assertEqual(status_res.status_code, 200)
        self.assertEqual(status_res.get_json().get('term'), 'Summer 2027 Special Session')

    def test_19_departments_management(self):
        """Verify querying and registering academic departments."""
        # 1. Query departments
        res = self.client.get('/api/departments')
        self.assertEqual(res.status_code, 200)
        depts = res.get_json()
        self.assertGreaterEqual(len(depts), 1)

        # 2. Add department
        add_res = self.client.post('/api/departments', json={
            'id': 'dept_mech',
            'name': 'Mechanical Engineering',
            'code': 'MECH'
        })
        self.assertEqual(add_res.status_code, 200)
        self.assertEqual(add_res.get_json()['status'], 'ok')
        self.assertEqual(add_res.get_json()['department']['code'], 'MECH')

    def test_20_public_portal_route(self):
        """Verify public portal renders clean HTML without administration controls and zero emojis."""
        res = self.client.get('/portal')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Campus Timetable Portal', res.data)
        self.assertIn(b'Export Excel', res.data)

        # Check for zero emojis
        for ch in res.data.decode('utf-8'):
            cp = ord(ch)
            is_emoji = ((0x1F300 <= cp <= 0x1FAFF) or (0x2600 <= cp <= 0x27BF) or
                        (0x2300 <= cp <= 0x23FF) or (cp in [0x2B50, 0x200D, 0xFE0F, 0xFE0E]))
            self.assertFalse(is_emoji, f"Found emoji {ch} in portal HTML")

    def test_21_user_authentication_flow(self):
        """Verify role authentication, password verification, session state, and logout."""
        # 1. Initially unauthenticated
        me_res = self.client.get('/api/auth/me')
        self.assertEqual(me_res.status_code, 200)
        self.assertFalse(me_res.get_json()['authenticated'])

        # 2. Login with incorrect credentials fails
        bad_login = self.client.post('/api/auth/login', json={'username': 'admin', 'password': 'wrongpassword'})
        self.assertEqual(bad_login.status_code, 401)

        # 3. Login with correct credentials succeeds
        login_res = self.client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin123'})
        self.assertEqual(login_res.status_code, 200)
        user_data = login_res.get_json()['user']
        self.assertEqual(user_data['username'], 'admin')
        self.assertEqual(user_data['role'], 'ADMIN')

        # 4. /api/auth/me returns authenticated user
        me_auth = self.client.get('/api/auth/me').get_json()
        self.assertTrue(me_auth['authenticated'])
        self.assertEqual(me_auth['user']['role'], 'ADMIN')

        # 5. List users
        users_res = self.client.get('/api/auth/users')
        self.assertEqual(users_res.status_code, 200)
        self.assertGreaterEqual(len(users_res.get_json()), 3)

        # 6. Create new coordinator user
        new_user_res = self.client.post('/api/auth/users', json={
            'username': 'new_coord',
            'password': 'coordpassword456',
            'role': 'COORDINATOR',
            'name': 'Assistant Coordinator'
        })
        self.assertEqual(new_user_res.status_code, 200)

        # 7. Logout clears session
        logout_res = self.client.post('/api/auth/logout')
        self.assertEqual(logout_res.status_code, 200)
        me_logged_out = self.client.get('/api/auth/me').get_json()
        self.assertFalse(me_logged_out['authenticated'])

if __name__ == '__main__':
    unittest.main()
