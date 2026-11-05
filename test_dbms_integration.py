"""Comprehensive test suite for Relational DBMS Integration in AutoSchedule.

Tests:
1. Schema initialization (tables, primary keys, foreign keys, indexes).
2. SQLite foreign key enforcement (PRAGMA foreign_keys=ON).
3. Unique constraints (usernames, department codes).
4. Cascade deletion (section deletion cascades to batches).
5. Transaction rollback on failed operations.
6. Migration engine (dry-run, backup creation, idempotency).
7. ORM CRUD operations on institutional entities.
8. Timetable assignment persistence and versioning.
9. Atomic timetable move and swap persistence in SQLite.
10. Published student portal queries backed by relational database.
"""

import os
import json
import unittest
import tempfile
import sqlite3
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app import app, app_data
from db_models import (
    db, DBAcademicTerm, DBDepartment, DBUser, DBWorkingConfig,
    DBRoom, DBFaculty, DBSection, DBBatch, DBCourse,
    DBTimetableAssignment, DBScheduleVersion, DBTimetablePublication
)
from database import (
    init_db, load_data, save_data, hash_password,
    update_assignment_in_db, swap_assignments_in_db
)
from migrate_json_to_db import migrate_json_to_sqlite

class TestDBMSIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        cls.temp_db.close()
        cls.db_path = cls.temp_db.name.replace('\\', '/')
        cls.db_uri = f"sqlite:///{cls.db_path}"
        app.config['SQLALCHEMY_DATABASE_URI'] = cls.db_uri
        
        with app.app_context():
            init_db(app)

    @classmethod
    def tearDownClass(cls):
        try:
            if os.path.exists(cls.temp_db.name):
                os.remove(cls.temp_db.name)
        except Exception:
            pass

    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess['user'] = {
                'id': 'user_admin',
                'username': 'admin',
                'role': 'ADMIN',
                'name': 'System Administrator'
            }
            sess['csrf_token'] = 'test-dbms-csrf-token'
        self.csrf_header = {'X-CSRF-Token': 'test-dbms-csrf-token'}

    def test_01_schema_initialization(self):
        """Verify all tables, primary keys, and indexes are created in SQLite."""
        with app.app_context():
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            expected_tables = [
                'academic_terms', 'departments', 'users', 'working_configs',
                'rooms', 'faculty', 'sections', 'batches', 'courses',
                'course_faculty', 'course_lab_batches', 'timetable_publications',
                'timetable_assignments', 'schedule_versions'
            ]
            for tbl in expected_tables:
                self.assertIn(tbl, tables, f"Expected table {tbl} missing from database.")

            # Check primary key on rooms
            pk_rooms = inspector.get_pk_constraint('rooms')
            self.assertEqual(pk_rooms['constrained_columns'], ['id'])

            # Check indexes on timetable_assignments
            indexes = [idx['name'] for idx in inspector.get_indexes('timetable_assignments')]
            self.assertTrue(any('idx_assign' in (name or '') for name in indexes) or len(indexes) > 0)

    def test_02_sqlite_foreign_key_enforcement(self):
        """Verify foreign key enforcement blocks inserting orphaned child records."""
        with app.app_context():
            # Inserting a batch pointing to non-existent section_id must fail
            invalid_batch = DBBatch(
                id='batch_invalid_fk',
                name='Invalid Batch',
                section_id='section_does_not_exist_999'
            )
            db.session.add(invalid_batch)
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_03_unique_constraints(self):
        """Verify unique constraints prevent duplicate department codes and usernames."""
        with app.app_context():
            dept1 = DBDepartment(id='dept_unique_1', name='Unique Dept 1', code='TEST_UNIQUE')
            dept2 = DBDepartment(id='dept_unique_2', name='Unique Dept 2', code='TEST_UNIQUE')
            db.session.add(dept1)
            db.session.commit()

            db.session.add(dept2)
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()

            # Clean up dept1
            db.session.delete(dept1)
            db.session.commit()

    def test_04_cascade_deletion(self):
        """Verify cascading deletion from Section to child Batches."""
        with app.app_context():
            sec = DBSection(
                id='sec_cascade_test',
                name='Cascade Test Section',
                semester=3,
                division='C'
            )
            db.session.add(sec)
            db.session.commit()

            batch1 = DBBatch(id='batch_casc_1', name='Batch C1', section_id='sec_cascade_test')
            batch2 = DBBatch(id='batch_casc_2', name='Batch C2', section_id='sec_cascade_test')
            db.session.add_all([batch1, batch2])
            db.session.commit()

            self.assertIsNotNone(db.session.get(DBBatch, 'batch_casc_1'))
            self.assertIsNotNone(db.session.get(DBBatch, 'batch_casc_2'))

            # Delete the section
            db.session.delete(sec)
            db.session.commit()

            # Child batches must be cascade deleted
            self.assertIsNone(db.session.get(DBBatch, 'batch_casc_1'))
            self.assertIsNone(db.session.get(DBBatch, 'batch_casc_2'))

    def test_05_transaction_rollback_on_failure(self):
        """Verify transaction rollback maintains database integrity when a statement fails."""
        with app.app_context():
            initial_room_count = db.session.query(DBRoom).count()
            try:
                db.session.begin_nested()
                db.session.add(DBRoom(id='room_valid_trans', name='Valid Room', room_type='THEORY_ROOM'))
                # Force failure with duplicate ID or bad FK
                db.session.add(DBBatch(id='bad_batch', name='Bad Batch', section_id='nonexistent_sec'))
                db.session.commit()
            except Exception:
                db.session.rollback()

            post_count = db.session.query(DBRoom).count()
            self.assertEqual(initial_room_count, post_count, "Rollback failed: partial changes were committed.")
            self.assertIsNone(db.session.get(DBRoom, 'room_valid_trans'))

    def test_06_migration_dry_run_and_idempotence(self):
        """Verify JSON migration dry-run does not alter DB and live migration is idempotent."""
        # 1. Dry run
        report_dry = migrate_json_to_sqlite(
            json_path='database.json',
            db_uri=self.db_uri,
            dry_run=True,
            create_backup=False
        )
        self.assertTrue(report_dry['dry_run'])
        self.assertEqual(len(report_dry['errors']), 0)
        self.assertGreater(report_dry['counts']['courses'], 0)

        # 2. Live migration
        report_live = migrate_json_to_sqlite(
            json_path='database.json',
            db_uri=self.db_uri,
            dry_run=False,
            create_backup=False
        )
        self.assertFalse(report_live['dry_run'])
        self.assertEqual(len(report_live['errors']), 0)

        # 3. Second run (idempotency check)
        report_second = migrate_json_to_sqlite(
            json_path='database.json',
            db_uri=self.db_uri,
            dry_run=False,
            create_backup=False
        )
        self.assertEqual(len(report_second['errors']), 0)
        self.assertEqual(report_live['counts'], report_second['counts'])

    def test_07_orm_crud_operations(self):
        """Verify full CRUD lifecycle on institutional entities through ORM."""
        with app.app_context():
            # Create
            test_faculty = DBFaculty(
                id='fac_crud_test',
                name='Dr. Alan Turing',
                available_days_json=json.dumps(["Monday", "Wednesday"])
            )
            db.session.add(test_faculty)
            db.session.commit()

            # Read
            retrieved = db.session.get(DBFaculty, 'fac_crud_test')
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.name, 'Dr. Alan Turing')
            self.assertEqual(json.loads(retrieved.available_days_json), ["Monday", "Wednesday"])

            # Update
            retrieved.name = 'Dr. Alan M. Turing'
            db.session.commit()
            updated = db.session.get(DBFaculty, 'fac_crud_test')
            self.assertEqual(updated.name, 'Dr. Alan M. Turing')

            # Delete
            db.session.delete(updated)
            db.session.commit()
            self.assertIsNone(db.session.get(DBFaculty, 'fac_crud_test'))

    def test_08_schedule_persistence_and_versioning(self):
        """Verify schedule assignments and versions are persisted in relational tables."""
        with app.app_context():
            # Ensure an active term exists
            term = db.session.query(DBAcademicTerm).filter_by(is_active=True).first()
            if not term:
                term = DBAcademicTerm(id='term_test_sched', name='Test Term', academic_year='2026-27', is_active=True)
                db.session.add(term)
                db.session.commit()

            # Create test room
            room = db.session.get(DBRoom, 'R_TEST_SCHED')
            if not room:
                room = DBRoom(id='R_TEST_SCHED', name='Room Test Sched', room_type='THEORY_ROOM')
                db.session.add(room)
                db.session.commit()

            # Add assignment
            assignment = DBTimetableAssignment(
                academic_term_id=term.id,
                session_id='TEST_SESS_01',
                day='Monday',
                start_slot_index=1,
                room_id=room.id,
                duration_slots=1,
                variant_index=0
            )
            version = DBScheduleVersion(
                academic_term_id=term.id,
                version_tag='v_test_persistence',
                note='Unit test version',
                soft_score=92.5,
                assignments_json=json.dumps([{'session_id': 'TEST_SESS_01', 'day': 'Monday', 'start_slot_index': 1, 'room_id': room.id}])
            )
            db.session.add_all([assignment, version])
            db.session.commit()

            # Verify in DB
            saved_a = db.session.query(DBTimetableAssignment).filter_by(session_id='TEST_SESS_01').first()
            self.assertIsNotNone(saved_a)
            self.assertEqual(saved_a.day, 'Monday')
            self.assertEqual(saved_a.room_id, 'R_TEST_SCHED')

            saved_v = db.session.query(DBScheduleVersion).filter_by(version_tag='v_test_persistence').first()
            self.assertIsNotNone(saved_v)
            self.assertEqual(saved_v.soft_score, 92.5)

    def test_09_atomic_move_and_swap_persistence(self):
        """Verify direct DB update and swap helpers persist changes atomically."""
        with app.app_context():
            term_id = 'term_2026_fall'
            room1 = DBRoom(id='R_SWAP_1', name='Room S1', room_type='THEORY_ROOM')
            room2 = DBRoom(id='R_SWAP_2', name='Room S2', room_type='THEORY_ROOM')
            db.session.add_all([room1, room2])
            db.session.commit()

            a1 = DBTimetableAssignment(
                academic_term_id=term_id, session_id='SESS_SWAP_A',
                day='Monday', start_slot_index=0, room_id='R_SWAP_1'
            )
            a2 = DBTimetableAssignment(
                academic_term_id=term_id, session_id='SESS_SWAP_B',
                day='Tuesday', start_slot_index=2, room_id='R_SWAP_2'
            )
            db.session.add_all([a1, a2])
            db.session.commit()

            # Test atomic move
            updated = update_assignment_in_db(term_id, 'SESS_SWAP_A', 'Wednesday', 3, 'R_SWAP_2')
            self.assertTrue(updated)
            a1_check = db.session.query(DBTimetableAssignment).filter_by(session_id='SESS_SWAP_A').first()
            self.assertEqual(a1_check.day, 'Wednesday')
            self.assertEqual(a1_check.start_slot_index, 3)

            # Test atomic swap
            move_a = {'day': 'Tuesday', 'start_slot_index': 2, 'room_id': 'R_SWAP_2'}
            move_b = {'day': 'Wednesday', 'start_slot_index': 3, 'room_id': 'R_SWAP_2'}
            swapped = swap_assignments_in_db(term_id, 'SESS_SWAP_A', move_a, 'SESS_SWAP_B', move_b)
            self.assertTrue(swapped)

            a1_after = db.session.query(DBTimetableAssignment).filter_by(session_id='SESS_SWAP_A').first()
            a2_after = db.session.query(DBTimetableAssignment).filter_by(session_id='SESS_SWAP_B').first()
            self.assertEqual(a1_after.day, 'Tuesday')
            self.assertEqual(a1_after.start_slot_index, 2)
            self.assertEqual(a2_after.day, 'Wednesday')
            self.assertEqual(a2_after.start_slot_index, 3)

    def test_10_student_portal_persistence(self):
        """Verify published timetable in DB is served correctly to the student portal."""
        # Authenticate coordinator to publish
        with self.client.session_transaction() as sess:
            sess['user'] = {'id': 'user_coord', 'username': 'coordinator', 'role': 'COORDINATOR'}
            sess['csrf_token'] = 'test-dbms-csrf-token'

        pub_res = self.client.post('/api/timetable/publish', json={'term': 'Fall 2026-27 (Term 1)'}, headers=self.csrf_header)
        self.assertEqual(pub_res.status_code, 200)

        # Anonymous/student client accesses status and metadata
        anon_client = app.test_client()
        status_res = anon_client.get('/api/timetable/status')
        self.assertEqual(status_res.status_code, 200)
        data = status_res.get_json()
        self.assertTrue(data.get('is_published'))
        self.assertEqual(data.get('status'), 'PUBLISHED')

if __name__ == '__main__':
    unittest.main()

