import sqlite3
import os
import json
from datetime import datetime, timedelta, date

DB_PATH = os.path.join(os.path.dirname(__file__), "edupulse.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. profiles
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL,
        full_name TEXT NOT NULL,
        college_name TEXT DEFAULT 'National Institute of Technology',
        department TEXT DEFAULT 'Computer Science & Engineering',
        current_semester TEXT DEFAULT 'Semester 5',
        daily_study_goal_minutes INTEGER DEFAULT 180,
        default_attendance_threshold REAL DEFAULT 75.0,
        quiet_hours_start TEXT DEFAULT '22:00',
        quiet_hours_end TEXT DEFAULT '07:00',
        alarm_sound TEXT DEFAULT 'urgent_chime',
        created_at TEXT,
        updated_at TEXT
    )""")

    # 2. semesters
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS semesters (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        name TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        is_current INTEGER DEFAULT 1,
        target_attendance_percentage REAL DEFAULT 75.0,
        created_at TEXT
    )""")

    # 3. subjects
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        semester_id TEXT,
        name TEXT NOT NULL,
        code TEXT NOT NULL,
        faculty_name TEXT,
        faculty_email TEXT,
        classroom TEXT,
        target_attendance REAL DEFAULT 75.0,
        total_classes INTEGER DEFAULT 0,
        attended_classes INTEGER DEFAULT 0,
        color TEXT DEFAULT '#38BDF8',
        credits INTEGER DEFAULT 3,
        created_at TEXT,
        updated_at TEXT
    )""")

    # 4. attendance_records
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance_records (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        subject_id TEXT NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL, -- present, absent, cancelled, holiday
        notes TEXT,
        created_at TEXT
    )""")

    # 5. timetable_entries
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS timetable_entries (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        semester_id TEXT,
        subject_id TEXT NOT NULL,
        day_of_week INTEGER NOT NULL, -- 0=Mon, 6=Sun
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        classroom TEXT,
        faculty_name TEXT,
        is_cancelled INTEGER DEFAULT 0,
        notes TEXT,
        created_at TEXT
    )""")

    # 6. assignments
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        subject_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        assigned_date TEXT,
        due_date TEXT NOT NULL,
        due_time TEXT NOT NULL DEFAULT '23:59',
        priority TEXT NOT NULL DEFAULT 'medium', -- low, medium, high, urgent
        estimated_duration_minutes INTEGER DEFAULT 120,
        status TEXT NOT NULL DEFAULT 'not_started', -- not_started, in_progress, completed, overdue
        attachment_url TEXT,
        created_at TEXT,
        updated_at TEXT
    )""")

    # 7. tasks
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        subject_id TEXT,
        title TEXT NOT NULL,
        description TEXT,
        task_type TEXT NOT NULL DEFAULT 'daily', -- daily, assignment, lab_record, project, exam_prep, study_goal, admin
        start_date TEXT,
        due_date TEXT NOT NULL,
        due_time TEXT DEFAULT '23:59',
        priority TEXT NOT NULL DEFAULT 'medium',
        estimated_duration_minutes INTEGER DEFAULT 60,
        actual_duration_minutes INTEGER DEFAULT 0,
        completion_percentage INTEGER DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'not_started',
        completed_at TEXT,
        created_at TEXT,
        updated_at TEXT
    )""")

    # 8. task_subtasks
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_subtasks (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        title TEXT NOT NULL,
        is_completed INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT
    )""")

    # 9. projects
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        subject_id TEXT,
        title TEXT NOT NULL,
        description TEXT,
        start_date TEXT,
        deadline TEXT NOT NULL,
        progress_percentage INTEGER DEFAULT 0,
        supervisor_name TEXT,
        supervisor_contact TEXT,
        team_members TEXT,
        document_url TEXT,
        submission_status TEXT NOT NULL DEFAULT 'in_progress',
        created_at TEXT,
        updated_at TEXT
    )""")

    # 10. project_milestones
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS project_milestones (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        due_date TEXT NOT NULL,
        is_completed INTEGER DEFAULT 0,
        created_at TEXT
    )""")

    # 11. exams
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exams (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        subject_id TEXT NOT NULL,
        semester_id TEXT,
        title TEXT NOT NULL,
        exam_type TEXT NOT NULL DEFAULT 'internal_1',
        exam_date TEXT NOT NULL,
        start_time TEXT NOT NULL DEFAULT '09:30',
        end_time TEXT NOT NULL DEFAULT '12:30',
        classroom TEXT,
        syllabus_covered TEXT,
        target_marks REAL,
        max_marks REAL DEFAULT 100.0,
        notes TEXT,
        created_at TEXT
    )""")

    # 12. study_sessions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS study_sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        subject_id TEXT,
        task_id TEXT,
        start_time TEXT NOT NULL,
        end_time TEXT,
        duration_minutes INTEGER NOT NULL DEFAULT 0,
        session_type TEXT NOT NULL DEFAULT 'focus', -- focus, pomodoro, manual
        notes TEXT,
        created_at TEXT
    )""")

    # 13. study_goals
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS study_goals (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        date TEXT NOT NULL,
        target_minutes INTEGER NOT NULL DEFAULT 180,
        completed_minutes INTEGER NOT NULL DEFAULT 0,
        is_achieved INTEGER DEFAULT 0,
        created_at TEXT,
        UNIQUE(user_id, date)
    )""")

    # 14. modules
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS modules (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        subject_id TEXT NOT NULL,
        unit_number INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'not_started',
        syllabus_percentage INTEGER DEFAULT 0,
        created_at TEXT
    )""")

    # 15. study_materials
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS study_materials (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        subject_id TEXT NOT NULL,
        module_id TEXT,
        title TEXT NOT NULL,
        material_type TEXT NOT NULL, -- lecture_notes, presentation, syllabus, pyq, lab_record, guidelines
        file_name TEXT NOT NULL,
        file_url TEXT NOT NULL,
        file_size INTEGER DEFAULT 0,
        exam_year INTEGER,
        exam_type TEXT,
        semester TEXT,
        created_at TEXT
    )""")

    # 16. notification_preferences
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notification_preferences (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL UNIQUE,
        in_app_sound INTEGER DEFAULT 1,
        browser_push INTEGER DEFAULT 1,
        quiet_hours_enabled INTEGER DEFAULT 1,
        quiet_hours_start TEXT DEFAULT '22:00',
        quiet_hours_end TEXT DEFAULT '07:00',
        attendance_warning_threshold REAL DEFAULT 80.0,
        reminder_7d INTEGER DEFAULT 1,
        reminder_3d INTEGER DEFAULT 1,
        reminder_1d INTEGER DEFAULT 1,
        reminder_3h INTEGER DEFAULT 1,
        reminder_1h INTEGER DEFAULT 1,
        timetable_lead_minutes INTEGER DEFAULT 15,
        repeated_overdue_interval_hours INTEGER DEFAULT 6,
        created_at TEXT,
        updated_at TEXT
    )""")

    # 17. notifications
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        category TEXT NOT NULL, -- critical, attendance, assignment, overdue, project, exam, timetable, study
        priority INTEGER NOT NULL DEFAULT 4, -- 1 (highest) to 6 (lowest)
        related_type TEXT,
        related_id TEXT,
        is_read INTEGER DEFAULT 0,
        is_resolved INTEGER DEFAULT 0,
        dismissed_at TEXT,
        trigger_time TEXT,
        created_at TEXT
    )""")

    # 18. reminder_jobs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reminder_jobs (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        related_type TEXT NOT NULL,
        related_id TEXT NOT NULL,
        reminder_trigger_time TEXT NOT NULL,
        reminder_type TEXT NOT NULL,
        idempotency_key TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'scheduled', -- scheduled, delivered, cancelled
        delivered_at TEXT,
        created_at TEXT
    )""")

    # 19. holidays
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS holidays (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        date TEXT NOT NULL,
        name TEXT NOT NULL,
        notes TEXT,
        created_at TEXT
    )""")

    # 20. academic_reports
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS academic_reports (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        report_type TEXT NOT NULL DEFAULT 'weekly',
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        total_study_minutes INTEGER DEFAULT 0,
        attendance_average REAL DEFAULT 0.0,
        tasks_completed INTEGER DEFAULT 0,
        tasks_overdue INTEGER DEFAULT 0,
        critical_issues_count INTEGER DEFAULT 0,
        report_data_json TEXT,
        created_at TEXT
    )""")

    conn.commit()
    conn.close()

def seed_demo_data(reset=False):
    conn = get_connection()
    cursor = conn.cursor()

    if reset:
        tables = [
            "profiles", "semesters", "subjects", "attendance_records", "timetable_entries",
            "assignments", "tasks", "task_subtasks", "projects", "project_milestones",
            "exams", "study_sessions", "study_goals", "modules", "study_materials",
            "notification_preferences", "notifications", "reminder_jobs", "holidays", "academic_reports"
        ]
        for tbl in tables:
            cursor.execute(f"DELETE FROM {tbl}")
        conn.commit()

    cursor.execute("SELECT COUNT(*) as count FROM profiles WHERE id = 'demo-student'")
    if cursor.fetchone()["count"] > 0 and not reset:
        conn.close()
        return

    now = datetime.now()
    now_iso = now.isoformat()
    today_str = now.strftime("%Y-%m-%d")
    tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    in_3_days_str = (now + timedelta(days=3)).strftime("%Y-%m-%d")
    in_5_days_str = (now + timedelta(days=5)).strftime("%Y-%m-%d")
    in_10_days_str = (now + timedelta(days=10)).strftime("%Y-%m-%d")
    in_14_days_str = (now + timedelta(days=14)).strftime("%Y-%m-%d")

    # 1. Profile
    cursor.execute("""
    INSERT INTO profiles (id, email, full_name, college_name, department, current_semester, daily_study_goal_minutes, default_attendance_threshold, quiet_hours_start, quiet_hours_end, alarm_sound, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'demo-student', 'alex.chen@nit.edu', 'Alex Chen',
        'National Institute of Technology', 'Computer Science & Engineering',
        'Semester 5', 180, 75.0, '22:00', '07:00', 'urgent_chime', now_iso, now_iso
    ))

    # 2. Semester
    sem_id = 'sem-5'
    cursor.execute("""
    INSERT INTO semesters (id, user_id, name, start_date, end_date, is_current, target_attendance_percentage, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sem_id, 'demo-student', 'Fall 2026 (Semester 5)',
        (now - timedelta(days=60)).strftime("%Y-%m-%d"),
        (now + timedelta(days=90)).strftime("%Y-%m-%d"),
        1, 75.0, now_iso
    ))

    # 3. Subjects
    # Note: Mathematics V has 25 attended out of 35 = 71.4% (CRITICAL, below 75% target!)
    # DBMS: 29 / 38 = 76.3% (WARNING, close to 75%)
    # OS: 34 / 40 = 85.0% (SAFE)
    # Computer Networks: 31 / 40 = 77.5% (WARNING)
    # Algorithms: 30 / 36 = 83.3% (SAFE)
    subjects_data = [
        ('sub-math', 'demo-student', sem_id, 'Discrete Mathematics & Graph Theory', 'CS301', 'Dr. S. Ramanujan', 'ramanujan@nit.edu', 'Room 302', 75.0, 35, 25, '#EF4444', 4),
        ('sub-os', 'demo-student', sem_id, 'Operating Systems & System Architecture', 'CS302', 'Prof. Alan Turing', 'turing@nit.edu', 'Hall A1', 75.0, 40, 34, '#10B981', 4),
        ('sub-dbms', 'demo-student', sem_id, 'Database Management Systems', 'CS303', 'Dr. Edgar Codd', 'codd@nit.edu', 'Lab 2', 75.0, 38, 29, '#F59E0B', 4),
        ('sub-cn', 'demo-student', sem_id, 'Computer Networks & Protocols', 'CS304', 'Prof. Vint Cerf', 'cerf@nit.edu', 'NetLab 4', 75.0, 40, 31, '#8B5CF6', 3),
        ('sub-daa', 'demo-student', sem_id, 'Design & Analysis of Algorithms', 'CS305', 'Dr. Donald Knuth', 'knuth@nit.edu', 'Hall B3', 75.0, 36, 30, '#06B6D4', 4)
    ]
    cursor.executemany("""
    INSERT INTO subjects (id, user_id, semester_id, name, code, faculty_name, faculty_email, classroom, target_attendance, total_classes, attended_classes, color, credits, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7], s[8], s[9], s[10], s[11], s[12], now_iso, now_iso) for s in subjects_data])

    # 4. Attendance Records (Sample history for subjects)
    for sub in ['sub-math', 'sub-os', 'sub-dbms', 'sub-cn', 'sub-daa']:
        for i in range(1, 15):
            d_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            status = 'absent' if (sub == 'sub-math' and i in [1, 3, 7, 10]) else 'present'
            cursor.execute("""
            INSERT INTO attendance_records (id, user_id, subject_id, date, status, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (f"att-{sub}-{i}", 'demo-student', sub, d_str, status, 'Regular session', now_iso))

    # 5. Timetable (Weekly entries)
    # Today's day of week
    today_dow = now.weekday() # 0 = Mon, 6 = Sun
    timetable_samples = [
        # Monday
        ('tt-1', 'demo-student', sem_id, 'sub-os', 0, '09:00', '10:00', 'Hall A1', 'Prof. Alan Turing', 0, 'Kernel Architecture'),
        ('tt-2', 'demo-student', sem_id, 'sub-dbms', 0, '10:15', '11:15', 'Lab 2', 'Dr. Edgar Codd', 0, 'SQL & Indexing'),
        ('tt-3', 'demo-student', sem_id, 'sub-math', 0, '11:30', '12:30', 'Room 302', 'Dr. S. Ramanujan', 0, 'Graph Coloring'),
        ('tt-4', 'demo-student', sem_id, 'sub-cn', 0, '13:30', '15:30', 'NetLab 4', 'Prof. Vint Cerf', 0, 'Socket Programming Lab'),
        # Tuesday
        ('tt-5', 'demo-student', sem_id, 'sub-daa', 1, '09:00', '10:00', 'Hall B3', 'Dr. Donald Knuth', 0, 'Dynamic Programming'),
        ('tt-6', 'demo-student', sem_id, 'sub-os', 1, '10:15', '11:15', 'Hall A1', 'Prof. Alan Turing', 0, 'Memory Management'),
        ('tt-7', 'demo-student', sem_id, 'sub-math', 1, '11:30', '12:30', 'Room 302', 'Dr. S. Ramanujan', 0, 'Combinatorics'),
        # Wednesday
        ('tt-8', 'demo-student', sem_id, 'sub-cn', 2, '09:00', '10:00', 'NetLab 4', 'Prof. Vint Cerf', 0, 'TCP/IP Stack'),
        ('tt-9', 'demo-student', sem_id, 'sub-dbms', 2, '10:15', '11:15', 'Lab 2', 'Dr. Edgar Codd', 0, 'Transaction Isolation'),
        ('tt-10', 'demo-student', sem_id, 'sub-daa', 2, '11:30', '12:30', 'Hall B3', 'Dr. Donald Knuth', 0, 'Greedy Strategies'),
        # Thursday
        ('tt-11', 'demo-student', sem_id, 'sub-math', 3, '09:00', '10:00', 'Room 302', 'Dr. S. Ramanujan', 0, 'Number Theory'),
        ('tt-12', 'demo-student', sem_id, 'sub-os', 3, '10:15', '11:15', 'Hall A1', 'Prof. Alan Turing', 0, 'Virtual Memory Lab'),
        ('tt-13', 'demo-student', sem_id, 'sub-daa', 3, '13:30', '15:30', 'Hall B3', 'Dr. Donald Knuth', 0, 'Algorithm Lab'),
        # Friday
        ('tt-14', 'demo-student', sem_id, 'sub-dbms', 4, '09:00', '10:00', 'Lab 2', 'Dr. Edgar Codd', 0, 'Relational Algebra'),
        ('tt-15', 'demo-student', sem_id, 'sub-cn', 4, '10:15', '11:15', 'NetLab 4', 'Prof. Vint Cerf', 0, 'Routing Protocols'),
        ('tt-16', 'demo-student', sem_id, 'sub-math', 4, '11:30', '12:30', 'Room 302', 'Dr. S. Ramanujan', 0, 'Recurrence Relations')
    ]
    cursor.executemany("""
    INSERT INTO timetable_entries (id, user_id, semester_id, subject_id, day_of_week, start_time, end_time, classroom, faculty_name, is_cancelled, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8], t[9], t[10], now_iso) for t in timetable_samples])

    # 6. Assignments
    # - Due tomorrow: DBMS
    # - Overdue: OS Lab Record
    # - Due in 3 days: DAA
    cursor.execute("""
    INSERT INTO assignments (id, user_id, subject_id, title, description, assigned_date, due_date, due_time, priority, estimated_duration_minutes, status, attachment_url, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'asg-1', 'demo-student', 'sub-dbms', 'B+ Trees & Query Optimization Report',
        'Analyze query execution plans on 1M tuples and construct indexing benchmarks.',
        yesterday_str, tomorrow_str, '23:59', 'urgent', 150, 'in_progress', '/uploads/dbms_spec.pdf', now_iso, now_iso
    ))

    cursor.execute("""
    INSERT INTO assignments (id, user_id, subject_id, title, description, assigned_date, due_date, due_time, priority, estimated_duration_minutes, status, attachment_url, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'asg-2', 'demo-student', 'sub-os', 'Submit Operating Systems Kernel Record',
        'Compilation of page replacement algorithms (FIFO, LRU, Optimal) and benchmark results.',
        (now - timedelta(days=7)).strftime("%Y-%m-%d"), yesterday_str, '17:00', 'urgent', 180, 'overdue', '/uploads/os_lab_template.pdf', now_iso, now_iso
    ))

    cursor.execute("""
    INSERT INTO assignments (id, user_id, subject_id, title, description, assigned_date, due_date, due_time, priority, estimated_duration_minutes, status, attachment_url, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'asg-3', 'demo-student', 'sub-daa', 'Dynamic Programming Subset Sum Assignment',
        'Implement 0/1 knapsack, matrix chain multiplication, and Floyd-Warshall with time complexity proof.',
        yesterday_str, in_3_days_str, '23:59', 'high', 120, 'not_started', None, now_iso, now_iso
    ))

    # 7. Tasks
    tasks_data = [
        ('task-1', 'demo-student', 'sub-os', 'Submit Operating Systems record', 'Hand in printed lab record to Prof. Turing', 'lab_record', yesterday_str, yesterday_str, '17:00', 'urgent', 60, 0, 80, 'overdue', None),
        ('task-2', 'demo-student', 'sub-dbms', 'Database assignment query indexing', 'Finalize B+ tree bench script', 'assignment', yesterday_str, tomorrow_str, '23:59', 'high', 90, 45, 50, 'in_progress', None),
        ('task-3', 'demo-student', 'sub-math', 'Practice 15 Graph Coloring problems', 'Unit 3 exam preparation', 'exam_prep', today_str, in_3_days_str, '20:00', 'medium', 120, 0, 0, 'not_started', None),
        ('task-4', 'demo-student', 'sub-cn', 'Socket Programming TCP Chat Server', 'Implement select() multi-client server', 'assignment', today_str, in_5_days_str, '23:59', 'medium', 150, 60, 40, 'in_progress', None),
        ('task-5', 'demo-student', 'sub-daa', 'Review DAA Chapter 4 Greedy Algorithms', 'Daily revision goal', 'study_goal', today_str, today_str, '22:00', 'low', 45, 45, 100, 'completed', now_iso)
    ]
    cursor.executemany("""
    INSERT INTO tasks (id, user_id, subject_id, title, description, task_type, start_date, due_date, due_time, priority, estimated_duration_minutes, actual_duration_minutes, completion_percentage, status, completed_at, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8], t[9], t[10], t[11], t[12], t[13], t[14], now_iso, now_iso) for t in tasks_data])

    # 8. Task Subtasks
    subtasks = [
        ('st-1', 'task-2', 'Write schema generation SQL', 1, 1),
        ('st-2', 'task-2', 'Generate 1,000,000 synthetic records', 1, 2),
        ('st-3', 'task-2', 'Run EXPLAIN ANALYZE on unindexed queries', 0, 3),
        ('st-4', 'task-2', 'Create composite B+ index and measure speedup', 0, 4)
    ]
    cursor.executemany("""
    INSERT INTO task_subtasks (id, task_id, title, is_completed, sort_order, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, [(s[0], s[1], s[2], s[3], s[4], now_iso) for s in subtasks])

    # 9. Projects
    cursor.execute("""
    INSERT INTO projects (id, user_id, subject_id, title, description, start_date, deadline, progress_percentage, supervisor_name, supervisor_contact, team_members, document_url, submission_status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'proj-1', 'demo-student', 'sub-cn', 'Autonomous Drone Telemetry & Mesh Network',
        'Ad-hoc multi-hop routing protocol for emergency telemetry communication without cellular reception.',
        (now - timedelta(days=30)).strftime("%Y-%m-%d"), in_14_days_str, 45,
        'Dr. R. K. Sharma', 'sharma.rk@nit.edu', 'Alex Chen, Priya Nair, Rohan Verma',
        '/uploads/drone_mesh_proposal.pdf', 'in_progress', now_iso, now_iso
    ))

    # 10. Project Milestones
    milestones = [
        ('ms-1', 'proj-1', 'Protocol Simulation in NS-3', 'Benchmark throughput & packet loss', (now - timedelta(days=10)).strftime("%Y-%m-%d"), 1),
        ('ms-2', 'proj-1', 'Hardware ESP32 LoRa Mesh Test', 'Field range test on campus', in_3_days_str, 0),
        ('ms-3', 'proj-1', 'Final Demonstration & Viva Presentation', 'Faculty presentation & live flight demo', in_14_days_str, 0)
    ]
    cursor.executemany("""
    INSERT INTO project_milestones (id, project_id, title, description, due_date, is_completed, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [(m[0], m[1], m[2], m[3], m[4], m[5], now_iso) for m in milestones])

    # 11. Exams
    cursor.execute("""
    INSERT INTO exams (id, user_id, subject_id, semester_id, title, exam_type, exam_date, start_time, end_time, classroom, syllabus_covered, target_marks, max_marks, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'exam-1', 'demo-student', 'sub-cn', sem_id, 'Computer Networks Midterm Examination',
        'internal_1', in_5_days_str, '09:30', '11:30', 'Exam Hall 3',
        'Units 1 & 2: Physical, Data Link, MAC, Network Layer IP Addressing',
        45.0, 50.0, 'Calculators allowed. Bring student ID.', now_iso
    ))

    cursor.execute("""
    INSERT INTO exams (id, user_id, subject_id, semester_id, title, exam_type, exam_date, start_time, end_time, classroom, syllabus_covered, target_marks, max_marks, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'exam-2', 'demo-student', 'sub-daa', sem_id, 'Algorithms Practical & Viva Exam',
        'practical', in_10_days_str, '14:00', '17:00', 'CS Lab 1',
        'All Units: Sorting, DP, Graphs, Branch & Bound',
        48.0, 50.0, 'Code implementation in C++/Python', now_iso
    ))

    # 12. Study Sessions (Past days)
    sessions = [
        ('sess-1', 'demo-student', 'sub-daa', 'task-5', (now - timedelta(hours=3)).isoformat(), (now - timedelta(hours=2, minutes=15)).isoformat(), 45, 'pomodoro', 'Completed Greedy interval scheduling notes'),
        ('sess-2', 'demo-student', 'sub-os', 'task-1', (now - timedelta(days=1, hours=4)).isoformat(), (now - timedelta(days=1, hours=2)).isoformat(), 120, 'focus', 'Kernel synchronization primitives analysis'),
        ('sess-3', 'demo-student', 'sub-dbms', 'task-2', (now - timedelta(days=2, hours=3)).isoformat(), (now - timedelta(days=2, hours=1, minutes=30)).isoformat(), 90, 'focus', 'B+ tree index benchmarking')
    ]
    cursor.executemany("""
    INSERT INTO study_sessions (id, user_id, subject_id, task_id, start_time, end_time, duration_minutes, session_type, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7], s[8], now_iso) for s in sessions])

    # 13. Study Goals
    cursor.execute("""
    INSERT INTO study_goals (id, user_id, date, target_minutes, completed_minutes, is_achieved, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ('sg-today', 'demo-student', today_str, 180, 45, 0, now_iso))

    # 14. Modules
    modules_data = [
        ('mod-math-1', 'demo-student', 'sub-math', 1, 'Propositional & Predicate Logic', 'Inference rules, truth tables, quantifiers', 'completed', 100),
        ('mod-math-2', 'demo-student', 'sub-math', 2, 'Set Theory & Relations', 'Equivalence relations, partial orderings, lattices', 'completed', 100),
        ('mod-math-3', 'demo-student', 'sub-math', 3, 'Graph Theory & Trees', 'Eulerian paths, planar graphs, chromatic numbers', 'in_progress', 60),
        ('mod-math-4', 'demo-student', 'sub-math', 4, 'Combinatorics & Generating Functions', 'Permutations, recurrence relations', 'not_started', 0),
        ('mod-os-1', 'demo-student', 'sub-os', 1, 'Processes & Threads', 'PCB, IPC, thread pools, race conditions', 'completed', 100),
        ('mod-os-2', 'demo-student', 'sub-os', 2, 'CPU Scheduling & Synchronization', 'Semaphores, monitors, deadlock prevention', 'completed', 100),
        ('mod-os-3', 'demo-student', 'sub-os', 3, 'Memory Management & Paging', 'Virtual memory, page faults, thrashing', 'in_progress', 75),
        ('mod-dbms-1', 'demo-student', 'sub-dbms', 1, 'ER Modeling & Relational Model', 'Entity sets, cardinalities, relational algebra', 'completed', 100),
        ('mod-dbms-2', 'demo-student', 'sub-dbms', 2, 'SQL & Normalization', '1NF, 2NF, 3NF, BCNF, lossy vs lossless join', 'completed', 100),
        ('mod-dbms-3', 'demo-student', 'sub-dbms', 3, 'Indexing & Transactions', 'B+ trees, hash indices, ACID properties, 2PL', 'in_progress', 50)
    ]
    cursor.executemany("""
    INSERT INTO modules (id, user_id, subject_id, unit_number, title, description, status, syllabus_percentage, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7], now_iso) for m in modules_data])

    # 15. Study Materials & PYQs
    materials = [
        ('mat-1', 'demo-student', 'sub-math', 'mod-math-3', 'Graph Theory Formula Cheat Sheet', 'lecture_notes', 'graph_theory_summary.pdf', '/uploads/graph_theory_summary.pdf', 1420000, None, None, 'Semester 5'),
        ('mat-2', 'demo-student', 'sub-dbms', 'mod-dbms-2', 'Relational Normalization Practice Problems', 'lecture_notes', 'dbms_normalization_solved.pdf', '/uploads/dbms_normalization_solved.pdf', 2150000, None, None, 'Semester 5'),
        ('mat-3', 'demo-student', 'sub-cn', None, '2025 Midterm Question Paper with Solutions', 'pyq', 'cn_2025_midterm_pyq.pdf', '/uploads/cn_2025_midterm_pyq.pdf', 3800000, 2025, 'internal_1', 'Semester 5'),
        ('mat-4', 'demo-student', 'sub-os', None, '2024 End-Semester Question Paper', 'pyq', 'os_2024_endsem_pyq.pdf', '/uploads/os_2024_endsem_pyq.pdf', 4100000, 2024, 'semester', 'Semester 5'),
        ('mat-5', 'demo-student', 'sub-daa', None, 'Complete DAA Syllabus & Course Outcome Matrix', 'syllabus', 'daa_syllabus_2026.pdf', '/uploads/daa_syllabus_2026.pdf', 850000, 2026, 'semester', 'Semester 5')
    ]
    cursor.executemany("""
    INSERT INTO study_materials (id, user_id, subject_id, module_id, title, material_type, file_name, file_url, file_size, exam_year, exam_type, semester, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7], m[8], m[9], m[10], m[11], now_iso) for m in materials])

    # 16. Notification Preferences
    cursor.execute("""
    INSERT INTO notification_preferences (id, user_id, in_app_sound, browser_push, quiet_hours_enabled, quiet_hours_start, quiet_hours_end, attendance_warning_threshold, reminder_7d, reminder_3d, reminder_1d, reminder_3h, reminder_1h, timetable_lead_minutes, repeated_overdue_interval_hours, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'pref-demo', 'demo-student', 1, 1, 1, '22:00', '07:00', 80.0, 1, 1, 1, 1, 1, 15, 6, now_iso, now_iso
    ))

    # 17. Seed Initial Notifications matching Prompt Examples!
    notifs = [
        ('notif-1', 'demo-student', 'CRITICAL ATTENDANCE ALERT', 'WARNING: Mathematics attendance is 71.4%. Your target is 75.0%. Attend next 5 consecutive classes to restore safe standing.', 'critical', 1, 'subject', 'sub-math', 0, 0, None, (now - timedelta(hours=1)).isoformat()),
        ('notif-2', 'demo-student', 'OVERDUE TASK', 'OVERDUE: Submit your Operating Systems record. It was due yesterday.', 'overdue', 1, 'task', 'task-1', 0, 0, None, (now - timedelta(hours=5)).isoformat()),
        ('notif-3', 'demo-student', 'URGENT ASSIGNMENT DEADLINE', 'URGENT: Database assignment is due tomorrow at 23:59.', 'assignment', 2, 'assignment', 'asg-1', 0, 0, None, (now - timedelta(hours=2)).isoformat()),
        ('notif-4', 'demo-student', 'PROJECT MILESTONE ALERT', 'PROJECT ALERT: Mini-project milestone (ESP32 LoRa Mesh Test) is due in 3 days.', 'project', 3, 'project', 'proj-1', 0, 0, None, (now - timedelta(hours=6)).isoformat()),
        ('notif-5', 'demo-student', 'DAILY STUDY REMINDER', 'STUDY REMINDER: You have not completed today’s study goal (45/180 mins completed).', 'study', 4, 'study_goal', 'sg-today', 0, 0, None, (now - timedelta(minutes=30)).isoformat()),
        ('notif-6', 'demo-student', 'UPCOMING EXAMINATION', 'EXAM ALERT: Computer Networks Midterm is in 5 days (Nov 3). Review Units 1 & 2.', 'exam', 3, 'exam', 'exam-1', 0, 0, None, (now - timedelta(hours=12)).isoformat())
    ]
    cursor.executemany("""
    INSERT INTO notifications (id, user_id, title, message, category, priority, related_type, related_id, is_read, is_resolved, dismissed_at, trigger_time, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(n[0], n[1], n[2], n[3], n[4], n[5], n[6], n[7], n[8], n[9], n[10], n[11], now_iso) for n in notifs])

    # 18. Reminder Jobs (Pre-scheduled for upcoming events)
    jobs = [
        ('job-1', 'demo-student', 'assignment', 'asg-1', tomorrow_str + ' 12:00:00', '1d_before', 'job_asg1_1d', 'delivered', now_iso),
        ('job-2', 'demo-student', 'assignment', 'asg-1', tomorrow_str + ' 20:59:00', '3h_before', 'job_asg1_3h', 'scheduled', None),
        ('job-3', 'demo-student', 'assignment', 'asg-1', tomorrow_str + ' 22:59:00', '1h_before', 'job_asg1_1h', 'scheduled', None),
        ('job-4', 'demo-student', 'task', 'task-1', today_str + ' 18:00:00', 'repeated_overdue', 'job_task1_od1', 'delivered', now_iso),
        ('job-5', 'demo-student', 'exam', 'exam-1', (now + timedelta(days=2)).strftime("%Y-%m-%d") + ' 09:00:00', '3d_before', 'job_exam1_3d', 'scheduled', None)
    ]
    cursor.executemany("""
    INSERT INTO reminder_jobs (id, user_id, related_type, related_id, reminder_trigger_time, reminder_type, idempotency_key, status, delivered_at, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(j[0], j[1], j[2], j[3], j[4], j[5], j[6], j[7], j[8], now_iso) for j in jobs])

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    seed_demo_data(reset=True)
    print("EduPulse SQLite Database successfully initialized and seeded with 20 tables!")
