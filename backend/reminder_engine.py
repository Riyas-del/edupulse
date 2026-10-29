import math
import hashlib
from datetime import datetime, timedelta, time
from typing import Dict, List, Any, Optional
from database import get_connection

def calculate_attendance_metrics(attended: int, total: int, target_percent: float = 75.0) -> Dict[str, Any]:
    """
    Computes accurate attendance percentage, status, consecutive classes required,
    and maximum safe absences according to academic formulas.
    """
    target = float(target_percent)
    if total <= 0:
        return {
            "percentage": 100.0,
            "attended": 0,
            "total": 0,
            "missed": 0,
            "status": "Safe",
            "risk_level": "low",
            "classes_needed": 0,
            "can_miss": 0,
            "message": "No classes conducted yet."
        }

    pct = round((attended / total) * 100.0, 1)
    missed = total - attended
    t_ratio = target / 100.0

    if pct < target:
        # Below target: calculate consecutive classes needed to restore target
        # (attended + C) / (total + C) >= t_ratio
        # C * (1 - t_ratio) >= t_ratio * total - attended
        denom = 1.0 - t_ratio
        if denom > 0:
            numerator = (t_ratio * total) - attended
            classes_needed = max(1, math.ceil(numerator / denom))
        else:
            classes_needed = 999
        
        status = "Critical" if pct < (target - 5.0) else "Recovery"
        risk_level = "critical" if pct < (target - 5.0) else "high"
        can_miss = 0
        message = f"Below target ({target}%). Attend next {classes_needed} consecutive classes to restore safe standing."
    else:
        # Above target: calculate how many classes student can miss safely
        # attended / (total + M) >= t_ratio
        # attended - t_ratio * total >= t_ratio * M
        numerator = attended - (t_ratio * total)
        can_miss = max(0, math.floor(numerator / t_ratio))
        classes_needed = 0

        if pct >= (target + 5.0):
            status = "Safe"
            risk_level = "low"
            message = f"Comfortably above target. You can safely miss up to {can_miss} classes."
        else:
            status = "Warning"
            risk_level = "medium"
            message = f"Approaching minimum threshold ({target}%). You can only miss {can_miss} classes."

    return {
        "percentage": pct,
        "attended": attended,
        "total": total,
        "missed": missed,
        "status": status,
        "risk_level": risk_level,
        "classes_needed": classes_needed,
        "can_miss": can_miss,
        "message": message
    }

def schedule_assignment_reminders(user_id: str, assignment_id: str, due_date_str: str, due_time_str: str = "23:59"):
    """
    Schedules standardized reminder jobs for an assignment:
    - 7 days before
    - 3 days before
    - 1 day before
    - 3 hours before
    - 1 hour before
    - At deadline
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()

    try:
        due_dt = datetime.strptime(f"{due_date_str} {due_time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        due_dt = datetime.strptime(f"{due_date_str} 23:59", "%Y-%m-%d %H:%M")

    intervals = [
        ("7d_before", due_dt - timedelta(days=7)),
        ("3d_before", due_dt - timedelta(days=3)),
        ("1d_before", due_dt - timedelta(days=1)),
        ("3h_before", due_dt - timedelta(hours=3)),
        ("1h_before", due_dt - timedelta(hours=1)),
        ("at_deadline", due_dt)
    ]

    for reminder_type, trigger_time in intervals:
        if trigger_time > now:
            idempotency_key = f"{user_id}_asg_{assignment_id}_{reminder_type}"
            cursor.execute("""
            INSERT OR IGNORE INTO reminder_jobs (id, user_id, related_type, related_id, reminder_trigger_time, reminder_type, idempotency_key, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'scheduled', ?)
            """, (
                f"job-{hashlib.md5(idempotency_key.encode()).hexdigest()[:12]}",
                user_id, 'assignment', assignment_id, trigger_time.strftime("%Y-%m-%d %H:%M:%S"),
                reminder_type, idempotency_key, now.isoformat()
            ))

    conn.commit()
    conn.close()

def cancel_pending_reminders(related_type: str, related_id: str):
    """
    Cancels unnecessary pending reminder jobs when a task/assignment is completed, deleted, or rescheduled.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE reminder_jobs
    SET status = 'cancelled'
    WHERE related_type = ? AND related_id = ? AND status = 'scheduled'
    """, (related_type, related_id))
    conn.commit()
    conn.close()

def run_reminder_check(user_id: str = "demo-student") -> List[Dict[str, Any]]:
    """
    Central reminder engine tick.
    Checks deadlines, attendance, timetable, overdue tasks, and generates notifications
    with strict idempotency to prevent spam or duplicate alerts.
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()
    now_iso = now.isoformat()
    today_str = now.strftime("%Y-%m-%d")
    delivered_alerts = []

    # 1. Fetch user preferences
    cursor.execute("SELECT * FROM notification_preferences WHERE user_id = ?", (user_id,))
    pref = cursor.fetchone()
    att_thresh = pref["attendance_warning_threshold"] if pref else 80.0

    # 2. Check Overdue Assignments & Tasks
    cursor.execute("""
    SELECT a.*, s.name as subject_name, s.code as subject_code
    FROM assignments a
    JOIN subjects s ON a.subject_id = s.id
    WHERE a.user_id = ? AND a.status != 'completed'
    """, (user_id,))
    assignments = cursor.fetchall()

    for a in assignments:
        due_str = f"{a['due_date']} {a['due_time'] if a['due_time'] else '23:59'}"
        try:
            due_dt = datetime.strptime(due_str, "%Y-%m-%d %H:%M")
        except ValueError:
            due_dt = datetime.strptime(f"{a['due_date']} 23:59", "%Y-%m-%d %H:%M")

        # Overdue check
        if due_dt < now and a['status'] != 'overdue':
            # Mark overdue in database
            cursor.execute("UPDATE assignments SET status = 'overdue', updated_at = ? WHERE id = ?", (now_iso, a['id']))
            conn.commit()

            idemp_key = f"notif_asg_overdue_{a['id']}_{now.strftime('%Y%m%d_%H')}"
            cursor.execute("SELECT 1 FROM notifications WHERE related_id = ? AND category = 'overdue' AND is_resolved = 0", (a['id'],))
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO notifications (id, user_id, title, message, category, priority, related_type, related_id, is_read, is_resolved, trigger_time, created_at)
                VALUES (?, ?, ?, ?, 'overdue', 1, 'assignment', ?, 0, 0, ?, ?)
                """, (
                    f"notif-{hashlib.md5(idemp_key.encode()).hexdigest()[:12]}",
                    user_id, f"OVERDUE: {a['title']}",
                    f"Assignment '{a['title']}' for {a['subject_code']} is overdue (Deadline was {due_str}). Submit immediately!",
                    a['id'], now_iso, now_iso
                ))
                conn.commit()
                delivered_alerts.append({"type": "overdue", "title": f"OVERDUE: {a['title']}", "priority": 1})

        # Due tomorrow / within 24h check
        elif 0 <= (due_dt - now).total_seconds() <= 86400:
            cursor.execute("SELECT 1 FROM notifications WHERE related_id = ? AND category = 'assignment' AND is_resolved = 0 AND trigger_time >= ?", 
                           (a['id'], (now - timedelta(hours=12)).isoformat()))
            if not cursor.fetchone():
                hours_left = max(1, int((due_dt - now).total_seconds() // 3600))
                cursor.execute("""
                INSERT INTO notifications (id, user_id, title, message, category, priority, related_type, related_id, is_read, is_resolved, trigger_time, created_at)
                VALUES (?, ?, ?, ?, 'assignment', 1 if ? <= 3 else 2, 'assignment', ?, 0, 0, ?, ?)
                """, (
                    f"notif-due-{a['id']}-{now.strftime('%Y%m%d')}",
                    user_id, f"URGENT DEADLINE: {a['title']}",
                    f"'{a['title']}' ({a['subject_code']}) is due in {hours_left} hour(s) at {a['due_time']}. Complete and submit now.",
                    hours_left, a['id'], now_iso, now_iso
                ))
                conn.commit()
                delivered_alerts.append({"type": "due_soon", "title": f"URGENT: {a['title']}", "priority": 2})

    # 3. Check Tasks Overdue
    cursor.execute("""
    SELECT t.*, s.name as subject_name, s.code as subject_code
    FROM tasks t
    LEFT JOIN subjects s ON t.subject_id = s.id
    WHERE t.user_id = ? AND t.status != 'completed'
    """, (user_id,))
    tasks = cursor.fetchall()
    for t in tasks:
        due_str = f"{t['due_date']} {t['due_time'] if t['due_time'] else '23:59'}"
        try:
            due_dt = datetime.strptime(due_str, "%Y-%m-%d %H:%M")
        except ValueError:
            due_dt = datetime.strptime(f"{t['due_date']} 23:59", "%Y-%m-%d %H:%M")

        if due_dt < now and t['status'] != 'overdue':
            cursor.execute("UPDATE tasks SET status = 'overdue', updated_at = ? WHERE id = ?", (now_iso, t['id']))
            conn.commit()
            cursor.execute("SELECT 1 FROM notifications WHERE related_id = ? AND category = 'overdue' AND is_resolved = 0", (t['id'],))
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO notifications (id, user_id, title, message, category, priority, related_type, related_id, is_read, is_resolved, trigger_time, created_at)
                VALUES (?, ?, ?, ?, 'overdue', 1, 'task', ?, 0, 0, ?, ?)
                """, (
                    f"notif-task-od-{t['id']}",
                    user_id, f"OVERDUE TASK: {t['title']}",
                    f"Task '{t['title']}' is overdue. Please complete it as soon as possible.",
                    t['id'], now_iso, now_iso
                ))
                conn.commit()
                delivered_alerts.append({"type": "overdue_task", "title": f"OVERDUE: {t['title']}", "priority": 1})

    # 4. Check Attendance for All Subjects
    cursor.execute("SELECT * FROM subjects WHERE user_id = ?", (user_id,))
    subjects = cursor.fetchall()
    for s in subjects:
        metrics = calculate_attendance_metrics(s["attended_classes"], s["total_classes"], s["target_attendance"])
        if metrics["percentage"] < s["target_attendance"]:
            # Critical Attendance
            cursor.execute("SELECT 1 FROM notifications WHERE related_id = ? AND category = 'critical' AND is_resolved = 0 AND trigger_time >= ?",
                           (s['id'], (now - timedelta(hours=24)).isoformat()))
            if not cursor.fetchone():
                msg = f"WARNING: {s['name']} attendance is {metrics['percentage']}%. Your target is {s['target_attendance']}%. Attend next {metrics['classes_needed']} consecutive classes to recover."
                cursor.execute("""
                INSERT INTO notifications (id, user_id, title, message, category, priority, related_type, related_id, is_read, is_resolved, trigger_time, created_at)
                VALUES (?, ?, ?, ?, 'critical', 2, 'subject', ?, 0, 0, ?, ?)
                """, (
                    f"notif-att-crit-{s['id']}-{today_str}",
                    user_id, f"CRITICAL ATTENDANCE: {s['code']}",
                    msg, s['id'], now_iso, now_iso
                ))
                conn.commit()
                delivered_alerts.append({"type": "critical_attendance", "title": f"Low Attendance: {s['code']}", "priority": 2})

    # 5. Check Upcoming Classes (Timetable Alarms: 30m, 15m, 5m before class)
    current_dow = now.weekday()
    cursor.execute("""
    SELECT t.*, s.name as subject_name, s.code as subject_code
    FROM timetable_entries t
    JOIN subjects s ON t.subject_id = s.id
    WHERE t.user_id = ? AND t.day_of_week = ? AND t.is_cancelled = 0
    """, (user_id, current_dow))
    today_classes = cursor.fetchall()
    for c in today_classes:
        try:
            start_hour, start_min = map(int, c['start_time'].split(":"))
            class_dt = now.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
            diff_mins = (class_dt - now).total_seconds() / 60.0

            # Trigger class reminder within lead minutes (e.g., 0 to 15 mins before class)
            if 0 <= diff_mins <= 15:
                idemp_key = f"class_{c['id']}_{today_str}_{c['start_time']}"
                cursor.execute("SELECT 1 FROM notifications WHERE related_id = ? AND category = 'timetable' AND trigger_time >= ?",
                               (c['id'], (now - timedelta(hours=1)).isoformat()))
                if not cursor.fetchone():
                    cursor.execute("""
                    INSERT INTO notifications (id, user_id, title, message, category, priority, related_type, related_id, is_read, is_resolved, trigger_time, created_at)
                    VALUES (?, ?, ?, ?, 'timetable', 5, 'timetable', ?, 0, 0, ?, ?)
                    """, (
                        f"notif-tt-{hashlib.md5(idemp_key.encode()).hexdigest()[:12]}",
                        user_id, f"UPCOMING CLASS: {c['subject_code']} in {int(diff_mins)} min(s)",
                        f"Class '{c['subject_name']}' starts at {c['start_time']} in {c['classroom']}. Faculty: {c['faculty_name'] or 'N/A'}.",
                        c['id'], now_iso, now_iso
                    ))
                    conn.commit()
                    delivered_alerts.append({"type": "class_soon", "title": f"Class starting: {c['subject_code']}", "priority": 5})
        except Exception:
            pass

    # 6. Check Project Deadlines & Milestones
    cursor.execute("""
    SELECT p.*, s.code as subject_code
    FROM projects p
    LEFT JOIN subjects s ON p.subject_id = s.id
    WHERE p.user_id = ? AND p.submission_status != 'submitted'
    """, (user_id,))
    projects = cursor.fetchall()
    for p in projects:
        try:
            p_deadline = datetime.strptime(p['deadline'], "%Y-%m-%d")
            days_left = (p_deadline - now).days
            if 0 <= days_left <= 3:
                cursor.execute("SELECT 1 FROM notifications WHERE related_id = ? AND category = 'project' AND is_resolved = 0 AND trigger_time >= ?",
                               (p['id'], (now - timedelta(hours=24)).isoformat()))
                if not cursor.fetchone():
                    cursor.execute("""
                    INSERT INTO notifications (id, user_id, title, message, category, priority, related_type, related_id, is_read, is_resolved, trigger_time, created_at)
                    VALUES (?, ?, ?, ?, 'project', 3, 'project', ?, 0, 0, ?, ?)
                    """, (
                        f"notif-proj-{p['id']}-{today_str}",
                        user_id, f"PROJECT ALERT: {p['title']}",
                        f"Submission deadline is in {days_left} day(s). Current progress is {p['progress_percentage']}%.",
                        p['id'], now_iso, now_iso
                    ))
                    conn.commit()
                    delivered_alerts.append({"type": "project_deadline", "title": f"Project Due: {p['title']}", "priority": 3})
        except Exception:
            pass

    # 7. Check Exams within 5 days
    cursor.execute("""
    SELECT e.*, s.name as subject_name, s.code as subject_code
    FROM exams e
    JOIN subjects s ON e.subject_id = s.id
    WHERE e.user_id = ?
    """, (user_id,))
    exams = cursor.fetchall()
    for e in exams:
        try:
            exam_dt = datetime.strptime(f"{e['exam_date']} {e['start_time']}", "%Y-%m-%d %H:%M")
            days_left = (exam_dt - now).days
            if 0 <= days_left <= 7:
                cursor.execute("SELECT 1 FROM notifications WHERE related_id = ? AND category = 'exam' AND is_resolved = 0 AND trigger_time >= ?",
                               (e['id'], (now - timedelta(hours=48)).isoformat()))
                if not cursor.fetchone():
                    cursor.execute("""
                    INSERT INTO notifications (id, user_id, title, message, category, priority, related_type, related_id, is_read, is_resolved, trigger_time, created_at)
                    VALUES (?, ?, ?, ?, 'exam', 3, 'exam', ?, 0, 0, ?, ?)
                    """, (
                        f"notif-exam-{e['id']}-{today_str}",
                        user_id, f"EXAMINATION IN {days_left} DAYS",
                        f"'{e['title']}' ({e['subject_code']}) scheduled for {e['exam_date']} at {e['start_time']}. Venue: {e['classroom']}.",
                        e['id'], now_iso, now_iso
                    ))
                    conn.commit()
                    delivered_alerts.append({"type": "exam_soon", "title": f"Exam Alert: {e['title']}", "priority": 3})
        except Exception:
            pass

    conn.close()
    return delivered_alerts
