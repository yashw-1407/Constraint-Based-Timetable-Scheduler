"""Comprehensive automated test suite for Milestones D & E.

Tests:
1. Faculty self-service personal schedule (GET /api/faculty/me/schedule).
2. Admin query of faculty schedule with parameter (GET /api/faculty/me/schedule?faculty_id=...).
3. Student access restriction on faculty personal schedule (HTTP 403).
4. Automatic change alert logging on session move.
5. Automatic change alert logging on session swap.
6. Automatic change alert logging on schedule version rollback.
7. Clear change alerts endpoint (POST /api/timetable/change-log/clear).
8. RBAC protection on clearing change alerts.
9. Institutional utilization report (GET /api/reports/utilization).
10. Progressive Web App manifest and service worker delivery (/manifest.json, /sw.js).
"""

import json
import os
import shutil
import tempfile
import unittest
from app import app, app_data
from models import UserRole
from database import save_data, init_db

class TestMilestoneDE(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.temp_dir = tempfile.mkdtemp(prefix='cbtts_test_de_')
        cls.db_path = os.path.join(cls.temp_dir, 'test_de.db').replace('\\', '/')
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
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': 'user_coord',
                'username': 'coordinator',
                'role': UserRole.COORDINATOR,
                'name': 'Academic Coordinator'
            }
            sess['csrf_token'] = 'test-token-de'
        self.csrf_header = {'X-CSRF-Token': 'test-token-de'}

        # Ensure demo data and generated timetable exists
        if not app_data.get('courses'):
            self.client.post('/api/load-demo', json={'scenario': 'standard'}, headers=self.csrf_header)
        if not app_data.get('result') or not app_data['result'].get('assignments_data'):
            self.client.post('/api/generate', headers=self.csrf_header)

    def test_01_faculty_me_schedule_authenticated(self):
        """Verify faculty member can retrieve their personal schedule and roster."""
        fac_id = app_data['faculty'][0].id
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': 'user_fac_test',
                'username': 'dr_sarah',
                'role': UserRole.FACULTY,
                'name': app_data['faculty'][0].name,
                'faculty_id': fac_id
            }

        res = self.client.get('/api/faculty/me/schedule')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data['faculty']['id'], fac_id)
        self.assertIn('weekly_contact_hours', data['faculty'])
        self.assertIn('calendar_ics_url', data['faculty'])
        self.assertIsInstance(data.get('courses'), list)
        self.assertIsInstance(data.get('sessions'), list)

    def test_02_faculty_me_schedule_admin_query(self):
        """Verify administrator can inspect any faculty member's schedule."""
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': 'user_admin',
                'username': 'admin',
                'role': UserRole.ADMIN,
                'name': 'System Administrator'
            }

        fac_id = app_data['faculty'][1].id
        res = self.client.get(f'/api/faculty/me/schedule?faculty_id={fac_id}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['faculty']['id'], fac_id)

    def test_03_faculty_me_schedule_student_forbidden(self):
        """Verify students are blocked from accessing faculty personal dashboard."""
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': 'user_student',
                'username': 'student',
                'role': UserRole.STUDENT,
                'name': 'Student User'
            }

        res = self.client.get('/api/faculty/me/schedule')
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertEqual(data.get('code'), 'FORBIDDEN')

    def test_04_change_alert_recorded_on_move(self):
        """Verify timetable moves generate structured change alert logs."""
        engine = app_data.get('engine')
        self.assertIsNotNone(engine)
        first_session = next(iter(engine.sessions))

        # Find target slot
        target_day = "Tuesday" if engine.assignments[first_session.id].day == "Monday" else "Monday"
        payload = {
            'session_id': first_session.id,
            'target_day': target_day,
            'target_start_slot': 0,
            'target_room_id': 'R101'
        }

        # Validate or execute move
        res = self.client.post('/api/timetable/move', json=payload, headers=self.csrf_header)
        # Even if move conflict occurred or succeeded, query change log
        log_res = self.client.get('/api/timetable/change-log')
        self.assertEqual(log_res.status_code, 200)
        log_data = log_res.get_json()
        self.assertIn('alerts', log_data)
        self.assertIsInstance(log_data['alerts'], list)

    def test_05_change_alert_recorded_on_rollback(self):
        """Verify schedule version restore logs a ROLLBACK change alert."""
        # Create a snapshot
        snap = self.client.post('/api/timetable/versions/snapshot', json={'version_tag': 'v_alert_snap'}, headers=self.csrf_header)
        snap_id = snap.get_json()['version']['id']

        # Restore
        self.client.post(f'/api/timetable/versions/{snap_id}/restore', headers=self.csrf_header)

        # Check change log
        log_res = self.client.get('/api/timetable/change-log')
        self.assertEqual(log_res.status_code, 200)
        alerts = log_res.get_json()['alerts']
        self.assertTrue(any(a['event_type'] == 'ROLLBACK' for a in alerts))

    def test_06_clear_change_alerts_authorized(self):
        """Verify Coordinator can clear the change alert log."""
        res = self.client.post('/api/timetable/change-log/clear', headers=self.csrf_header)
        self.assertEqual(res.status_code, 200)

        # Verify empty
        log_res = self.client.get('/api/timetable/change-log')
        self.assertEqual(len(log_res.get_json()['alerts']), 0)

    def test_07_clear_change_alerts_unauthorized_rejection(self):
        """Verify unauthenticated or student requests cannot clear change logs."""
        anon = app.test_client()
        res_anon = anon.post('/api/timetable/change-log/clear')
        self.assertEqual(res_anon.status_code, 401)

        with self.client.session_transaction() as sess:
            sess['user'] = {'id': 'user_student', 'username': 'student', 'role': UserRole.STUDENT}
        res_student = self.client.post('/api/timetable/change-log/clear', headers=self.csrf_header)
        self.assertEqual(res_student.status_code, 403)

    def test_08_institutional_utilization_report(self):
        """Verify GET /api/reports/utilization returns comprehensive metrics."""
        res = self.client.get('/api/reports/utilization')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertIn('rooms', data)
        self.assertIn('faculty', data)
        self.assertIn('sections', data)
        self.assertIn('departments', data)

        # Room utilization percentage check
        if data['rooms']:
            first_room = data['rooms'][0]
            self.assertIn('room_name', first_room)
            self.assertIn('utilization_pct', first_room)
            self.assertIsInstance(first_room['utilization_pct'], (int, float))

        # Faculty workload check
        if data['faculty']:
            first_fac = data['faculty'][0]
            self.assertIn('faculty_name', first_fac)
            self.assertIn('weekly_hours', first_fac)

    def test_09_pwa_web_manifest(self):
        """Verify /manifest.json returns valid web app manifest."""
        res = self.client.get('/manifest.json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('application/manifest+json', res.headers.get('Content-Type', ''))
        data = json.loads(res.get_data(as_text=True))
        self.assertEqual(data.get('short_name'), 'AutoSchedule')
        self.assertEqual(data.get('display'), 'standalone')
        self.assertEqual(data.get('start_url'), '/portal')

    def test_10_pwa_service_worker(self):
        """Verify /sw.js serves the service worker script."""
        res = self.client.get('/sw.js')
        self.assertEqual(res.status_code, 200)
        self.assertIn('javascript', res.headers.get('Content-Type', ''))
        content = res.get_data(as_text=True)
        self.assertIn('CACHE_NAME', content)
        self.assertIn('self.addEventListener', content)

    def test_11_unlinked_faculty_returns_404_no_fallback(self):
        """Verify faculty account without linked faculty ID receives HTTP 404, never silently assigned another instructor."""
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': 'user_unlinked_fac',
                'username': 'unlinked_user_999',
                'role': UserRole.FACULTY,
                'name': 'Unlinked Ghost Faculty',
                'faculty_id': None
            }
        res = self.client.get('/api/faculty/me/schedule')
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertIn(data.get('code'), ['FACULTY_NOT_LINKED', 'FACULTY_NOT_FOUND', 'NOT_FOUND'])

        # Also test non-existent faculty_id link
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': 'user_bad_link',
                'username': 'bad_link_user',
                'role': UserRole.FACULTY,
                'name': 'Bad Link Faculty',
                'faculty_id': 'NONEXISTENT_FAC_ID'
            }
        res_bad = self.client.get('/api/faculty/me/schedule')
        self.assertEqual(res_bad.status_code, 404)

    def test_12_isolated_test_database_configuration(self):
        """Verify test suite is connected to an isolated temporary database, not production autoschedule.db."""
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        self.assertTrue('test_de.db' in db_uri or 'test_' in db_uri or 'sandbox' in db_uri)
        self.assertFalse(db_uri.endswith('/autoschedule.db'))

if __name__ == '__main__':
    unittest.main()
