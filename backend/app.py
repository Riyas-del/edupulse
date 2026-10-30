import os
import sys
import json
import asyncio
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

# Ensure backend directory is in sys.path when imported from root
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from database import init_db, seed_demo_data, get_connection
from reminder_engine import (
    calculate_attendance_metrics,
    schedule_assignment_reminders,
    cancel_pending_reminders,
    run_reminder_check
)
from pdf_report import generate_student_pdf_report

# Background scheduler task that ticks the reminder engine
async def background_reminder_worker():
    while True:
        try:
            run_reminder_check("demo-student")
        except Exception as e:
            print(f"[Reminder Worker Error] {e}")
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_demo_data(reset=False)
    # Start reminder worker
    worker_task = asyncio.create_task(background_reminder_worker())
    yield
    worker_task.cancel()

app = FastAPI(title="EduPulse Backend API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Pydantic Request Models
class SubjectCreate(BaseModel):
    name: str
    code: str
    faculty_name: Optional[str] = None
    faculty_email: Optional[str] = None
    classroom: Optional[str] = None
    target_attendance: float = 75.0
    total_classes: int = 0
    attended_classes: int = 0
    credits: int = 3
    color: Optional[str] = "#38BDF8"

class AttendanceLog(BaseModel):
    subject_id: str
    status: str # present, absent, cancelled
    date: Optional[str] = None
    notes: Optional[str] = None

class TaskCreate(BaseModel):
    title: str
    subject_id: Optional[str] = None
    description: Optional[str] = None
    task_type: str = "daily"
    due_date: str
    due_time: Optional[str] = "23:59"
    priority: str = "medium"
    estimated_duration_minutes: int = 60

class AssignmentCreate(BaseModel):
    title: str
    subject_id: str
    description: Optional[str] = None
    assigned_date: Optional[str] = None
    due_date: str
    due_time: str = "23:59"
    priority: str = "medium"
    estimated_duration_minutes: int = 120

class StudySessionCreate(BaseModel):
    subject_id: Optional[str] = None
    task_id: Optional[str] = None
    start_time: str
    end_time: str
    duration_minutes: int
    session_type: str = "focus"
    notes: Optional[str] = None

class SettingsUpdate(BaseModel):
    full_name: Optional[str] = None
    college_name: Optional[str] = None
    default_attendance_threshold: Optional[float] = 75.0
    daily_study_goal_minutes: Optional[int] = 180
    quiet_hours_start: Optional[str] = "22:00"
    quiet_hours_end: Optional[str] = "07:00"
    in_app_sound: Optional[bool] = True
    browser_push: Optional[bool] = True

# ============================================================================
# 1. DASHBOARD & ACTION REQUIRED
# ============================================================================
@app.get("/api/dashboard")
def get_dashboard(user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_dow = now.weekday()

    # User profile
    cursor.execute("SELECT * FROM profiles WHERE id = ?", (user_id,))
    profile = cursor.fetchone()
    daily_goal = profile["daily_study_goal_minutes"] if profile else 180

    # Subjects & Attendance
    cursor.execute("SELECT * FROM subjects WHERE user_id = ?", (user_id,))
    subjects = cursor.fetchall()
    subjects_list = []
    total_attended = 0
    total_conducted = 0
    critical_attendance_count = 0

    for s in subjects:
        total_attended += s["attended_classes"]
        total_conducted += s["total_classes"]
        m = calculate_attendance_metrics(s["attended_classes"], s["total_classes"], s["target_attendance"])
        if m["percentage"] < s["target_attendance"]:
            critical_attendance_count += 1
        subjects_list.append({
            "id": s["id"],
            "name": s["name"],
            "code": s["code"],
            "color": s["color"],
            "total_classes": s["total_classes"],
            "attended_classes": s["attended_classes"],
            "target_attendance": s["target_attendance"],
            "metrics": m
        })

    overall_attendance = round((total_attended / max(1, total_conducted)) * 100, 1) if total_conducted > 0 else 100.0

    # Today's Study Time
    cursor.execute("""
    SELECT SUM(duration_minutes) as mins FROM study_sessions
    WHERE user_id = ? AND date(start_time) = ?
    """, (user_id, today_str))
    today_study = cursor.fetchone()["mins"] or 0

    # Weekly Study Time
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    cursor.execute("""
    SELECT SUM(duration_minutes) as mins FROM study_sessions
    WHERE user_id = ? AND date(start_time) >= ?
    """, (user_id, week_start))
    week_study = cursor.fetchone()["mins"] or 0

    # Tasks stats
    cursor.execute("SELECT * FROM tasks WHERE user_id = ?", (user_id,))
    tasks = cursor.fetchall()
    completed_tasks_count = sum(1 for t in tasks if t["status"] == "completed")
    pending_tasks_count = sum(1 for t in tasks if t["status"] != "completed")
    overdue_tasks_count = sum(1 for t in tasks if t["status"] == "overdue")

    # Assignments due soon & overdue
    cursor.execute("""
    SELECT a.*, s.name as subject_name, s.code as subject_code
    FROM assignments a
    JOIN subjects s ON a.subject_id = s.id
    WHERE a.user_id = ?
    ORDER BY a.due_date ASC, a.due_time ASC
    """, (user_id,))
    all_asg = cursor.fetchall()
    asg_due_soon = []
    asg_overdue = []
    for a in all_asg:
        a_dict = dict(a)
        if a["status"] == "overdue":
            asg_overdue.append(a_dict)
        elif a["status"] != "completed":
            asg_due_soon.append(a_dict)

    # Next upcoming deadline
    next_deadline = asg_due_soon[0] if asg_due_soon else None

    # Today's Timetable
    cursor.execute("""
    SELECT t.*, s.name as subject_name, s.code as subject_code, s.color as subject_color
    FROM timetable_entries t
    JOIN subjects s ON t.subject_id = s.id
    WHERE t.user_id = ? AND t.day_of_week = ?
    ORDER BY t.start_time ASC
    """, (user_id, current_dow))
    today_timetable = [dict(r) for r in cursor.fetchall()]

    # Upcoming Exams
    cursor.execute("""
    SELECT e.*, s.name as subject_name, s.code as subject_code
    FROM exams e
    JOIN subjects s ON e.subject_id = s.id
    WHERE e.user_id = ? AND e.exam_date >= ?
    ORDER BY e.exam_date ASC
    LIMIT 3
    """, (user_id, today_str))
    upcoming_exams = [dict(r) for r in cursor.fetchall()]

    # Project progress
    cursor.execute("SELECT * FROM projects WHERE user_id = ? ORDER BY deadline ASC LIMIT 2", (user_id,))
    projects = [dict(r) for r in cursor.fetchall()]

    # ACTION REQUIRED: The highest priority issues
    action_required = []
    # 1. Overdue assignments/tasks (Priority 1)
    for a in asg_overdue:
        action_required.append({
            "type": "overdue",
            "priority": 1,
            "badge": "OVERDUE",
            "color": "red",
            "title": f"OVERDUE: Submit {a['title']}",
            "description": f"Assignment for {a['subject_code']} is overdue (Due was {a['due_date']} {a['due_time']}).",
            "action_text": "Submit Now",
            "link_type": "assignment",
            "link_id": a["id"]
        })
    for t in tasks:
        if t["status"] == "overdue":
            action_required.append({
                "type": "overdue_task",
                "priority": 1,
                "badge": "OVERDUE",
                "color": "red",
                "title": f"OVERDUE: {t['title']}",
                "description": f"Task was due {t['due_date']}. Finish immediately.",
                "action_text": "Mark Done",
                "link_type": "task",
                "link_id": t["id"]
            })

    # 2. Critical Low Attendance (Priority 2)
    for s in subjects_list:
        if s["metrics"]["status"] in ["Critical", "Recovery"]:
            action_required.append({
                "type": "attendance",
                "priority": 2,
                "badge": "CRITICAL ATTENDANCE",
                "color": "red" if s["metrics"]["status"] == "Critical" else "orange",
                "title": f"WARNING: {s['code']} attendance is {s['metrics']['percentage']}%. Target is {s['target_attendance']}%.",
                "description": s["metrics"]["message"],
                "action_text": "Log Attendance",
                "link_type": "subject",
                "link_id": s["id"]
            })

    # 3. Urgent assignments due tomorrow / within 24h
    for a in asg_due_soon:
        try:
            due_dt = datetime.strptime(f"{a['due_date']} {a['due_time']}", "%Y-%m-%d %H:%M")
            hours = (due_dt - now).total_seconds() / 3600.0
            if 0 <= hours <= 36:
                action_required.append({
                    "type": "urgent_deadline",
                    "priority": 3,
                    "badge": "URGENT",
                    "color": "orange",
                    "title": f"URGENT: {a['title']} is due {'tomorrow' if hours > 12 else 'today'}.",
                    "description": f"{a['subject_code']} • Due at {a['due_time']}. Estimated duration: {a['estimated_duration_minutes']} mins.",
                    "action_text": "Work On It",
                    "link_type": "assignment",
                    "link_id": a["id"]
                })
        except Exception:
            pass

    # 4. Project Alerts
    for p in projects:
        try:
            p_deadline = datetime.strptime(p['deadline'], "%Y-%m-%d")
            days_left = (p_deadline - now).days
            if 0 <= days_left <= 5 and p['progress_percentage'] < 60:
                action_required.append({
                    "type": "project_alert",
                    "priority": 3,
                    "badge": "PROJECT ALERT",
                    "color": "yellow",
                    "title": f"PROJECT ALERT: {p['title']} submission is in {days_left} days.",
                    "description": f"Current progress is only {p['progress_percentage']}%. Accelerated effort required.",
                    "action_text": "View Milestones",
                    "link_type": "project",
                    "link_id": p["id"]
                })
        except Exception:
            pass

    # 5. Study Goal Reminder
    if today_study < daily_goal:
        action_required.append({
            "type": "study_reminder",
            "priority": 4,
            "badge": "STUDY REMINDER",
            "color": "blue",
            "title": f"STUDY REMINDER: You have not completed today's study goal.",
            "description": f"{today_study} / {daily_goal} mins completed ({round((today_study/max(1, daily_goal))*100)}%).",
            "action_text": "Start Timer",
            "link_type": "study",
            "link_id": None
        })

    # Sort action items by priority
    action_required.sort(key=lambda x: x["priority"])

    # Unread notifications count
    cursor.execute("SELECT COUNT(*) as unread FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,))
    unread_notifs = cursor.fetchone()["unread"]

    conn.close()

    return {
        "student": dict(profile) if profile else {},
        "overall_attendance": overall_attendance,
        "critical_issues_count": len(action_required),
        "action_required": action_required,
        "today_study_mins": today_study,
        "weekly_study_mins": week_study,
        "daily_study_goal": daily_goal,
        "tasks_completed_today": completed_tasks_count,
        "tasks_pending": pending_tasks_count,
        "tasks_overdue": overdue_tasks_count,
        "subjects": subjects_list,
        "today_timetable": today_timetable,
        "assignments_due_soon": asg_due_soon[:5],
        "assignments_overdue": asg_overdue,
        "next_deadline": next_deadline,
        "upcoming_exams": upcoming_exams,
        "projects": projects,
        "unread_notifications": unread_notifs
    }

# ============================================================================
# 2. SUBJECTS & ATTENDANCE API
# ============================================================================
@app.get("/api/subjects")
def get_subjects(user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subjects WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["metrics"] = calculate_attendance_metrics(r["attended_classes"], r["total_classes"], r["target_attendance"])
        result.append(d)
    conn.close()
    return result

@app.post("/api/subjects")
def create_subject(sub: SubjectCreate, user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    sub_id = f"sub-{int(datetime.now().timestamp()*1000)}"
    now_iso = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO subjects (id, user_id, name, code, faculty_name, faculty_email, classroom, target_attendance, total_classes, attended_classes, credits, color, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (sub_id, user_id, sub.name, sub.code, sub.faculty_name, sub.faculty_email, sub.classroom, sub.target_attendance, sub.total_classes, sub.attended_classes, sub.credits, sub.color, now_iso, now_iso))
    conn.commit()
    conn.close()
    return {"id": sub_id, "message": "Subject created successfully."}

@app.get("/api/subjects/{subject_id}")
def get_subject_detail(subject_id: str, user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subjects WHERE id = ? AND user_id = ?", (subject_id, user_id))
    s = cursor.fetchone()
    if not s:
        conn.close()
        raise HTTPException(status_code=404, detail="Subject not found")

    sub_dict = dict(s)
    sub_dict["metrics"] = calculate_attendance_metrics(s["attended_classes"], s["total_classes"], s["target_attendance"])

    # Attendance logs
    cursor.execute("SELECT * FROM attendance_records WHERE subject_id = ? ORDER BY date DESC LIMIT 20", (subject_id,))
    sub_dict["attendance_history"] = [dict(r) for r in cursor.fetchall()]

    # Modules
    cursor.execute("SELECT * FROM modules WHERE subject_id = ? ORDER BY unit_number ASC", (subject_id,))
    sub_dict["modules"] = [dict(r) for r in cursor.fetchall()]

    # Assignments
    cursor.execute("SELECT * FROM assignments WHERE subject_id = ? ORDER BY due_date ASC", (subject_id,))
    sub_dict["assignments"] = [dict(r) for r in cursor.fetchall()]

    # Exams
    cursor.execute("SELECT * FROM exams WHERE subject_id = ? ORDER BY exam_date ASC", (subject_id,))
    sub_dict["exams"] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return sub_dict

@app.post("/api/subjects/{subject_id}/attendance")
def log_attendance(subject_id: str, log: AttendanceLog, user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subjects WHERE id = ? AND user_id = ?", (subject_id, user_id))
    sub = cursor.fetchone()
    if not sub:
        conn.close()
        raise HTTPException(status_code=404, detail="Subject not found")

    log_date = log.date or datetime.now().strftime("%Y-%m-%d")
    rec_id = f"att-{int(datetime.now().timestamp()*1000)}"
    now_iso = datetime.now().isoformat()

    # Record log
    cursor.execute("""
    INSERT INTO attendance_records (id, user_id, subject_id, date, status, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (rec_id, user_id, subject_id, log_date, log.status, log.notes, now_iso))

    # Update subject counters
    new_total = sub["total_classes"]
    new_attended = sub["attended_classes"]
    if log.status == "present":
        new_total += 1
        new_attended += 1
    elif log.status == "absent":
        new_total += 1
    # 'cancelled' does not increment total classes

    cursor.execute("""
    UPDATE subjects
    SET total_classes = ?, attended_classes = ?, updated_at = ?
    WHERE id = ?
    """, (new_total, new_attended, now_iso, subject_id))
    conn.commit()

    # Re-calculate metrics
    metrics = calculate_attendance_metrics(new_attended, new_total, sub["target_attendance"])

    # If critical, trigger alert immediately
    if metrics["percentage"] < sub["target_attendance"]:
        cursor.execute("""
        INSERT INTO notifications (id, user_id, title, message, category, priority, related_type, related_id, is_read, is_resolved, trigger_time, created_at)
        VALUES (?, ?, ?, ?, 'critical', 2, 'subject', ?, 0, 0, ?, ?)
        """, (
            f"notif-att-{rec_id}",
            user_id, f"ATTENDANCE ALERT: {sub['code']} at {metrics['percentage']}%",
            f"Attendance dropped below target ({sub['target_attendance']}%). Need {metrics['classes_needed']} consecutive classes to restore safe status.",
            subject_id, now_iso, now_iso
        ))
        conn.commit()

    conn.close()
    return {"message": "Attendance recorded", "metrics": metrics}

# ============================================================================
# 3. TIMETABLE API
# ============================================================================
@app.get("/api/timetable")
def get_timetable(user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT t.*, s.name as subject_name, s.code as subject_code, s.color as subject_color
    FROM timetable_entries t
    JOIN subjects s ON t.subject_id = s.id
    WHERE t.user_id = ?
    ORDER BY t.day_of_week ASC, t.start_time ASC
    """, (user_id,))
    rows = cursor.fetchall()
    by_day = {i: [] for i in range(7)}
    for r in rows:
        by_day[r["day_of_week"]].append(dict(r))
    conn.close()
    return by_day

@app.post("/api/timetable")
def add_timetable_entry(entry: Dict[str, Any], user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    entry_id = f"tt-{int(datetime.now().timestamp()*1000)}"
    now_iso = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO timetable_entries (id, user_id, subject_id, day_of_week, start_time, end_time, classroom, faculty_name, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (entry_id, user_id, entry["subject_id"], entry["day_of_week"], entry["start_time"], entry["end_time"], entry.get("classroom"), entry.get("faculty_name"), entry.get("notes"), now_iso))
    conn.commit()
    conn.close()
    return {"id": entry_id, "message": "Timetable entry created."}

# ============================================================================
# 4. TASKS & ASSIGNMENTS API
# ============================================================================
@app.get("/api/tasks")
def get_tasks(user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT t.*, s.name as subject_name, s.code as subject_code, s.color as subject_color
    FROM tasks t
    LEFT JOIN subjects s ON t.subject_id = s.id
    WHERE t.user_id = ?
    ORDER BY t.due_date ASC, t.due_time ASC
    """, (user_id,))
    tasks = [dict(r) for r in cursor.fetchall()]

    # Fetch subtasks
    for t in tasks:
        cursor.execute("SELECT * FROM task_subtasks WHERE task_id = ? ORDER BY sort_order ASC", (t["id"],))
        t["subtasks"] = [dict(st) for st in cursor.fetchall()]

    conn.close()
    return tasks

@app.post("/api/tasks")
def create_task(t: TaskCreate, user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    task_id = f"task-{int(datetime.now().timestamp()*1000)}"
    now_iso = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO tasks (id, user_id, subject_id, title, description, task_type, due_date, due_time, priority, estimated_duration_minutes, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'not_started', ?, ?)
    """, (task_id, user_id, t.subject_id, t.title, t.description, t.task_type, t.due_date, t.due_time, t.priority, t.estimated_duration_minutes, now_iso, now_iso))
    conn.commit()
    conn.close()
    return {"id": task_id, "message": "Task created."}

@app.post("/api/assignments")
def create_assignment(a: AssignmentCreate, user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    asg_id = f"asg-{int(datetime.now().timestamp()*1000)}"
    now_iso = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO assignments (id, user_id, subject_id, title, description, assigned_date, due_date, due_time, priority, estimated_duration_minutes, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'not_started', ?, ?)
    """, (asg_id, user_id, a.subject_id, a.title, a.description, a.assigned_date or date.today().isoformat(), a.due_date, a.due_time, a.priority, a.estimated_duration_minutes, now_iso, now_iso))
    conn.commit()
    conn.close()

    # Automatically schedule reminder jobs
    schedule_assignment_reminders(user_id, asg_id, a.due_date, a.due_time)
    return {"id": asg_id, "message": "Assignment created and reminders scheduled."}

@app.patch("/api/tasks/{task_id}/complete")
def complete_task(task_id: str, user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()

    # Check tasks table
    cursor.execute("UPDATE tasks SET status = 'completed', completion_percentage = 100, completed_at = ?, updated_at = ? WHERE id = ? AND user_id = ?", (now_iso, now_iso, task_id, user_id))
    # Also check assignments table if id matches
    cursor.execute("UPDATE assignments SET status = 'completed', updated_at = ? WHERE id = ? AND user_id = ?", (now_iso, task_id, user_id))

    # Mark corresponding notifications resolved
    cursor.execute("UPDATE notifications SET is_resolved = 1, is_read = 1 WHERE related_id = ?", (task_id,))
    conn.commit()
    conn.close()

    # Cancel pending reminders
    cancel_pending_reminders("task", task_id)
    cancel_pending_reminders("assignment", task_id)

    return {"message": "Task marked complete and pending reminders cancelled."}

# ============================================================================
# 5. PROJECTS & MILESTONES API
# ============================================================================
@app.get("/api/projects")
def get_projects(user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.*, s.name as subject_name, s.code as subject_code
    FROM projects p
    LEFT JOIN subjects s ON p.subject_id = s.id
    WHERE p.user_id = ?
    ORDER BY p.deadline ASC
    """, (user_id,))
    projects = [dict(r) for r in cursor.fetchall()]
    for p in projects:
        cursor.execute("SELECT * FROM project_milestones WHERE project_id = ? ORDER BY due_date ASC", (p["id"],))
        p["milestones"] = [dict(m) for m in cursor.fetchall()]
    conn.close()
    return projects

@app.post("/api/projects")
def create_project(data: Dict[str, Any], user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    proj_id = f"proj-{int(datetime.now().timestamp()*1000)}"
    now_iso = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO projects (id, user_id, subject_id, title, description, start_date, deadline, progress_percentage, supervisor_name, supervisor_contact, team_members, submission_status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, 'in_progress', ?, ?)
    """, (proj_id, user_id, data.get("subject_id"), data["title"], data.get("description"), data.get("start_date", date.today().isoformat()), data["deadline"], data.get("supervisor_name"), data.get("supervisor_contact"), data.get("team_members"), now_iso, now_iso))
    conn.commit()
    conn.close()
    return {"id": proj_id, "message": "Project created."}

@app.patch("/api/projects/milestones/{milestone_id}/toggle")
def toggle_milestone(milestone_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM project_milestones WHERE id = ?", (milestone_id,))
    m = cursor.fetchone()
    if not m:
        conn.close()
        raise HTTPException(status_code=404, detail="Milestone not found")
    new_status = 0 if m["is_completed"] else 1
    cursor.execute("UPDATE project_milestones SET is_completed = ? WHERE id = ?", (new_status, milestone_id))

    # Recalculate project progress
    proj_id = m["project_id"]
    cursor.execute("SELECT COUNT(*) as total, SUM(is_completed) as completed FROM project_milestones WHERE project_id = ?", (proj_id,))
    res = cursor.fetchone()
    if res["total"] > 0:
        progress = int((res["completed"] / res["total"]) * 100)
        cursor.execute("UPDATE projects SET progress_percentage = ? WHERE id = ?", (progress, proj_id))

    conn.commit()
    conn.close()
    return {"message": "Milestone updated"}

# ============================================================================
# 6. EXAMS API
# ============================================================================
@app.get("/api/exams")
def get_exams(user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT e.*, s.name as subject_name, s.code as subject_code, s.color as subject_color
    FROM exams e
    JOIN subjects s ON e.subject_id = s.id
    WHERE e.user_id = ?
    ORDER BY e.exam_date ASC
    """, (user_id,))
    exams = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return exams

@app.post("/api/exams")
def create_exam(data: Dict[str, Any], user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    exam_id = f"exam-{int(datetime.now().timestamp()*1000)}"
    now_iso = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO exams (id, user_id, subject_id, title, exam_type, exam_date, start_time, end_time, classroom, syllabus_covered, target_marks, max_marks, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (exam_id, user_id, data["subject_id"], data["title"], data.get("exam_type", "internal_1"), data["exam_date"], data.get("start_time", "09:30"), data.get("end_time", "12:30"), data.get("classroom"), data.get("syllabus_covered"), data.get("target_marks"), data.get("max_marks", 100.0), data.get("notes"), now_iso))
    conn.commit()
    conn.close()
    return {"id": exam_id, "message": "Exam scheduled."}

# ============================================================================
# 7. STUDY SESSIONS & TIME TRACKER API
# ============================================================================
@app.get("/api/study/stats")
def get_study_stats(user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # Today's study time
    cursor.execute("SELECT SUM(duration_minutes) as mins FROM study_sessions WHERE user_id = ? AND date(start_time) = ?", (user_id, today_str))
    today_mins = cursor.fetchone()["mins"] or 0

    # Past 7 days breakdown
    seven_days = []
    for i in range(6, -1, -1):
        d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        d_label = (now - timedelta(days=i)).strftime("%a")
        cursor.execute("SELECT SUM(duration_minutes) as mins FROM study_sessions WHERE user_id = ? AND date(start_time) = ?", (user_id, d))
        m = cursor.fetchone()["mins"] or 0
        seven_days.append({"date": d, "day": d_label, "minutes": m, "hours": round(m / 60.0, 1)})

    # By subject breakdown
    cursor.execute("""
    SELECT s.name, s.code, s.color, SUM(ss.duration_minutes) as total_mins
    FROM study_sessions ss
    JOIN subjects s ON ss.subject_id = s.id
    WHERE ss.user_id = ?
    GROUP BY s.id
    """, (user_id,))
    by_subject = [dict(r) for r in cursor.fetchall()]

    # Recent sessions
    cursor.execute("""
    SELECT ss.*, s.name as subject_name, s.code as subject_code
    FROM study_sessions ss
    LEFT JOIN subjects s ON ss.subject_id = s.id
    WHERE ss.user_id = ?
    ORDER BY ss.start_time DESC
    LIMIT 10
    """, (user_id,))
    recent = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        "today_minutes": today_mins,
        "weekly_chart": seven_days,
        "subject_distribution": by_subject,
        "recent_sessions": recent
    }

@app.post("/api/study/session")
def record_study_session(sess: StudySessionCreate, user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    sess_id = f"sess-{int(datetime.now().timestamp()*1000)}"
    now_iso = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO study_sessions (id, user_id, subject_id, task_id, start_time, end_time, duration_minutes, session_type, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (sess_id, user_id, sess.subject_id, sess.task_id, sess.start_time, sess.end_time, sess.duration_minutes, sess.session_type, sess.notes, now_iso))

    # Update today's study goal progress
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
    INSERT INTO study_goals (id, user_id, date, target_minutes, completed_minutes, is_achieved, created_at)
    VALUES (?, ?, ?, 180, ?, 0, ?)
    ON CONFLICT(user_id, date) DO UPDATE SET
    completed_minutes = completed_minutes + excluded.completed_minutes
    """, (f"sg-{today_str}", user_id, today_str, sess.duration_minutes, now_iso))

    # If linked to task, update actual duration
    if sess.task_id:
        cursor.execute("UPDATE tasks SET actual_duration_minutes = actual_duration_minutes + ? WHERE id = ?", (sess.duration_minutes, sess.task_id))

    conn.commit()
    conn.close()
    return {"id": sess_id, "message": "Study session saved."}

# ============================================================================
# 8. DIGITAL ACADEMIC LIBRARY & PYQ API
# ============================================================================
@app.get("/api/library")
def get_library(user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subjects WHERE user_id = ?", (user_id,))
    subjects = [dict(s) for s in cursor.fetchall()]

    for s in subjects:
        # Modules
        cursor.execute("SELECT * FROM modules WHERE subject_id = ? ORDER BY unit_number ASC", (s["id"],))
        s["modules"] = [dict(m) for m in cursor.fetchall()]

        # Materials
        cursor.execute("SELECT * FROM study_materials WHERE subject_id = ? ORDER BY created_at DESC", (s["id"],))
        s["materials"] = [dict(mat) for mat in cursor.fetchall()]

    conn.close()
    return subjects

@app.post("/api/library/materials")
def add_material(data: Dict[str, Any], user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    mat_id = f"mat-{int(datetime.now().timestamp()*1000)}"
    now_iso = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO study_materials (id, user_id, subject_id, module_id, title, material_type, file_name, file_url, file_size, exam_year, exam_type, semester, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (mat_id, user_id, data["subject_id"], data.get("module_id"), data["title"], data["material_type"], data["file_name"], data.get("file_url", f"/uploads/{data['file_name']}"), data.get("file_size", 1024000), data.get("exam_year"), data.get("exam_type"), data.get("semester", "Semester 5"), now_iso))
    conn.commit()
    conn.close()
    return {"id": mat_id, "message": "Material added to library."}

@app.patch("/api/modules/{module_id}/progress")
def update_module_progress(module_id: str, data: Dict[str, Any]):
    conn = get_connection()
    cursor = conn.cursor()
    status = data.get("status", "completed")
    pct = data.get("syllabus_percentage", 100 if status == "completed" else 50)
    cursor.execute("UPDATE modules SET status = ?, syllabus_percentage = ? WHERE id = ?", (status, pct, module_id))
    conn.commit()
    conn.close()
    return {"message": "Module progress updated"}

# ============================================================================
# 9. NOTIFICATIONS & ALERTS API
# ============================================================================
@app.get("/api/notifications")
def get_notifications(category: Optional[str] = None, user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    if category and category != "all":
        cursor.execute("SELECT * FROM notifications WHERE user_id = ? AND category = ? ORDER BY priority ASC, created_at DESC", (user_id, category))
    else:
        cursor.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY priority ASC, created_at DESC", (user_id,))
    notifs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return notifs

@app.patch("/api/notifications/{notif_id}/read")
def mark_notification_read(notif_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notif_id,))
    conn.commit()
    conn.close()
    return {"message": "Notification marked read"}

@app.post("/api/notifications/mark-all-read")
def mark_all_notifications_read(user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"message": "All marked as read"}

@app.post("/api/notifications/{notif_id}/snooze")
def snooze_notification(notif_id: str, minutes: int = 15):
    conn = get_connection()
    cursor = conn.cursor()
    new_trigger = (datetime.now() + timedelta(minutes=minutes)).isoformat()
    cursor.execute("UPDATE notifications SET is_read = 1, trigger_time = ? WHERE id = ?", (new_trigger, notif_id))
    conn.commit()
    conn.close()
    return {"message": f"Snoozed for {minutes} minutes"}

@app.post("/api/notifications/{notif_id}/resolve")
def resolve_notification(notif_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_resolved = 1, is_read = 1 WHERE id = ?", (notif_id,))
    conn.commit()
    conn.close()
    return {"message": "Underlying issue resolved"}

@app.post("/api/reminder-engine/trigger")
def trigger_reminder_check(user_id: str = "demo-student"):
    alerts = run_reminder_check(user_id)
    return {"message": "Reminder engine tick executed", "generated_alerts": alerts}

# ============================================================================
# 10. SETTINGS & PREFERENCES API
# ============================================================================
@app.get("/api/settings")
def get_settings(user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles WHERE id = ?", (user_id,))
    p = cursor.fetchone()
    cursor.execute("SELECT * FROM notification_preferences WHERE user_id = ?", (user_id,))
    pref = cursor.fetchone()
    conn.close()
    return {
        "profile": dict(p) if p else {},
        "preferences": dict(pref) if pref else {}
    }

@app.post("/api/settings")
def update_settings(data: SettingsUpdate, user_id: str = "demo-student"):
    conn = get_connection()
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()
    if data.full_name or data.default_attendance_threshold or data.daily_study_goal_minutes:
        cursor.execute("""
        UPDATE profiles
        SET full_name = COALESCE(?, full_name),
            college_name = COALESCE(?, college_name),
            default_attendance_threshold = COALESCE(?, default_attendance_threshold),
            daily_study_goal_minutes = COALESCE(?, daily_study_goal_minutes),
            quiet_hours_start = COALESCE(?, quiet_hours_start),
            quiet_hours_end = COALESCE(?, quiet_hours_end),
            updated_at = ?
        WHERE id = ?
        """, (data.full_name, data.college_name, data.default_attendance_threshold, data.daily_study_goal_minutes, data.quiet_hours_start, data.quiet_hours_end, now_iso, user_id))

    cursor.execute("""
    UPDATE notification_preferences
    SET in_app_sound = COALESCE(?, in_app_sound),
        browser_push = COALESCE(?, browser_push),
        quiet_hours_start = COALESCE(?, quiet_hours_start),
        quiet_hours_end = COALESCE(?, quiet_hours_end),
        updated_at = ?
    WHERE user_id = ?
    """, (1 if data.in_app_sound else 0, 1 if data.browser_push else 0, data.quiet_hours_start, data.quiet_hours_end, now_iso, user_id))
    conn.commit()
    conn.close()
    return {"message": "Settings updated"}

# ============================================================================
# 11. PDF REPORT & ANALYTICS API
# ============================================================================
@app.get("/api/reports/download-pdf")
def download_pdf(user_id: str = "demo-student"):
    pdf_filename = f"EduPulse_Report_{user_id}.pdf"
    pdf_path = os.path.join(UPLOADS_DIR, pdf_filename)
    generate_student_pdf_report(user_id, pdf_path)
    return FileResponse(pdf_path, media_type="application/pdf", filename=pdf_filename)

# ============================================================================
# 12. COLLEGE INTEGRATION (LINWAYS / CSV) & DEMO RESET
# ============================================================================
@app.post("/api/integration/import-csv")
def import_csv(file_type: str = Form(...), content: str = Form(...), user_id: str = "demo-student"):
    """
    Parses CSV attendance or timetable records (supports Linways / standard CSV export)
    """
    conn = get_connection()
    cursor = conn.cursor()
    lines = content.strip().split("\n")
    imported = 0
    now_iso = datetime.now().isoformat()

    if file_type == "attendance":
        # Format: SubjectCode, Attended, Total, Target
        for line in lines[1:]:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                code, att, tot = parts[0], int(parts[1]), int(parts[2])
                cursor.execute("""
                UPDATE subjects SET attended_classes = ?, total_classes = ?, updated_at = ?
                WHERE code = ? AND user_id = ?
                """, (att, tot, now_iso, code, user_id))
                imported += 1

    elif file_type == "timetable":
        # Format: Day(0-6), StartTime, EndTime, SubjectCode, Classroom, Faculty
        for line in lines[1:]:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                dow, st, et, code = int(parts[0]), parts[1], parts[2], parts[3]
                room = parts[4] if len(parts) > 4 else "Hall 1"
                fac = parts[5] if len(parts) > 5 else "Staff"
                cursor.execute("SELECT id FROM subjects WHERE code = ? AND user_id = ?", (code, user_id))
                sub = cursor.fetchone()
                if sub:
                    cursor.execute("""
                    INSERT INTO timetable_entries (id, user_id, subject_id, day_of_week, start_time, end_time, classroom, faculty_name, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (f"tt-imp-{imported}-{int(datetime.now().timestamp())}", user_id, sub["id"], dow, st, et, room, fac, now_iso))
                    imported += 1

    conn.commit()
    conn.close()
    return {"message": f"Successfully imported {imported} records from CSV", "imported_count": imported}

@app.post("/api/demo/reset")
def reset_demo():
    seed_demo_data(reset=True)
    return {"message": "Demo data reset successfully."}

# ============================================================================
# STATIC FILES & ROOT SPA ROUTING
# ============================================================================
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
