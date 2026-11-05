# AutoSchedule — Database Setup & Operations Guide

This guide provides exact Windows PowerShell commands for initializing, migrating, backing up, restoring, and inspecting the AutoSchedule relational database.

---

## 1. Environment & Prerequisites

AutoSchedule requires Python 3.10+ (tested on Python 3.14).

### 1.1 Verify Python and Virtual Environment
In Windows PowerShell from the repository root (`d:\KLE\MiniProject\CBTTS_V3`):

```powershell
# Verify Python version
python --version

# Verify required packages are installed
python -c "import flask, flask_sqlalchemy, flask_migrate, sqlalchemy; print('All DBMS packages verified successfully.')"
```

If dependencies need to be installed:
```powershell
pip install flask-sqlalchemy flask-migrate
```

---

## 2. Database Initialization & Schema Migration

AutoSchedule uses SQLite by default, storing its primary database in `autoschedule.db` in the repository root.

### 2.1 Preview Migration (Dry-Run Mode)
The migration utility can validate records and check referential integrity without modifying the database:

```powershell
python migrate_json_to_db.py --dry-run
```

Expected output:
```text
Beginning AutoSchedule database migration (dry_run=True)...

--- MIGRATION SUMMARY REPORT ---
Dry Run: True
Entities Processed:
  - academic_terms: 2
  - departments: 2
  - users: 5
  - working_configs: 1
  - rooms: 6
  - faculty: 8
  - sections: 4
  - batches: 8
  - courses: 16
  - course_faculty_links: 21
  - course_batch_links: 8
  - publications: 1
  - timetable_assignments: 60
  - schedule_versions: 1

Migration completed successfully.
```

### 2.2 Execute Live Migration with Automatic Backup
Run the migration script to populate `autoschedule.db` while creating a timestamped backup of `database.json`:

```powershell
python migrate_json_to_db.py
```

---

## 3. Database Inspection & Verification

You can inspect the SQLite database directly from PowerShell using either Python one-liners or the `sqlite3` CLI.

### 3.1 Table Row Counts (PowerShell)
```powershell
python -c "import sqlite3; con = sqlite3.connect('autoschedule.db'); cur = con.cursor(); print('\n--- TABLE COUNTS ---'); [print(f'{r[0]:<25}: {cur.execute(f\"SELECT count(*) FROM {r[0]}\").fetchone()[0]}') for r in cur.execute(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\").fetchall()]"
```

### 3.2 View Active Users & Roles
```powershell
python -c "import sqlite3; con = sqlite3.connect('autoschedule.db'); cur = con.cursor(); [print(f'{r[0]:<15} | {r[1]:<12} | {r[2]}') for r in cur.execute('SELECT username, role, name FROM users').fetchall()]"
```

### 3.3 Verify Indexes on Timetable Assignments
```powershell
python -c "import sqlite3; con = sqlite3.connect('autoschedule.db'); cur = con.cursor(); [print(r[1]) for r in cur.execute(\"PRAGMA index_list('timetable_assignments')\").fetchall()]"
```

---

## 4. Backup & Disaster Recovery Procedures

### 4.1 Creating a Database Backup
To take a snapshot of both SQLite and JSON fallback:

```powershell
# Create timestamp variable
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# Backup SQLite database
Copy-Item "autoschedule.db" "backup_autoschedule_$timestamp.db"

# Backup JSON fallback
Copy-Item "database.json" "backup_database_$timestamp.json"

Write-Host "Backup created: backup_autoschedule_$timestamp.db and backup_database_$timestamp.json"
```

### 4.2 Restoring from a Backup
If you need to restore the system to a previous snapshot:

```powershell
# Stop any running server process first
# Replace <TIMESTAMP> with your backup timestamp (e.g. 20261105_210340)
Copy-Item "backup_autoschedule_<TIMESTAMP>.db" "autoschedule.db" -Force
Copy-Item "backup_database_<TIMESTAMP>.json" "database.json" -Force

# Verify integrity after restore
python -c "import sqlite3; con = sqlite3.connect('autoschedule.db'); print('Assignments:', con.cursor().execute('SELECT count(*) FROM timetable_assignments').fetchone()[0])"
```

---

## 5. Running the Application with Relational Persistence

Start the Flask server:
```powershell
python app.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser.

All resource CRUD, manual session movements, schedule generations, and publication toggles will be committed directly to `autoschedule.db` with transaction rollback safety.

---

## 6. Enterprise Transition: PostgreSQL Configuration

AutoSchedule uses standard SQLAlchemy ORM abstractions and supports PostgreSQL without modifying any application code.

To point the application to PostgreSQL:
```powershell
# Set the DATABASE_URL environment variable
$env:DATABASE_URL = "postgresql://autoschedule_user:YourSecurePassword@localhost:5432/autoschedule_db"

# Run migrations against PostgreSQL
python migrate_json_to_db.py

# Launch the application
python app.py
```
To revert back to SQLite:
```powershell
Remove-Item Env:\DATABASE_URL
```

