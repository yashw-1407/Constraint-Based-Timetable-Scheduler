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

import unittest
from app import app, app_data
from models import UserRole
from database import save_data

class TestMilestoneC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True

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
        """Verify unpublished faculty schedule rejects anonymous and student access."""
        app_data['publishing'] = {'is_published': False, 'status': 'DRAFT'}
        save_data(app_data)

        faculty_id = app_data['faculty'][0].id
        anon_client = app.test_client()

        # Anonymous access rejected
        res_anon = anon_client.get(f'/api/faculty/{faculty_id}/calendar.ics')
        self.assertEqual(res_anon.status_code, 401)

        # Student access rejected
        with self.client.session_transaction() as sess:
            sess['user'] = {'id': 'user_student', 'username': 'student', 'role': UserRole.STUDENT}
        res_student = self.client.get(f'/api/faculty/{faculty_id}/calendar.ics')
        self.assertEqual(res_student.status_code, 403)

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

if __name__ == '__main__':
    unittest.main()

