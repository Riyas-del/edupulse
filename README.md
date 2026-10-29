# EduPulse — Smart Student Study Monitoring & Alarm System

> **Core Product Principle:** *Never let a student unknowingly miss an important academic deadline or attendance warning because they forgot to check the app.*

**EduPulse** is a modern, mobile-first student productivity and academic monitoring application. It functions as a 24/7 personal academic assistant that monitors class schedules, attendance percentages, assignments, project milestones, examinations, and study goals.

---

## Key Features & Capabilities

### 1. Design & Mobile-First User Experience
- **Color Hierarchy:** Dark Navy (`#0B0F19`) & Deep Purple (`#1E1B4B`) theme with Cyan accents (`#38BDF8`). Warning states:
  - 🟢 **Green (`#10B981`):** Safe attendance (>80%), completed assignments.
  - 🟡 **Yellow (`#F59E0B`):** Approaching deadlines (2–3 days), attendance warnings (75%–80%).
  - 🟠 **Orange (`#F97316`):** Urgent warnings (due tomorrow), recovery status.
  - 🔴 **Red (`#EF4444`):** Overdue tasks, critical attendance (<75%), imminent examinations (<24h).
- **Navigation:** Bottom navigation bar on mobile (Home, Timetable, Tasks, Study, Alerts) and a sidebar on desktop.
- **Real-Time Clock & Alarm Status:** Live monitoring radar badge indicates active background rules.

### 2. Action Required Academic Command Center
Prominent urgent banner that surfaces highest-priority academic interventions:
- *“WARNING: Mathematics attendance is 71.4%. Your target is 75.0%.”* (with consecutive classes needed to recover).
- *“URGENT: Database assignment is due tomorrow at 23:59.”*
- *“OVERDUE: Submit your Operating Systems record.”*
- *“PROJECT ALERT: Mini-project milestone submission is in 3 days.”*
- *“STUDY REMINDER: You have not completed today’s study goal.”*

### 3. Intelligent Alarm & Reminder Engine
- **Attendance Formulas & Recovery Math:**
  $$\text{Attendance \%} = \left(\frac{\text{Attended Classes}}{\text{Total Classes}}\right) \times 100$$
  - When below target $T$: Calculates minimum consecutive classes $C$ required:
    $$C = \left\lceil \frac{T \cdot \text{Total} - \text{Attended}}{1 - T} \right\rceil$$
  - When above target $T$: Calculates maximum classes student can safely miss $M$:
    $$M = \left\lfloor \frac{\text{Attended} - T \cdot \text{Total}}{T} \right\rfloor$$
- **Standardized Multi-Stage Deadline Scheduling:**
  - 7 days before deadline
  - 3 days before deadline
  - 1 day before deadline
  - 3 hours before deadline
  - 1 hour before deadline
  - At the exact deadline
  - Repeated overdue reminders every 6 hours until completed or snoozed.
- **Idempotency & Deduplication:** Uses unique hash keys in `reminder_jobs` table to eliminate duplicate notifications.
- **Automatic Cancellation:** Marking an assignment complete or deleting it instantly cancels future scheduled jobs.

### 4. Real Synthesized Audio Alarms (Web Audio API)
- Works natively on mobile and desktop without external audio assets:
  - **Urgent Alarm Siren:** Dual-modulated tone (800Hz–1200Hz) for overdue tasks and critical attendance drops.
  - **Gentle Chime:** Harmonic arpeggio (C5–G5) for upcoming lecture reminders (15 mins prior).
  - **Focus Bell:** Crystal bell chime when Pomodoro sessions complete.
- Integrated with browser **Web Notifications API** and mobile **Vibration API** (`[200, 100, 200]`).

### 5. Study Time Tracker & Pomodoro
- Start, pause, resume, reset focus timer with custom durations (25m Pomodoro, 5m Short Break, 15m Long Break, Stopwatch).
- Session recovery across page refreshes or device restart.
- Manual study session logger.
- Weekly study hours bar chart and subject distribution doughnut chart (powered by Chart.js).

### 6. Digital Academic Library & PYQs
- Unit-wise module organization with syllabus completion percentage tracking.
- Previous-Year Question Papers (PYQ) indexed by subject, semester, examination year, and exam type.

### 7. Certified Academic Reports & PDF Generator
- One-click PDF export using **ReportLab** providing an audit of attendance health, assignment compliance, exam readiness, and actionable recommendations.

### 8. College LMS / Linways Data Importer
- Import weekly timetables or attendance records via CSV formatted exports from Linways or college ERPs.

---

## Database Architecture (20 Relational Tables)

The database schema is fully defined for both **SQLite** (local zero-dependency development) and **Supabase / PostgreSQL** (cloud production with Row Level Security).

| # | Table Name | Purpose |
|---|------------|---------|
| 1 | `profiles` | Student information, daily goals, quiet hours, sound preferences |
| 2 | `semesters` | Academic terms and target attendance percentages |
| 3 | `subjects` | Courses, codes, faculty details, colors, total and attended lectures |
| 4 | `attendance_records` | Timestamped attendance logs (present, absent, cancelled, holiday) |
| 5 | `timetable_entries` | Weekly recurring classes (day 0–6, start/end times, venues) |
| 6 | `assignments` | Academic assignments, due dates, priorities, estimated durations |
| 7 | `tasks` | General tasks, lab records, exam prep, study goals, status |
| 8 | `task_subtasks` | Checklists and subtask completion tracking |
| 9 | `projects` | Capstone/mini-projects, supervisors, teams, completion percentages |
| 10 | `project_milestones` | Milestones and deliverables |
| 11 | `exams` | Internal tests, semester finals, practicals, viva sessions |
| 12 | `study_sessions` | Focus sessions, duration, session types, subject tags |
| 13 | `study_goals` | Daily study targets and progress tracking |
| 14 | `modules` | Syllabus units and completion percentages |
| 15 | `study_materials` | Notes, presentations, syllabus documents, PYQ question papers |
| 16 | `notification_preferences` | Quiet hours, in-app audio, push notifications, intervals |
| 17 | `notifications` | In-app alerts, priorities (1–6), resolution statuses |
| 18 | `reminder_jobs` | Background scheduler jobs with idempotency keys |
| 19 | `holidays` | Academic calendar holidays and off-days |
| 20 | `academic_reports` | Generated weekly performance reports and analytics |

---

## Quick Start & Execution

### 1. Start the Application
Run the launcher script from the project directory:
```powershell
py run.py
```
Or on Windows:
```cmd
run.bat
```

The application starts on `http://127.0.0.1:8000` and automatically opens your browser.

### 2. Pre-Populated Demo Student
The application comes pre-loaded with realistic academic data for **Alex Chen (B.Tech CS Sem 5)**:
- **Critical Attendance:** Mathematics V at 71.4% (< 75.0% threshold).
- **Overdue Task:** Operating Systems Lab Record submission.
- **Urgent Deadline:** Database B+ Tree Indexing assignment due tomorrow.
- **Upcoming Examination:** Computer Networks Midterm in 5 days.
- **Project Milestone:** Autonomous Drone LoRa Mesh test in 3 days.

### 3. Run Acceptance Test Suite
To verify all 14 Acceptance Tests specified in the master prompt:
```powershell
py tests/test_acceptance.py
```
**Result:** 14/14 tests pass with 100% success.

---

## Supabase Deployment Guide

1. Navigate to your [Supabase Dashboard](https://supabase.com).
2. Create a new project or select an existing one.
3. Open the **SQL Editor**.
4. Copy the entire contents of `supabase/schema.sql`.
5. Execute the query. This creates:
   - All 20 tables with primary keys, foreign keys, and cascading deletes.
   - Row Level Security (RLS) policies isolating students by `auth.uid() = user_id`.
   - Performance indexes on frequently queried fields.
