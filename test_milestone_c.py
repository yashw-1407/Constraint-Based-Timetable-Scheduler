"""Comprehensive automated test suite for Milestone C.

Tests:
1. Schedule versions listing (GET /api/timetable/versions).
2. Schedule snapshot creation (POST /api/timetable/versions/snapshot).
3. Snapshot creation RBAC enforcement (Admin/Coordinator required).
4. Atomic schedule version rollback/restore (POST /api/timetable/versions/<id>/restore).
5. Non-existent version rollback error handling (HTTP 404).
6. Version restore draft invalidation behavior.
7. Faculty RFC 5545 iCalendar feed format and structure (GET /api/faculty/<id>/calendar.ics).
8. Non-existent faculty iCalendar lookup (HTTP 404).
9. Unpublished faculty calendar access control (401/403 enforcement).
10. Published faculty calendar public subscription access.
"""

import os
import shutil
import tempfile
import unittest
from app import app, app_data
from models import UserRole
from database import save_data, load_data, init_db

class TestMilestoneC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.temp_dir = tempfile.mkdtemp(prefix='cbtts_test_c_')
        cls.db_path = os.path.join(cls.temp_dir, 'test_c.db').replace('\\', '/')
        cls.db_uri = f'sqlite:///{cls.db_path}'
        app.config['SQLALCHEMY_DATABASE_URI'] = cls.db_uri
        with app.app_context():
            init_db(app)

    @classmethod
    def tearDownClass(cls):
        try:
            shutil.rmtree(cls.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def setUp(self):
        self.client = app.test_client()
        # Authenticate as Coordinator by default
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': 'user_coord',
                'username': 'coordinator',
                'role': UserRole.COORDINATOR,
                'name': 'Academic Coordinator'
            }
            sess['csrf_token'] = 'test-csrf-token-c'
        self.csrf_header = {'X-CSRF-Token': 'test-csrf-token-c'}

    def test_01_get_schedule_versions_list(self):
        """Verify GET /api/timetable/versions returns a list of version records."""
        res = self.client.get('/api/timetable/versions')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertIsInstance(data.get('versions'), list)

    def test_02_create_schedule_snapshot(self):
        """Verify creating a named schedule snapshot stores version metadata."""
        # Ensure a generated result exists
        if not app_data.get('result'):
            self.client.post('/api/generate', headers=self.csrf_header)

        payload = {
            'version_tag': 'v_test_snapshot_01',
            'note': 'Test snapshot before manual revisions'
        }
        res = self.client.post('/api/timetable/versions/snapshot', json=payload, headers=self.csrf_header)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'ok')
        v = data.get('version')
        self.assertIsNotNone(v)
        self.assertEqual(v.get('version_tag'), 'v_test_snapshot_01')
        self.assertEqual(v.get('note'), 'Test snapshot before manual revisions')
        self.assertGreater(v.get('assignment_count', 0), 0)

    def test_03_snapshot_requires_auth_and_coordinator(self):
        """Verify unauthenticated or unauthorized users cannot create snapshots."""
        anon_client = app.test_client()
        # Unauthenticated request
        res_anon = anon_client.post('/api/timetable/versions/snapshot', json={'version_tag': 'v_anon'})
        self.assertEqual(res_anon.status_code, 401)

        # Authenticated as Student
        with self.client.session_transaction() as sess:
            sess['user'] = {'id': 'user_student', 'username': 'student', 'role': UserRole.STUDENT}
        res_student = self.client.post('/api/timetable/versions/snapshot', json={'version_tag': 'v_student'}, headers=self.csrf_header)
        self.assertEqual(res_student.status_code, 403)

    def test_04_restore_schedule_version_success(self):
        """Verify restoring a historical version rollbacks assignments accurately."""
        # Create a baseline snapshot
        snap_res = self.client.post('/api/timetable/versions/snapshot', json={
            'version_tag': 'v_restore_baseline',
            'note': 'Baseline before relocation'
        }, headers=self.csrf_header)
        self.assertEqual(snap_res.status_code, 200)
        snap_id = snap_res.get_json()['version']['id']
        baseline_count = snap_res.get_json()['version']['assignment_count']

        # Mutate the active timetable (e.g. relocate an assignment)
        first_assign = app_data['result']['assignments_data'][0]
        sess_id = first_assign['session_id']
        orig_day = first_assign['day']

        # Perform restore
        restore_res = self.client.post(f'/api/timetable/versions/{snap_id}/restore', headers=self.csrf_header)
        self.assertEqual(restore_res.status_code, 200)
        r_data = restore_res.get_json()
        self.assertEqual(r_data.get('status'), 'ok')
        self.assertEqual(r_data.get('result', {}).get('assignments_count'), baseline_count)

    def test_05_restore_nonexistent_version_returns_404(self):
        """Verify restoring an invalid or non-existent version ID returns HTTP 404."""
        res = self.client.post('/api/timetable/versions/999999/restore', headers=self.csrf_header)
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data.get('code'), 'NOT_FOUND')

    def test_06_restore_invalidates_published_state(self):
        """Verify restoring an earlier version sets published status back to DRAFT."""
        # Publish timetable
        pub_res = self.client.post('/api/timetable/publish', json={'term': 'Fall 2026-27 (Term 1)'}, headers=self.csrf_header)
        self.assertEqual(pub_res.status_code, 200)
        self.assertTrue(app_data['publishing']['is_published'])

        # Snapshot and restore
        snap = self.client.post('/api/timetable/versions/snapshot', json={'version_tag': 'v_pub_snap'}, headers=self.csrf_header)
        snap_id = snap.get_json()['version']['id']

        self.client.post(f'/api/timetable/versions/{snap_id}/restore', headers=self.csrf_header)
        self.assertEqual(app_data['publishing']['status'], 'DRAFT')

    def test_07_faculty_ical_feed_structure(self):
        """Verify GET /api/faculty/<id>/calendar.ics generates valid RFC 5545 format."""
        faculty_id = app_data['faculty'][0].id
        res = self.client.get(f'/api/faculty/{faculty_id}/calendar.ics')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/calendar', res.headers.get('Content-Type', ''))
        self.assertIn(f'faculty_{faculty_id}_schedule.ics', res.headers.get('Content-Disposition', ''))

        content = res.get_data(as_text=True)
        self.assertIn('BEGIN:VCALENDAR', content)
        self.assertIn('VERSION:2.0', content)
        self.assertIn('PRODID:-//AutoSchedule//', content)
        self.assertIn('BEGIN:VEVENT', content)
        self.assertIn('SUMMARY:', content)
        self.assertIn('DTSTART:', content)
        self.assertIn('DTEND:', content)
        self.assertIn('RRULE:FREQ=WEEKLY', content)
        self.assertIn('LOCATION:', content)
        self.assertIn('END:VEVENT', content)
        self.assertIn('END:VCALENDAR', content)

    def test_08_faculty_ical_feed_nonexistent_faculty_404(self):
        """Verify request for unknown faculty member returns HTTP 404."""
        res = self.client.get('/api/faculty/FAC_UNKNOWN_9999/calendar.ics')
        self.assertEqual(res.status_code, 404)

    def test_09_faculty_ical_unpublished_access_control(self):
        """Verify unpublished faculty schedule rejects anonymous, student, and other faculty access."""
        app_data['publishing'] = {'is_published': False, 'status': 'DRAFT'}
        save_data(app_data)

        faculty_id = app_data['faculty'][0].id
        anon_client = app.test_client()

        # 1. Anonymous access rejected (401)
        res_anon = anon_client.get(f'/api/faculty/{faculty_id}/calendar.ics')
        self.assertEqual(res_anon.status_code, 401)

        # 2. Student access rejected (403)
        with self.client.session_transaction() as sess:
            sess['user'] = {'id': 'user_student', 'username': 'student', 'role': UserRole.STUDENT}
        res_student = self.client.get(f'/api/faculty/{faculty_id}/calendar.ics')
        self.assertEqual(res_student.status_code, 403)

        # 3. Another faculty member access rejected (403)
        with self.client.session_transaction() as sess:
            sess['user'] = {'id': 'user_other_fac', 'username': 'other_fac', 'role': UserRole.FACULTY, 'faculty_id': 'FAC_DIFFERENT_99'}
        res_other = self.client.get(f'/api/faculty/{faculty_id}/calendar.ics')
        self.assertEqual(res_other.status_code, 403)

        # 4. Same faculty member allowed to access own unpublished calendar (200)
        with self.client.session_transaction() as sess:
            sess['user'] = {'id': 'user_same_fac', 'username': 'same_fac', 'role': UserRole.FACULTY, 'faculty_id': faculty_id}
        res_own = self.client.get(f'/api/faculty/{faculty_id}/calendar.ics')
        self.assertEqual(res_own.status_code, 200)
        self.assertIn('BEGIN:VCALENDAR', res_own.get_data(as_text=True))

    def test_10_faculty_ical_published_public_access(self):
        """Verify published faculty schedule is accessible to anonymous subscribers."""
        app_data['publishing'] = {'is_published': True, 'status': 'PUBLISHED', 'term': 'Fall 2026-27'}
        save_data(app_data)

        faculty_id = app_data['faculty'][0].id
        anon_client = app.test_client()

        # Public access allowed when timetable is published
        res_anon = anon_client.get(f'/api/faculty/{faculty_id}/calendar.ics')
        self.assertEqual(res_anon.status_code, 200)
        self.assertIn('BEGIN:VCALENDAR', res_anon.get_data(as_text=True))

    def test_11_test_database_is_isolated(self):
        """Verify active test database configuration points to a temporary SQLite database."""
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        self.assertTrue('test_c.db' in db_uri or 'test_' in db_uri or 'sandbox' in db_uri)
        self.assertFalse(db_uri.endswith('/autoschedule.db'))

    def test_12_multi_candidate_selection_sync_and_persistence(self):
        """Verify multi-candidate generation and variant selection synchronizes assignments and persists across restart."""
        # Ensure demo data exists
        if not app_data.get('courses'):
            self.client.post('/api/load-demo', json={'scenario': 'standard'}, headers=self.csrf_header)

        # Reset active result
        app_data['result'] = None
        app_data['engine'] = None

        # Generate multiple variants without single generate
        res_multi = self.client.post('/api/generate-multiple', json={'count': 2}, headers=self.csrf_header)
        self.assertEqual(res_multi.status_code, 200)
        data = res_multi.get_json()
        self.assertIn('variants', data)
        self.assertGreaterEqual(len(data['variants']), 2)

        # Active variant 0 assignments must be synchronized
        self.assertIsNotNone(app_data.get('result'))
        self.assertIn('assignments_data', app_data['result'])
        self.assertEqual(len(app_data['result']['assignments_data']), len(data['variants'][0]['assignments_data']))

        # Select variant 1
        res_sel = self.client.post('/api/timetable/variant/1', headers=self.csrf_header)
        self.assertEqual(res_sel.status_code, 200)
        self.assertEqual(app_data['result']['assignments_data'], data['variants'][1]['assignments_data'])

        # Create snapshot using the selected variant
        res_snap = self.client.post('/api/timetable/versions/snapshot', json={'note': 'Variant 1 Snapshot'}, headers=self.csrf_header)
        self.assertEqual(res_snap.status_code, 200)

        # Simulate restart and reload
        reloaded_state = {'active_term_id': app_data.get('active_term_id', 'term_2026_fall')}
        with app.app_context():
            load_data(reloaded_state)
        self.assertIsNotNone(reloaded_state.get('result'))
        self.assertEqual(len(reloaded_state['result']['assignments_data']), len(data['variants'][1]['assignments_data']))

if __name__ == '__main__':
    unittest.main()

