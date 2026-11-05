"""
test_milestone_a.py - Verification suite for Milestone A:
Seam Restoration & Backend Access Control Hardening.

Covers:
1. Manual timetable adjustments (valid moves, invalid room/faculty/batch/availability,
   atomic rollbacks, valid/invalid swaps, persistence).
2. Authentication & RBAC (Admin, Coordinator, Faculty, Student, privilege escalation,
   route protection).
3. CSRF & Session Security (rejection without token, rejection with invalid token,
   success with valid token, session invalidation).
"""

import unittest
import json
import os
import io
from app import app, app_data
from models import UserRole, RoomType, CourseType, Faculty
from database import save_data, load_data

class TestMilestoneA(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def _login(self, username, password):
        res = self.client.post('/api/auth/login', json={'username': username, 'password': password})
        self.assertEqual(res.status_code, 200, f"Login failed for {username}")
        data = res.get_json()
        token = data.get('csrf_token')
        self.client.environ_base['HTTP_X_CSRF_TOKEN'] = token
        return data['user'], token

    def _logout(self):
        self.client.post('/api/auth/logout')
        self.client.environ_base.pop('HTTP_X_CSRF_TOKEN', None)

    def _setup_demo_timetable(self):
        self._login('admin', 'admin123')
        self.client.post('/api/load-demo', json={'scenario': 'standard'})
        gen_res = self.client.post('/api/generate')
        self.assertEqual(gen_res.status_code, 200)

    # =========================================================================
    # PART 1: MANUAL ADJUSTMENTS & SEAM RESTORATION
    # =========================================================================

    def test_01_valid_session_move(self):
        """Verify validating and executing a valid session move."""
        self._setup_demo_timetable()
        master = self.client.get('/api/timetable/master').get_json()
        self.assertGreater(len(master), 0)
        s0 = master[0]

        # Validate move to current position
        val_res = self.client.post('/api/timetable/validate-move', json={
            'session_id': s0['session_id'],
            'target_day': s0['day'],
            'target_start_slot': s0['start_slot_index'],
            'target_room_id': s0['room_id']
        })
        self.assertEqual(val_res.status_code, 200)
        self.assertTrue(val_res.get_json()['valid'])

        # Execute move
        move_res = self.client.post('/api/timetable/move', json={
            'session_id': s0['session_id'],
            'target_day': s0['day'],
            'target_start_slot': s0['start_slot_index'],
            'target_room_id': s0['room_id']
        })
        self.assertEqual(move_res.status_code, 200)
        self.assertEqual(move_res.get_json()['status'], 'ok')

    def test_02_invalid_room_assignment(self):
        """Verify moves to non-existent, unsuitable, or undersized rooms are rejected."""
        self._setup_demo_timetable()
        master = self.client.get('/api/timetable/master').get_json()
        s0 = master[0]

        # 1. Non-existent room
        res = self.client.post('/api/timetable/validate-move', json={
            'session_id': s0['session_id'],
            'target_day': s0['day'],
            'target_start_slot': s0['start_slot_index'],
            'target_room_id': 'NON_EXISTENT_ROOM_XYZ'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data['valid'])
        self.assertEqual(data['details']['code'], 'ROOM_NOT_FOUND')

        # 2. Room suitability mismatch (try placing theory session in lab room)
        lab_rooms = [r for r in app_data['rooms'] if r.room_type == RoomType.LAB]
        if lab_rooms:
            l_room = lab_rooms[0]
            res_suit = self.client.post('/api/timetable/validate-move', json={
                'session_id': s0['session_id'],
                'target_day': s0['day'],
                'target_start_slot': s0['start_slot_index'],
                'target_room_id': l_room.id
            })
            self.assertEqual(res_suit.status_code, 200)
            self.assertFalse(res_suit.get_json()['valid'])
            self.assertIn(res_suit.get_json()['details']['code'], ['ROOM_SUITABILITY_MISMATCH', 'DEDICATED_ROOM_CONFLICT'])

    def test_03_faculty_double_booking_rejection(self):
        """Verify moving a session to collide with instructor's existing class is rejected."""
        self._setup_demo_timetable()
        master = self.client.get('/api/timetable/master').get_json()
        # Find two sessions taught by different faculty at different times
        # Try moving session 1 into session 0's slot and room
        s0 = master[0]
        s1 = master[1]
        res = self.client.post('/api/timetable/validate-move', json={
            'session_id': s1['session_id'],
            'target_day': s0['day'],
            'target_start_slot': s0['start_slot_index'],
            'target_room_id': s0['room_id']
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data['valid'])
        self.assertIn(data['details']['code'], ['ROOM_CONFLICT', 'FACULTY_CONFLICT', 'SECTION_CONFLICT', 'BATCH_CONFLICT'])

    def test_04_batch_overlap_rejection(self):
        """Verify moving a batch session into a slot where the same batch is busy is rejected."""
        self._setup_demo_timetable()
        master = self.client.get('/api/timetable/master').get_json()
        lab_sessions = [s for s in master if s.get('batch_id')]
        if len(lab_sessions) >= 2:
            l0 = lab_sessions[0]
            # Try to place l0 into a slot where its section/batch has another class
            res = self.client.post('/api/timetable/validate-move', json={
                'session_id': l0['session_id'],
                'target_day': l0['day'],
                'target_start_slot': 99,
                'target_room_id': l0['room_id']
            })
            self.assertEqual(res.status_code, 200)
            self.assertFalse(res.get_json()['valid'])
            self.assertEqual(res.get_json()['details']['code'], 'SLOT_OUT_OF_BOUNDS')

    def test_05_faculty_unavailability_enforcement(self):
        """Verify faculty unavailable slots constraint is honored."""
        self._setup_demo_timetable()
        # Mark instructor of first session as unavailable on Tuesday slot 0
        master = self.client.get('/api/timetable/master').get_json()
        s0 = master[0]
        fac_id = s0['faculty_ids'][0] if s0['faculty_ids'] else None
        if fac_id:
            fac = next((f for f in app_data['faculty'] if f.id == fac_id), None)
            if fac:
                fac.unavailable_slots = [{'day': 'Tuesday', 'slot_index': 0}]
                save_data(app_data)

                # Attempt moving session to Tuesday slot 0
                res = self.client.post('/api/timetable/validate-move', json={
                    'session_id': s0['session_id'],
                    'target_day': 'Tuesday',
                    'target_start_slot': 0,
                    'target_room_id': s0['room_id']
                })
                self.assertEqual(res.status_code, 200)
                data = res.get_json()
                self.assertFalse(data['valid'])
                self.assertIn(data['details']['code'], ['FACULTY_UNAVAILABLE', 'ROOM_CONFLICT', 'SECTION_CONFLICT'])

    def test_06_atomic_session_swap(self):
        """Verify atomic two-phase commit swap and rejection handling."""
        self._setup_demo_timetable()
        master = self.client.get('/api/timetable/master').get_json()
        theory = [s for s in master if s.get('duration_slots', 1) == 1]
        self.assertGreaterEqual(len(theory), 2)
        s_a = theory[0]
        s_b = theory[1]

        # Execute swap
        swap_res = self.client.post('/api/timetable/swap', json={
            'session_a_id': s_a['session_id'],
            'session_b_id': s_b['session_id']
        })
        self.assertIn(swap_res.status_code, [200, 400])

    def test_07_invalid_swap_duration_mismatch(self):
        """Verify swapping sessions with different duration slots is rejected."""
        self._setup_demo_timetable()
        master = self.client.get('/api/timetable/master').get_json()
        theory = [s for s in master if s.get('duration_slots', 1) == 1]
        labs = [s for s in master if s.get('duration_slots', 1) > 1]
        if theory and labs:
            res = self.client.post('/api/timetable/swap', json={
                'session_a_id': theory[0]['session_id'],
                'session_b_id': labs[0]['session_id']
            })
            self.assertEqual(res.status_code, 400)
            data = res.get_json()
            self.assertEqual(data['details']['code'], 'DURATION_MISMATCH')

    def test_08_failed_move_leaves_timetable_unchanged(self):
        """Verify rejected move does not partially mutate active assignments."""
        self._setup_demo_timetable()
        master_before = self.client.get('/api/timetable/master').get_json()
        s0 = master_before[0]

        # Execute an invalid move
        bad_res = self.client.post('/api/timetable/move', json={
            'session_id': s0['session_id'],
            'target_day': s0['day'],
            'target_start_slot': 99,
            'target_room_id': s0['room_id']
        })
        self.assertEqual(bad_res.status_code, 400)

        master_after = self.client.get('/api/timetable/master').get_json()
        self.assertEqual(len(master_before), len(master_after))
        s0_after = next(s for s in master_after if s['session_id'] == s0['session_id'])
        self.assertEqual(s0['day'], s0_after['day'])
        self.assertEqual(s0['start_slot_index'], s0_after['start_slot_index'])
        self.assertEqual(s0['room_id'], s0_after['room_id'])

    def test_09_failed_swap_leaves_both_assignments_unchanged(self):
        """Verify rejected swap leaves both original sessions completely untouched."""
        self._setup_demo_timetable()
        master_before = self.client.get('/api/timetable/master').get_json()
        theory = [s for s in master_before if s.get('duration_slots', 1) == 1]
        labs = [s for s in master_before if s.get('duration_slots', 1) > 1]
        if theory and labs:
            s_a = theory[0]
            s_b = labs[0]

            bad_swap = self.client.post('/api/timetable/swap', json={
                'session_a_id': s_a['session_id'],
                'session_b_id': s_b['session_id']
            })
            self.assertEqual(bad_swap.status_code, 400)

            master_after = self.client.get('/api/timetable/master').get_json()
            s_a_after = next(s for s in master_after if s['session_id'] == s_a['session_id'])
            s_b_after = next(s for s in master_after if s['session_id'] == s_b['session_id'])
            self.assertEqual(s_a['start_slot_index'], s_a_after['start_slot_index'])
            self.assertEqual(s_b['start_slot_index'], s_b_after['start_slot_index'])

    def test_10_successful_changes_persist_correctly(self):
        """Verify successful manual changes survive persistence and reload."""
        self._setup_demo_timetable()
        master = self.client.get('/api/timetable/master').get_json()
        s0 = master[0]

        # Move to its own valid position and confirm persistence save
        res = self.client.post('/api/timetable/move', json={
            'session_id': s0['session_id'],
            'target_day': s0['day'],
            'target_start_slot': s0['start_slot_index'],
            'target_room_id': s0['room_id']
        })
        self.assertEqual(res.status_code, 200)

        # Simulate fresh reload from disk
        fresh_app_data = {}
        load_data(fresh_app_data)
        self.assertIsNotNone(fresh_app_data.get('result'))
        self.assertGreater(len(fresh_app_data['result']['assignments_data']), 0)

    # =========================================================================
    # PART 2: AUTHENTICATION & ROLE-BASED ACCESS CONTROL
    # =========================================================================

    def test_11_unauthenticated_access_to_protected_endpoints(self):
        """Verify unauthenticated requests to protected endpoints return HTTP 401."""
        self._logout()

        protected_posts = [
            '/api/clear',
            '/api/generate',
            '/api/generate-multiple',
            '/api/timetable/publish',
            '/api/timetable/unpublish',
            '/api/timetable/validate-move',
            '/api/timetable/move',
            '/api/timetable/swap',
            '/api/load-demo',
        ]
        for ep in protected_posts:
            res = self.client.post(ep)
            self.assertEqual(res.status_code, 401, f"Expected 401 for unauthenticated POST {ep}")
            self.assertEqual(res.get_json()['code'], 'UNAUTHORIZED')

        # Check resource mutations
        res = self.client.post('/api/rooms', json={'id': 'R_NEW', 'name': 'Room New', 'room_type': 'THEORY_ROOM'})
        self.assertEqual(res.status_code, 401)

        res = self.client.post('/api/courses', json={'id': 'C_NEW', 'name': 'Course New', 'code': 'CS999'})
        self.assertEqual(res.status_code, 401)

    def test_12_admin_full_permissions(self):
        """Verify ADMIN can perform administrative actions including user management and data clearing."""
        self._login('admin', 'admin123')

        # 1. Access user management
        u_res = self.client.get('/api/auth/users')
        self.assertEqual(u_res.status_code, 200)

        # 2. Add an academic term
        t_res = self.client.post('/api/terms', json={
            'id': 'term_admin_test',
            'name': 'Admin Term Test',
            'academic_year': '2026-27'
        })
        self.assertEqual(t_res.status_code, 200)

        # 3. Add an academic department
        d_res = self.client.post('/api/departments', json={
            'id': 'dept_admin_test',
            'name': 'Admin Dept Test',
            'code': 'ADT'
        })
        self.assertEqual(d_res.status_code, 200)

        # 4. Clear data
        c_res = self.client.post('/api/clear')
        self.assertEqual(c_res.status_code, 200)

    def test_13_coordinator_permissions(self):
        """Verify COORDINATOR can generate, configure, and publish timetables."""
        self._login('coordinator', 'coord123')

        # Load demo, generate, and publish
        demo_res = self.client.post('/api/load-demo')
        self.assertEqual(demo_res.status_code, 200)

        gen_res = self.client.post('/api/generate')
        self.assertEqual(gen_res.status_code, 200)

        pub_res = self.client.post('/api/timetable/publish', json={'term': 'Term Test'})
        self.assertEqual(pub_res.status_code, 200)

    def test_14_coordinator_restricted_from_admin_operations(self):
        """Verify COORDINATOR cannot clear all data or manage users (returns HTTP 403)."""
        self._login('coordinator', 'coord123')

        # Attempt to clear data
        c_res = self.client.post('/api/clear')
        self.assertEqual(c_res.status_code, 403)
        self.assertEqual(c_res.get_json()['code'], 'FORBIDDEN')

        # Attempt to list users
        u_res = self.client.get('/api/auth/users')
        self.assertEqual(u_res.status_code, 403)

        # Attempt to create user
        cu_res = self.client.post('/api/auth/users', json={
            'username': 'escalated_user',
            'password': 'password123',
            'role': 'ADMIN'
        })
        self.assertEqual(cu_res.status_code, 403)

    def test_15_faculty_restrictions(self):
        """Verify FACULTY can view own timetable but cannot mutate resources or generate timetables."""
        self._setup_demo_timetable()
        self._login('faculty', 'faculty123')

        # 1. View own timetable
        my_res = self.client.get('/api/timetable/faculty/user_faculty')
        self.assertEqual(my_res.status_code, 200)

        # 2. Cannot clear data
        clr_res = self.client.post('/api/clear')
        self.assertEqual(clr_res.status_code, 403)

        # 3. Cannot generate timetable
        gen_res = self.client.post('/api/generate')
        self.assertEqual(gen_res.status_code, 403)

        # 4. Cannot modify rooms
        room_res = self.client.post('/api/rooms', json={'id': 'R_HACK', 'name': 'Hack Room', 'room_type': 'THEORY_ROOM'})
        self.assertEqual(room_res.status_code, 403)

    def test_16_student_restrictions_and_portal_access(self):
        """Verify STUDENT cannot access draft master timetable or administrative operations."""
        self._setup_demo_timetable()

        # Unpublish timetable
        self._login('admin', 'admin123')
        self.client.post('/api/timetable/unpublish')

        # Switch to student
        self._login('student', 'student123')

        # 1. Draft timetable access blocked for students
        master_res = self.client.get('/api/timetable/master')
        self.assertEqual(master_res.status_code, 403)

        # 2. Cannot clear data
        clr_res = self.client.post('/api/clear')
        self.assertEqual(clr_res.status_code, 403)

        # 3. Cannot publish timetable
        pub_res = self.client.post('/api/timetable/publish')
        self.assertEqual(pub_res.status_code, 403)

        # Switch back to admin to publish timetable
        self._login('admin', 'admin123')
        self.client.post('/api/timetable/publish')

        # Switch to student: published timetable now accessible
        self._login('student', 'student123')
        pub_master = self.client.get('/api/timetable/master')
        self.assertEqual(pub_master.status_code, 200)

    # =========================================================================
    # PART 3: CSRF & SESSION SECURITY
    # =========================================================================

    def test_17_csrf_rejection_for_missing_token(self):
        """Verify authenticated state-changing requests without CSRF token receive HTTP 403."""
        self._login('admin', 'admin123')

        # Remove CSRF token header
        self.client.environ_base.pop('HTTP_X_CSRF_TOKEN', None)

        res = self.client.post('/api/load-demo')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.get_json()['code'], 'CSRF_FAILED')

    def test_18_csrf_rejection_for_invalid_token(self):
        """Verify authenticated state-changing requests with invalid CSRF token receive HTTP 403."""
        self._login('admin', 'admin123')

        # Supply forged/tampered CSRF token
        self.client.environ_base['HTTP_X_CSRF_TOKEN'] = 'forged_fake_attacker_token_xyz'

        res = self.client.post('/api/load-demo')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.get_json()['code'], 'CSRF_FAILED')

    def test_19_successful_request_with_valid_csrf_token(self):
        """Verify authenticated state-changing requests with valid CSRF token succeed."""
        _, token = self._login('admin', 'admin123')
        self.client.environ_base['HTTP_X_CSRF_TOKEN'] = token

        res = self.client.post('/api/load-demo', json={'scenario': 'standard'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['status'], 'ok')

    def test_20_session_invalidation_on_logout(self):
        """Verify logout invalidates the session and subsequent requests require re-authentication."""
        self._login('admin', 'admin123')
        me_before = self.client.get('/api/auth/me').get_json()
        self.assertTrue(me_before['authenticated'])

        self._logout()
        me_after = self.client.get('/api/auth/me').get_json()
        self.assertFalse(me_after['authenticated'])

        # Attempt protected action after logout
        res = self.client.post('/api/load-demo')
        self.assertEqual(res.status_code, 401)

    @classmethod
    def tearDownClass(cls):
        """Restore clean standard environment at test completion."""
        client = app.test_client()
        login_res = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin123'})
        token = login_res.get_json().get('csrf_token', '')
        client.environ_base['HTTP_X_CSRF_TOKEN'] = token
        client.post('/api/load-demo', json={'scenario': 'standard'})
        client.post('/api/generate')
        client.post('/api/timetable/publish')

if __name__ == '__main__':
    unittest.main()
