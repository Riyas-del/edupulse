-- ============================================================================
-- EduPulse: Smart Student Study Monitoring & Alarm System
-- Complete Supabase PostgreSQL Schema with RLS and Indexes
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. PROFILES
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT NOT NULL,
    college_name TEXT DEFAULT 'National Institute of Technology',
    department TEXT DEFAULT 'Computer Science & Engineering',
    current_semester TEXT DEFAULT 'Semester 5',
    daily_study_goal_minutes INTEGER DEFAULT 180,
    default_attendance_threshold NUMERIC(5,2) DEFAULT 75.00,
    quiet_hours_start TEXT DEFAULT '22:00',
    quiet_hours_end TEXT DEFAULT '07:00',
    alarm_sound TEXT DEFAULT 'urgent_chime',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. SEMESTERS
CREATE TABLE IF NOT EXISTS public.semesters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_current BOOLEAN DEFAULT TRUE,
    target_attendance_percentage NUMERIC(5,2) DEFAULT 75.00,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. SUBJECTS
CREATE TABLE IF NOT EXISTS public.subjects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    semester_id UUID REFERENCES public.semesters(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    faculty_name TEXT,
    faculty_email TEXT,
    classroom TEXT,
    target_attendance NUMERIC(5,2) DEFAULT 75.00,
    total_classes INTEGER DEFAULT 0,
    attended_classes INTEGER DEFAULT 0,
    color TEXT DEFAULT '#38BDF8',
    credits INTEGER DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. ATTENDANCE_RECORDS
CREATE TABLE IF NOT EXISTS public.attendance_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('present', 'absent', 'cancelled', 'holiday')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. TIMETABLE_ENTRIES
CREATE TABLE IF NOT EXISTS public.timetable_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    semester_id UUID REFERENCES public.semesters(id) ON DELETE SET NULL,
    subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), -- 0=Mon, 6=Sun
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    classroom TEXT,
    faculty_name TEXT,
    is_cancelled BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. ASSIGNMENTS
CREATE TABLE IF NOT EXISTS public.assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    assigned_date DATE DEFAULT CURRENT_DATE,
    due_date DATE NOT NULL,
    due_time TIME NOT NULL DEFAULT '23:59',
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    estimated_duration_minutes INTEGER DEFAULT 120,
    status TEXT NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed', 'overdue')),
    attachment_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. TASKS
CREATE TABLE IF NOT EXISTS public.tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subject_id UUID REFERENCES public.subjects(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    task_type TEXT NOT NULL DEFAULT 'daily' CHECK (task_type IN ('daily', 'assignment', 'lab_record', 'project', 'exam_prep', 'study_goal', 'admin')),
    start_date DATE DEFAULT CURRENT_DATE,
    due_date DATE NOT NULL,
    due_time TIME DEFAULT '23:59',
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    estimated_duration_minutes INTEGER DEFAULT 60,
    actual_duration_minutes INTEGER DEFAULT 0,
    completion_percentage INTEGER DEFAULT 0 CHECK (completion_percentage BETWEEN 0 AND 100),
    status TEXT NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed', 'overdue')),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. TASK_SUBTASKS
CREATE TABLE IF NOT EXISTS public.task_subtasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    is_completed BOOLEAN DEFAULT FALSE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. PROJECTS
CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subject_id UUID REFERENCES public.subjects(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    start_date DATE DEFAULT CURRENT_DATE,
    deadline DATE NOT NULL,
    progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage BETWEEN 0 AND 100),
    supervisor_name TEXT,
    supervisor_contact TEXT,
    team_members TEXT,
    document_url TEXT,
    submission_status TEXT NOT NULL DEFAULT 'in_progress' CHECK (submission_status IN ('planning', 'in_progress', 'under_review', 'submitted')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. PROJECT_MILESTONES
CREATE TABLE IF NOT EXISTS public.project_milestones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    due_date DATE NOT NULL,
    is_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11. EXAMS
CREATE TABLE IF NOT EXISTS public.exams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
    semester_id UUID REFERENCES public.semesters(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    exam_type TEXT NOT NULL DEFAULT 'internal_1' CHECK (exam_type IN ('internal_1', 'internal_2', 'semester', 'practical', 'viva')),
    exam_date DATE NOT NULL,
    start_time TIME NOT NULL DEFAULT '09:30',
    end_time TIME NOT NULL DEFAULT '12:30',
    classroom TEXT,
    syllabus_covered TEXT,
    target_marks NUMERIC(5,2),
    max_marks NUMERIC(5,2) DEFAULT 100.00,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12. STUDY_SESSIONS
CREATE TABLE IF NOT EXISTS public.study_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subject_id UUID REFERENCES public.subjects(id) ON DELETE SET NULL,
    task_id UUID REFERENCES public.tasks(id) ON DELETE SET NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    duration_minutes INTEGER NOT NULL DEFAULT 0,
    session_type TEXT NOT NULL DEFAULT 'focus' CHECK (session_type IN ('focus', 'pomodoro', 'manual')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13. STUDY_GOALS
CREATE TABLE IF NOT EXISTS public.study_goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    target_minutes INTEGER NOT NULL DEFAULT 180,
    completed_minutes INTEGER NOT NULL DEFAULT 0,
    is_achieved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, date)
);

-- 14. MODULES
CREATE TABLE IF NOT EXISTS public.modules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
    unit_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed')),
    syllabus_percentage INTEGER DEFAULT 0 CHECK (syllabus_percentage BETWEEN 0 AND 100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 15. STUDY_MATERIALS
CREATE TABLE IF NOT EXISTS public.study_materials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
    module_id UUID REFERENCES public.modules(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    material_type TEXT NOT NULL CHECK (material_type IN ('lecture_notes', 'presentation', 'syllabus', 'pyq', 'lab_record', 'guidelines')),
    file_name TEXT NOT NULL,
    file_url TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    exam_year INTEGER,
    exam_type TEXT,
    semester TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 16. NOTIFICATION_PREFERENCES
CREATE TABLE IF NOT EXISTS public.notification_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    in_app_sound BOOLEAN DEFAULT TRUE,
    browser_push BOOLEAN DEFAULT TRUE,
    quiet_hours_enabled BOOLEAN DEFAULT TRUE,
    quiet_hours_start TIME DEFAULT '22:00',
    quiet_hours_end TIME DEFAULT '07:00',
    attendance_warning_threshold NUMERIC(5,2) DEFAULT 80.00,
    reminder_7d BOOLEAN DEFAULT TRUE,
    reminder_3d BOOLEAN DEFAULT TRUE,
    reminder_1d BOOLEAN DEFAULT TRUE,
    reminder_3h BOOLEAN DEFAULT TRUE,
    reminder_1h BOOLEAN DEFAULT TRUE,
    timetable_lead_minutes INTEGER DEFAULT 15,
    repeated_overdue_interval_hours INTEGER DEFAULT 6,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 17. NOTIFICATIONS
CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('critical', 'attendance', 'assignment', 'overdue', 'project', 'exam', 'timetable', 'study')),
    priority INTEGER NOT NULL DEFAULT 4 CHECK (priority BETWEEN 1 AND 6),
    related_type TEXT,
    related_id TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    is_resolved BOOLEAN DEFAULT FALSE,
    dismissed_at TIMESTAMPTZ,
    trigger_time TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 18. REMINDER_JOBS (Idempotency and background scheduling)
CREATE TABLE IF NOT EXISTS public.reminder_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    related_type TEXT NOT NULL,
    related_id TEXT NOT NULL,
    reminder_trigger_time TIMESTAMPTZ NOT NULL,
    reminder_type TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'delivered', 'cancelled')),
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 19. HOLIDAYS
CREATE TABLE IF NOT EXISTS public.holidays (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    name TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 20. ACADEMIC_REPORTS
CREATE TABLE IF NOT EXISTS public.academic_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    report_type TEXT NOT NULL DEFAULT 'weekly' CHECK (report_type IN ('weekly', 'monthly', 'semester')),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_study_minutes INTEGER DEFAULT 0,
    attendance_average NUMERIC(5,2) DEFAULT 0.00,
    tasks_completed INTEGER DEFAULT 0,
    tasks_overdue INTEGER DEFAULT 0,
    critical_issues_count INTEGER DEFAULT 0,
    report_data_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- Strict multi-tenant isolation: students can only access their own data
-- ============================================================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.semesters ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.attendance_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.timetable_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.task_subtasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.project_milestones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exams ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.study_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.study_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.modules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.study_materials ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reminder_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.holidays ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.academic_reports ENABLE ROW LEVEL SECURITY;

-- Standard user_id RLS policies
DO $$
DECLARE
    tbl text;
    tables text[] := ARRAY[
        'profiles', 'semesters', 'subjects', 'attendance_records', 'timetable_entries',
        'assignments', 'tasks', 'projects', 'exams', 'study_sessions', 'study_goals',
        'modules', 'study_materials', 'notification_preferences', 'notifications',
        'reminder_jobs', 'holidays', 'academic_reports'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        EXECUTE format('DROP POLICY IF EXISTS "%s_user_isolation" ON public.%I', tbl, tbl);
        IF tbl = 'profiles' THEN
            EXECUTE format('CREATE POLICY "%s_user_isolation" ON public.%I FOR ALL USING (auth.uid() = id) WITH CHECK (auth.uid() = id)', tbl, tbl);
        ELSE
            EXECUTE format('CREATE POLICY "%s_user_isolation" ON public.%I FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id)', tbl, tbl);
        END IF;
    END LOOP;
END $$;

-- Policies for sub-tables with foreign keys (task_subtasks, project_milestones)
DROP POLICY IF EXISTS "subtasks_user_isolation" ON public.task_subtasks;
CREATE POLICY "subtasks_user_isolation" ON public.task_subtasks FOR ALL USING (
    EXISTS (SELECT 1 FROM public.tasks t WHERE t.id = task_subtasks.task_id AND t.user_id = auth.uid())
);

DROP POLICY IF EXISTS "milestones_user_isolation" ON public.project_milestones;
CREATE POLICY "milestones_user_isolation" ON public.project_milestones FOR ALL USING (
    EXISTS (SELECT 1 FROM public.projects p WHERE p.id = project_milestones.project_id AND p.user_id = auth.uid())
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_subjects_user ON public.subjects(user_id);
CREATE INDEX IF NOT EXISTS idx_attendance_user_sub ON public.attendance_records(user_id, subject_id, date);
CREATE INDEX IF NOT EXISTS idx_timetable_user_day ON public.timetable_entries(user_id, day_of_week);
CREATE INDEX IF NOT EXISTS idx_assignments_user_due ON public.assignments(user_id, due_date, status);
CREATE INDEX IF NOT EXISTS idx_tasks_user_due ON public.tasks(user_id, due_date, status);
CREATE INDEX IF NOT EXISTS idx_exams_user_date ON public.exams(user_id, exam_date);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON public.notifications(user_id, is_read, trigger_time);
CREATE INDEX IF NOT EXISTS idx_reminder_jobs_sched ON public.reminder_jobs(status, reminder_trigger_time);
