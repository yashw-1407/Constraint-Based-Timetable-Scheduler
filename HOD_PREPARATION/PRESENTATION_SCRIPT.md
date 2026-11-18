# Final Project Presentation Script — CampusGrid
## 5-to-10 Minute Spoken Walkthrough for HOD & Faculty Review Committee

---

### Speaker Cue & Timing Guidelines:
- **Total Duration**: 7–8 minutes speaking + 2 minutes live demo.
- **Tone**: Respectful, technically precise, conversational, and confident.
- **Tip**: Do not read slides word-for-word. Speak naturally using the cues below.

---

### [0:00 – 1:00] Part 1: Introduction & The Core Problem

> **"Respected Head of the Department, faculty members, and dear examiners, good morning.**
>
> Today, my teammates and I are proud to present our mini-project: **CampusGrid — A Constraint-Based Academic Timetable Scheduling System**.
>
> Every semester, one of the most tedious and time-consuming administrative tasks in any academic department is **building the timetable**. 
>
> In our department alone, we have over 60 theory lectures and practical labs every week, involving 20 faculty members, 4 sections, and 8 classrooms and specialized computer labs. 
>
> When done manually on paper or in Excel, it takes days of trial and error. And even after days of work, human coordinators inevitably run into clashes:
> - Two classes booked into the same lab at 10 AM,
> - Or a professor scheduled to teach two different sections at the exact same hour,
> - Or students left with awkward 2-hour idle gaps between lectures.
>
> In computer science, this is known as an **NP-Complete combinatorial explosion problem**. Testing all combinations by brute force would require checking more combinations than the number of atoms in the universe.
>
> We wanted to solve this problem mathematically and cleanly."

---

### [1:00 – 2:30] Part 2: Our Proposed Solution & Mathematical Approach

> **"Our solution, CampusGrid, models academic timetabling as a Constraint Satisfaction Problem (CSP) solved using Backtracking with intelligent heuristics.**
>
> Instead of blind guessing, our engine defines:
> 1. **Variables**: Every class session that needs to take place (e.g. 3 lectures of Data Structures, 2 hours of Database Lab).
> 2. **Domains**: All available legal time slots and suitable rooms across the working week.
> 3. **Constraints**, which we have strictly divided into **Hard Constraints** and **Soft Constraints**.
>
> **Hard Constraints** are non-negotiable. They must have zero violations:
> - No teacher clash,
> - No room clash,
> - No student section or lab batch clash,
> - Room type suitability (labs only in computer labs),
> - And consecutive slot integrity (ensuring 2-hour practicals don't get broken across lunch).
>
> **Soft Constraints** measure the comfort and quality of the schedule on a scale of 0 to 100%:
> - Spreading subjects evenly across the week,
> - Preventing students from having the same theory subject twice in one day,
> - Minimizing idle gaps in student schedules,
> - Balancing daily faculty teaching loads,
> - And avoiding giving any professor more than 3 continuous hours of teaching without a break."

---

### [2:30 – 4:00] Part 3: Algorithmic Intelligence (MRV & Backtracking)

> **"To make the solver fast and efficient, we implemented two key Artificial Intelligence techniques:**
>
> First, **Minimum Remaining Values (MRV)**, also known as the **Fail-First Principle**. 
> If a 2-hour practical lab requires a specialized computer lab, it has very few possible slots in the week compared to a normal theory lecture. Our algorithm detects this and schedules the most constrained multi-slot sessions **first**. If an impossible condition exists, it fails and detects it immediately, rather than wasting time down dead ends.
>
> Second, **Intelligent Backtracking with Soft Candidate Scoring**.
> As the algorithm places classes, it scores each candidate slot so that pleasant, high-quality slots are tested first. If a conflict is reached later on, the engine cleanly undoes the last assignment, steps back, and explores the next viable alternative.
>
> Thanks to this combination of MRV and forward domain filtering, our solver schedules **68 sessions across 4 sections in just 34 milliseconds with 0 backtracks**!"

---

### [4:00 – 5:30] Part 4: System Architecture & Implementation

> **"Looking at the technical implementation:**
>
> We engineered CampusGrid as a self-contained, three-tier web application:
> - **Backend**: Built in **Python 3** using the **Flask** framework, exposing 24 clean REST API endpoints for configuration, CRUD operations, Excel parsing, and schedule solving.
> - **Database Layer**: We use **SQLite3** (`autoschedule.db`). Foreign keys are enforced with cascading deletes. Generated timetables are persisted so schedules remain intact across server restarts.
> - **Bulk Excel Import**: Using the `openpyxl` library, coordinators can download a standardized Excel template, edit courses, rooms, and faculty offline, and upload it with one click.
> - **Frontend**: Built with clean semantic HTML5, modern CSS Grid, and vanilla JavaScript. There are zero bulky dependencies, and the entire system runs locally without requiring an internet connection or external cloud services."

---

### [5:30 – 7:30] Part 5: Live Demonstration

> *(Walk over to the laptop screen or projector)*
>
> **"Let me now demonstrate the system live:**
>
> 1. Here is our dashboard on `http://127.0.0.1:5001`. Notice our clean tabs: Configuration, Rooms, Faculty, Sections, Courses, Import Excel, Generate, and Timetable Views.
>
> 2. Under **Configuration**, we can define working days, hours from 9 AM to 5 PM, and lunch from 1 PM to 2 PM.
>
> 3. In the **Courses** tab, you can see how we implement the standard university **L-T-P model**. For example, *Data Structures* has 3 Lecture hours and 2 Practical hours with Dr. Sharma. The system automatically splits this into 3 individual 1-hour theory lectures and a 2-hour practical lab assigned to lab batches.
>
> 4. Now, let's switch to the **Generate** tab. 
> *(Click the blue 'Generate Timetable' button)*
>
> Look at the execution card:
> - Status: **Success**
> - Total Sessions: **68**
> - Solve Time: **34 milliseconds**
> - Backtracks: **0**
> - Overall Quality Score: **75%**, with detailed progress bars showing zero duplicate subjects per day, balanced faculty workload, and minimal student gaps!
>
> 5. Notice the **Audit Verification Card**: It runs an independent mathematical check across all 68 assignments and confirms: **0 Conflicts Detected**.
>
> 6. Finally, let's open **Timetable Views**:
> - In **By Section View**, let's select **Section 3A**. You see a complete weekly grid: Monday through Friday, 9 to 5, with lunch clearly separated, and lab batches A1 and A2 scheduled concurrently in different labs!
> - In **By Faculty View**, let's select **Dr. Sharma**. He gets his personal schedule showing exactly when and where he teaches.
> - And clicking **Print Timetable** produces a clean, printable PDF-ready schedule."

---

### [7:30 – 8:30] Part 6: Conclusion & Future Scope

> **"To conclude:**
>
> CampusGrid successfully solves a real, painful problem that our department faces every semester. 
>
> It replaces days of stressful manual trial-and-error with a scientifically proven, mathematically verified schedule generated in milliseconds.
>
> In the future, we plan to extend this system with:
> 1. Real-time daily faculty substitution management when a teacher is on emergency leave,
> 2. Role-Based Access Control (RBAC) so faculty can view their schedules via mobile login,
> 3. And multi-building campus travel time optimization.
>
> We would like to thank our HOD and project guide for their mentorship throughout this semester.
>
> My teammates and I are now ready to answer any questions you may have. Thank you!"
