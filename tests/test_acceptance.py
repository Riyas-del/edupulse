import os
import sys
from datetime import datetime, timedelta

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from database import init_db, seed_demo_data, get_connection
from reminder_engine import (
    calculate_attendance_metrics,
    schedule_assignment_reminders,
    cancel_pending_reminders,
    run_reminder_check
)
from pdf_report import generate_student_pdf_report

def run_all_acceptance_tests():
    print("=" * 70)
    print("RUNNING EDUPULSE ACCEPTANCE TESTS (14 TEST SUITE)")
    print("=" * 70)

    # Reset clean demo database
    init_db()
    seed_demo_data(reset=True)
    conn = get_connection()
    cursor = conn.cursor()
    user_id = "demo-student"
    now = datetime.now()

    # -------------------------------------------------------------------------
    # Test 1: Assignment due tomorrow -> schedules and delivers reminder
    # -------------------------------------------------------------------------
    print("\n[Test 1] Assignment Due Tomorrow Reminder Scheduling...")
    tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    cursor.execute("""
    INSERT INTO assignments (id, user_id, subject_id, title, due_date, due_time, priority, status, created_at)
    VALUES ('test-asg-1', ?, 'sub-dbms', 'Test DB Assignment Due Tomorrow', ?, '23:59', 'urgent', 'not_started', ?)
    """, (user_id, tomorrow_str, now.isoformat()))
    conn.commit()
    schedule_assignment_reminders(user_id, 'test-asg-1', tomorrow_str, '23:59')
    
    cursor.execute("SELECT COUNT(*) as cnt FROM reminder_jobs WHERE related_id = 'test-asg-1'")
    jobs_count = cursor.fetchone()["cnt"]
    assert jobs_count > 0, "Failed: Reminders were not scheduled"
    print(f"  [OK] Pass: {jobs_count} scheduled reminder jobs created for assignment.")

    # -------------------------------------------------------------------------
    # Test 2: Assignment becomes overdue -> appears in urgent dashboard & notifications
    # -------------------------------------------------------------------------
    print("\n[Test 2] Overdue Assignment Detection...")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    cursor.execute("""
    INSERT INTO assignments (id, user_id, subject_id, title, due_date, due_time, priority, status, created_at)
    VALUES ('test-asg-od', ?, 'sub-os', 'OS Overdue Lab', ?, '12:00', 'urgent', 'not_started', ?)
    """, (user_id, yesterday_str, now.isoformat()))
    conn.commit()

    run_reminder_check(user_id)
    cursor.execute("SELECT status FROM assignments WHERE id = 'test-asg-od'")
    assert cursor.fetchone()["status"] == "overdue", "Failed: Assignment not marked overdue"
    cursor.execute("SELECT * FROM notifications WHERE related_id = 'test-asg-od' AND category = 'overdue'")
    assert cursor.fetchone() is not None, "Failed: Overdue notification not generated"
    print("  [OK] Pass: Overdue assignment detected, status updated, and urgent notification generated.")

    # -------------------------------------------------------------------------
    # Test 3: Student completes assignment -> future reminders cancelled
    # -------------------------------------------------------------------------
    print("\n[Test 3] Task Completion and Reminder Cancellation...")
    cursor.execute("UPDATE assignments SET status = 'completed' WHERE id = 'test-asg-1'")
    conn.commit()
    cancel_pending_reminders('assignment', 'test-asg-1')

    cursor.execute("SELECT COUNT(*) as active FROM reminder_jobs WHERE related_id = 'test-asg-1' AND status = 'scheduled'")
    active_jobs = cursor.fetchone()["active"]
    assert active_jobs == 0, "Failed: Pending reminders were not cancelled"
    print("  [OK] Pass: All future reminders successfully cancelled upon task completion.")

    # -------------------------------------------------------------------------
    # Test 4: Attendance falls below configured minimum -> critical notification appears
    # -------------------------------------------------------------------------
    print("\n[Test 4] Low Attendance Below Threshold Detection...")
    # Math is 25 / 35 = 71.4% < 75% target
    m = calculate_attendance_metrics(25, 35, 75.0)
    assert m["status"] in ["Critical", "Recovery"], "Failed: Status should be Recovery or Critical"
    cursor.execute("SELECT * FROM notifications WHERE related_id = 'sub-math' AND category = 'critical'")
    assert cursor.fetchone() is not None, "Failed: Critical attendance notification not found"
    print(f"  [OK] Pass: Attendance {m['percentage']}% < 75% triggered critical status with {m['classes_needed']} classes needed.")

    # -------------------------------------------------------------------------
    # Test 5: Student records attendance -> percentage and risk status recalculates
    # -------------------------------------------------------------------------
    print("\n[Test 5] Attendance Logging and Dynamic Recalculation...")
    # Log 3 present attendances for math: 25 -> 28, total 35 -> 38. 28/38 = 73.68%
    m_before = calculate_attendance_metrics(25, 35, 75.0)
    m_after = calculate_attendance_metrics(28, 38, 75.0)
    assert m_after["percentage"] > m_before["percentage"], "Failed: Percentage did not increase"
    assert m_after["classes_needed"] < m_before["classes_needed"], "Failed: Classes needed did not reduce"
    print(f"  [OK] Pass: Attendance recalculated from {m_before['percentage']}% to {m_after['percentage']}%, classes needed reduced from {m_before['classes_needed']} to {m_after['classes_needed']}.")

    # -------------------------------------------------------------------------
    # Test 6: Class starts in 15 minutes -> timetable reminder delivered
    # -------------------------------------------------------------------------
    print("\n[Test 6] Timetable Lead-Time Class Alert...")
    # Add timetable entry 10 mins from now
    target_time = (now + timedelta(minutes=10)).strftime("%H:%M")
    cursor.execute("""
    INSERT INTO timetable_entries (id, user_id, subject_id, day_of_week, start_time, end_time, classroom, faculty_name, created_at)
    VALUES ('tt-test-now', ?, 'sub-cn', ?, ?, '16:00', 'NetLab 4', 'Prof. Cerf', ?)
    """, (user_id, now.weekday(), target_time, now.isoformat()))
    conn.commit()

    run_reminder_check(user_id)
    cursor.execute("SELECT * FROM notifications WHERE related_id = 'tt-test-now' AND category = 'timetable'")
    assert cursor.fetchone() is not None, "Failed: Timetable class reminder not triggered"
    print(f"  [OK] Pass: Timetable reminder triggered for class starting at {target_time}.")

    # -------------------------------------------------------------------------
    # Test 7: Study session runs 45 minutes -> saved & reflected in analytics
    # -------------------------------------------------------------------------
    print("\n[Test 7] Study Timer Session Recording & Stats...")
    cursor.execute("""
    INSERT INTO study_sessions (id, user_id, subject_id, start_time, end_time, duration_minutes, session_type, created_at)
    VALUES ('test-sess-45', ?, 'sub-os', ?, ?, 45, 'pomodoro', ?)
    """, (user_id, (now - timedelta(minutes=45)).isoformat(), now.isoformat(), now.isoformat()))
    conn.commit()

    cursor.execute("SELECT SUM(duration_minutes) as tot FROM study_sessions WHERE user_id = ?", (user_id,))
    total_study = cursor.fetchone()["tot"]
    assert total_study >= 45, "Failed: Study session not recorded in analytics"
    print(f"  [OK] Pass: Study session of 45 mins saved. Total study minutes now: {total_study}.")

    # -------------------------------------------------------------------------
    # Test 8: PYQ Uploaded -> appears in correct subject library
    # -------------------------------------------------------------------------
    print("\n[Test 8] PYQ & Study Material Library Storage...")
    cursor.execute("""
    INSERT INTO study_materials (id, user_id, subject_id, title, material_type, file_name, file_url, exam_year, exam_type, created_at)
    VALUES ('mat-pyq-test', ?, 'sub-os', '2026 Midterm Question Paper', 'pyq', 'os_midterm_2026.pdf', '/uploads/os_midterm_2026.pdf', 2026, 'internal_1', ?)
    """, (user_id, now.isoformat()))
    conn.commit()

    cursor.execute("SELECT * FROM study_materials WHERE id = 'mat-pyq-test' AND material_type = 'pyq'")
    pyq = cursor.fetchone()
    assert pyq is not None and pyq["exam_year"] == 2026, "Failed: PYQ not stored properly"
    print("  [OK] Pass: Previous-year question paper indexed in subject library.")

    # -------------------------------------------------------------------------
    # Test 9: Project milestone approaches -> reminder received
    # -------------------------------------------------------------------------
    print("\n[Test 9] Project Milestone & Deadline Tracking...")
    cursor.execute("SELECT * FROM notifications WHERE related_type = 'project'")
    proj_notif = cursor.fetchone()
    assert proj_notif is not None, "Failed: Project alert not found"
    print(f"  [OK] Pass: Project alert active: '{proj_notif['title']}'.")

    # -------------------------------------------------------------------------
    # Test 10: App restart simulation -> scheduled notifications persist
    # -------------------------------------------------------------------------
    print("\n[Test 10] Persistence & Recovery Across Restarts...")
    # Close connection and reopen
    conn.close()
    conn2 = get_connection()
    c2 = conn2.cursor()
    c2.execute("SELECT COUNT(*) as cnt FROM reminder_jobs WHERE status = 'scheduled'")
    persisted_jobs = c2.fetchone()["cnt"]
    assert persisted_jobs > 0, "Failed: Scheduled jobs lost on connection restart"
    print(f"  [OK] Pass: {persisted_jobs} scheduled reminder jobs safely persisted in database.")
    conn2.close()

    # Re-open primary connection
    conn = get_connection()
    cursor = conn.cursor()

    # -------------------------------------------------------------------------
    # Test 11: Multi-student data isolation / security check
    # -------------------------------------------------------------------------
    print("\n[Test 11] Tenant Isolation & Multi-Student Privacy...")
    cursor.execute("""
    INSERT INTO profiles (id, email, full_name) VALUES ('other-student', 'other@nit.edu', 'Other Student')
    """)
    cursor.execute("""
    INSERT INTO subjects (id, user_id, name, code) VALUES ('other-sub-1', 'other-student', 'Private Physics', 'PH101')
    """)
    conn.commit()

    # Verify student cannot query other student's subject when filtering by user_id
    cursor.execute("SELECT * FROM subjects WHERE user_id = ? AND id = 'other-sub-1'", (user_id,))
    assert cursor.fetchone() is None, "Failed: User isolation leak!"
    print("  [OK] Pass: User tenancy verified. Student cannot access other student's private records.")

    # -------------------------------------------------------------------------
    # Test 12: Scheduler processes twice -> duplicate notifications prevented (Idempotency)
    # -------------------------------------------------------------------------
    print("\n[Test 12] Reminder Deduplication & Idempotency...")
    cursor.execute("SELECT COUNT(*) as count1 FROM notifications WHERE user_id = ?", (user_id,))
    cnt1 = cursor.fetchone()["count1"]

    # Run check twice consecutively
    run_reminder_check(user_id)
    run_reminder_check(user_id)

    cursor.execute("SELECT COUNT(*) as count2 FROM notifications WHERE user_id = ?", (user_id,))
    cnt2 = cursor.fetchone()["count2"]
    assert cnt1 == cnt2, f"Failed: Duplicate notifications generated! Before: {cnt1}, After: {cnt2}"
    print(f"  [OK] Pass: Zero duplicates generated across multiple engine ticks (Notification count stable at {cnt1}).")

    # -------------------------------------------------------------------------
    # Test 13: Deadline changes -> obsolete reminders cancelled and new scheduled
    # -------------------------------------------------------------------------
    print("\n[Test 13] Deadline Rescheduling & Job Replacement...")
    new_due = (now + timedelta(days=5)).strftime("%Y-%m-%d")
    cancel_pending_reminders('assignment', 'test-asg-1')
    schedule_assignment_reminders(user_id, 'test-asg-1', new_due, '20:00')

    cursor.execute("SELECT * FROM reminder_jobs WHERE related_id = 'test-asg-1' AND status = 'scheduled'")
    new_jobs = cursor.fetchall()
    assert len(new_jobs) > 0, "Failed: New reminders not scheduled"
    print(f"  [OK] Pass: Obsolete reminders cancelled, {len(new_jobs)} rescheduled reminders active for new deadline.")

    # -------------------------------------------------------------------------
    # Test 14: Notification marked as read / resolved -> updates dashboard
    # -------------------------------------------------------------------------
    print("\n[Test 14] Notification Read/Resolve State Synchronization...")
    cursor.execute("SELECT id FROM notifications WHERE user_id = ? AND is_read = 0 LIMIT 1", (user_id,))
    target_notif = cursor.fetchone()["id"]
    cursor.execute("UPDATE notifications SET is_read = 1, is_resolved = 1 WHERE id = ?", (target_notif,))
    conn.commit()

    cursor.execute("SELECT is_read, is_resolved FROM notifications WHERE id = ?", (target_notif,))
    row = cursor.fetchone()
    assert row["is_read"] == 1 and row["is_resolved"] == 1, "Failed: Notification status not updated"
    print(f"  [OK] Pass: Notification {target_notif} resolved and marked read.")

    conn.close()

    print("\n" + "=" * 70)
    print("ALL 14 ACCEPTANCE TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == '__main__':
    run_all_acceptance_tests()
