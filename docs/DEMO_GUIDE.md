# Live Demonstration Step-by-Step Guide — CampusGrid
## Flawless Presentation Runbook for College Students

---

### Pre-Demo Checklist (Complete 10 Minutes Before Presentation)

- [ ] Ensure Python is installed (`python --version` $\ge$ 3.10).
- [ ] Double-click `run.bat` or the **Academic Timetable Scheduler** desktop shortcut.
- [ ] Verify the console says:
  ```
  [*] Starting Timetable Scheduler server...
  [*] Opening your browser at http://127.0.0.1:5001 ...
   App is RUNNING!
  ```
- [ ] Confirm your browser opens `http://127.0.0.1:5001`.
- [ ] Keep the terminal window minimized (do NOT close it!).

---

### Step-by-Step Live Demo Runbook

#### Step 1: Open the Application & Show the Header
1. **Action**: Show the browser window at `http://127.0.0.1:5001`.
2. **What to point out**:
   - The clean header: **"CampusGrid — Academic Schedule Management System"**.
   - The green glowing indicator: **"System Active"**.
3. **Key Point to Highlight**:
   > *"Good morning Sir/Madam. Here is CampusGrid running locally on our machine. The system is completely self-contained with zero external dependencies."*

---

#### Step 2: Show Configuration (Institutional Rules)
1. **Action**: Click the **"Configuration"** tab.
2. **What to point out**:
   - Working days: Monday to Friday.
   - Day Start: `09:00`, Day End: `17:00`.
   - Period duration: `60` minutes.
   - Lunch break: `13:00` to `14:00` (1:00 PM to 2:00 PM).
3. **Key Point to Highlight**:
   > *"Under Configuration, we can customize working hours, period lengths, and dedicated lunch windows for our department. Every time slot generated adheres to these college rules."*

---

#### Step 3: Show Academic Resources (Rooms, Faculty, Sections)
1. **Action**: Click through **"Rooms"**, **"Faculty"**, and **"Sections"** tabs.
2. **What to point out**:
   - **Rooms**: Notice the separation between `THEORY_ROOM` (e.g. Room 101, 70 capacity) and `LAB` (e.g. Computer Lab 1, 35 capacity).
   - **Sections & Batches**: Show Section `3A` (60 students) with its sub-batches `A1` (30) and `A2` (30).
3. **Key Point to Highlight**:
   > *"We support both full-class lectures and sub-batches for practicals. Room capacities are tracked so a 60-student class is never assigned to a 35-seat room."*

---

#### Step 4: Show the L-T-P Course Modeling
1. **Action**: Click the **"Courses"** tab.
2. **What to point out**:
   - Look at course `CS301` (*Data Structures*): $L=3, T=0, P=2$.
   - Primary Faculty: `Dr. Sharma`.
   - Lab Batches: `A1` and `A2`.
3. **Key Point to Highlight**:
   > *"Here we implement university-standard L-T-P credit hours. For a course with 3 theory hours and 2 lab hours, the user enters L=3 and P=2 once. Our engine automatically creates 3 separate 1-hour theory lectures and a 2-hour practical lab for each batch."*

---

#### Step 5: (Optional) Show the Excel Bulk Importer
1. **Action**: Click the **"Import Excel"** tab.
2. **What to point out**:
   - The button **"Download Template (.xlsx)"**.
   - Drag & drop Excel upload zone.
3. **Key Point to Highlight**:
   > *"Instead of typing entries by hand, coordinators can download our pre-formatted 5-sheet Excel template, fill it in offline, and import their entire departmental curriculum in one click."*

---

#### Step 6: THE HIGHLIGHT — Generate the Timetable
1. **Action**: Click the **"Generate"** tab.
2. **Action**: Click the big blue button: **"Generate Timetable"**.
3. **What to show on screen**:
   - Status badge: **SUCCESS** (green).
   - Total Sessions: **68**.
   - Execution Time: **~30–50 ms** (less than one-tenth of a second!).
   - Backtracks: **0**.
   - Overall Quality Score: **75.0%**.
4. **What to point out in the Quality Score Breakdown**:
   - Show the 7 progress bars:
     - **Subject Distribution**: 20/20.
     - **No Same Subject Same Day**: 15/15.
     - **Faculty Workload**: 15/15.
     - **Consecutive Faculty Limit**: 15/15.
5. **Key Point to Highlight**:
   > *"With one click, our CSP Backtracking solver placed all 68 sessions in just 34 milliseconds with zero backtracks! And below, our soft scoring engine evaluated the timetable across 7 comfort metrics, achieving a 75% quality rating with zero same-subject duplications per day."*

---

#### Step 7: Show Independent Audit Verification
1. **Action**: Scroll down in the Generate tab to the **Conflict Validation** card.
2. **What to point out**:
   - Green banner: **"Timetable Valid: 0 Conflicts Detected"**.
3. **Key Point to Highlight**:
   > *"To prove mathematical rigor, our system runs an independent audit function. It checks every single assignment from scratch and proves that no two teachers, rooms, or sections are double-booked."*

---

#### Step 8: Show the Interactive Timetable Views
1. **Action**: Click the **"Timetable Views"** tab.
2. **Action A**: Show **By Section View** $\rightarrow$ Select `3A`.
   - Point out the 2D weekly grid. Monday to Friday across the top, time slots down the left.
   - Show how the 1:00 PM to 2:00 PM lunch slot is clean and unoccupied.
   - Show lab batches `A1` and `A2` running concurrently in different computer labs without conflict!
3. **Action B**: Show **By Faculty View** $\rightarrow$ Select `Dr. Sharma`.
   - Point out his personalized schedule.
4. **Action C**: Show **By Room View** $\rightarrow$ Select `Computer Lab 1`.
   - Show the room occupancy schedule.
5. **Action D**: Click **"Print Timetable"**.
   - The browser print preview dialog opens with a crisp, border-aligned paper timetable ready for printing. Cancel print preview to return.

---

### Fallback Plan (What if Something Goes Wrong?)

Every senior engineer prepares for demo contingencies. Here is your bulletproof backup plan:

| Issue | Immediate Fix During Demo |
| :--- | :--- |
| **Browser doesn't open / shows connection refused** | Make sure `run.bat` is running in your taskbar. If you accidentally closed it, double click `run.bat` and refresh `http://127.0.0.1:5001`. |
| **Someone accidentally modified data and generator says "Infeasible"** | Don't panic! Go to the **Configuration** tab $\rightarrow$ select **"Standard"** in the Demo Scenario dropdown $\rightarrow$ click **"Load Demo Data"**. This resets the database to the known-good 68-session working dataset in 1 second! |
| **Port 5001 in use by another app** | In PowerShell, run `$env:PORT=5002; python app.py` and open `http://127.0.0.1:5002`. |
| **Tester asks to evaluate an impossible scenario** | Load the **"Infeasible"** demo scenario and click Generate! It will return `infeasible` and display the **Capacity Shortfall Diagnostic**: *"Lab demand (2 slots) exceeds available (0 slots)"*. Explain: *"Sir, this proves our system detects physical resource impossibilities and warns the coordinator exactly what is missing!"* |
