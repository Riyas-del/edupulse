import os
import shutil
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    # 16:9 Widescreen
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Colors
    BG_DARK = RGBColor(11, 15, 25)        # #0B0F19
    CARD_BG = RGBColor(21, 30, 51)        # #151E33
    CARD_BORDER = RGBColor(49, 46, 129)   # #312E81
    ACCENT_CYAN = RGBColor(56, 189, 248)  # #38BDF8
    ACCENT_PURPLE = RGBColor(129, 140, 248)# #818CF8
    STATUS_CRITICAL = RGBColor(239, 68, 68)# #EF4444
    STATUS_SAFE = RGBColor(16, 185, 129)  # #10B981
    STATUS_WARN = RGBColor(245, 158, 11)  # #F59E0B
    TEXT_WHITE = RGBColor(255, 255, 255)
    TEXT_MUTED = RGBColor(148, 163, 184)  # #94A3B8
    TEXT_CYAN = RGBColor(56, 189, 248)

    def set_slide_background(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_DARK
        bg.line.color.rgb = BG_DARK
        return bg

    def add_header(slide, category, title, subtitle=None):
        # Category Badge
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.4))
        tf_c = cat_box.text_frame
        tf_c.word_wrap = True
        p_c = tf_c.paragraphs[0]
        p_c.text = category.upper()
        p_c.font.size = Pt(11)
        p_c.font.bold = True
        p_c.font.color.rgb = ACCENT_CYAN

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.7), Inches(0.8))
        tf_t = title_box.text_frame
        tf_t.word_wrap = True
        p_t = tf_t.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(26)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_WHITE

        if subtitle:
            p_s = tf_t.add_paragraph()
            p_s.text = subtitle
            p_s.font.size = Pt(13)
            p_s.font.color.rgb = TEXT_MUTED

    def add_card(slide, left, top, width, height, title, items, tag=None, tag_color=ACCENT_CYAN):
        # Card Background
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = CARD_BORDER
        card.line.width = Pt(1.5)

        tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), width - Inches(0.4), height - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True

        p0 = tf.paragraphs[0]
        p0.text = title
        p0.font.size = Pt(16)
        p0.font.bold = True
        p0.font.color.rgb = TEXT_WHITE

        if tag:
            p_tag = tf.add_paragraph()
            p_tag.text = f"● {tag}"
            p_tag.font.size = Pt(10)
            p_tag.font.bold = True
            p_tag.font.color.rgb = tag_color
            p_tag.space_after = Pt(8)

        for item in items:
            p = tf.add_paragraph()
            p.text = f"•  {item}"
            p.font.size = Pt(12)
            p.font.color.rgb = TEXT_MUTED
            p.space_after = Pt(4)

        return card

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1)

    # Decorative Top Accent Bar
    bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.15))
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT_CYAN
    bar.line.fill.background()

    # Main Title Box
    t_box = s1.shapes.add_textbox(Inches(1.2), Inches(1.8), Inches(11), Inches(3.5))
    tf1 = t_box.text_frame
    tf1.word_wrap = True

    p_badge = tf1.paragraphs[0]
    p_badge.text = "SMART ACADEMIC MONITORING & ALARM SYSTEM"
    p_badge.font.size = Pt(14)
    p_badge.font.bold = True
    p_badge.font.color.rgb = ACCENT_CYAN
    p_badge.space_after = Pt(12)

    p_main = tf1.add_paragraph()
    p_main.text = "EDUPULSE"
    p_main.font.size = Pt(56)
    p_main.font.bold = True
    p_main.font.color.rgb = TEXT_WHITE

    p_sub = tf1.add_paragraph()
    p_sub.text = "Academic Deadline Engine • Attendance Recovery Math • Proactive Alarms"
    p_sub.font.size = Pt(20)
    p_sub.font.bold = True
    p_sub.font.color.rgb = ACCENT_PURPLE
    p_sub.space_after = Pt(20)

    p_desc = tf1.add_paragraph()
    p_desc.text = "Core Principle: Never let a student miss a deadline or fall below attendance thresholds."
    p_desc.font.size = Pt(14)
    p_desc.font.italic = True
    p_desc.font.color.rgb = TEXT_MUTED

    # Bottom Meta Card
    meta_box = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(5.6), Inches(10.9), Inches(1.1))
    meta_box.fill.solid()
    meta_box.fill.fore_color.rgb = CARD_BG
    meta_box.line.color.rgb = CARD_BORDER
    meta_tf = meta_box.text_frame
    meta_tf.word_wrap = True
    m_p = meta_tf.paragraphs[0]
    m_p.text = "Student Profile Simulation: Alex Chen | B.Tech Computer Science & Engineering | Semester 5"
    m_p.font.size = Pt(13)
    m_p.font.bold = True
    m_p.font.color.rgb = TEXT_WHITE
    m_p2 = meta_tf.add_paragraph()
    m_p2.text = "Cross-Platform Ecosystem: Android Native APK • Cloud Backend (Render) • Fast & Responsive PWA"
    m_p2.font.size = Pt(11)
    m_p2.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 2: THE PROBLEM STATEMENT
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2)
    add_header(s2, "The Student Challenge", "Academic Friction & The 'Silent Failure' Trap", "Why conventional reminders and generic calendar apps fail modern college students")

    add_card(s2, Inches(0.8), Inches(1.8), Inches(3.6), Inches(5.0),
             "Silent Notifications",
             [
                 "Students receive 100+ generic notifications daily across social & utility apps.",
                 "Passive banners are instantly swiped away or ignored without action.",
                 "No progressive escalation as assignment deadlines draw closer.",
                 "Result: Midnight panic, rushed submissions, and quality drops."
             ], "CRITICAL ISSUE", STATUS_CRITICAL)

    add_card(s2, Inches(4.85), Inches(1.8), Inches(3.6), Inches(5.0),
             "Attendance Math Trap",
             [
                 "Most institutions mandate strict 75% or 80% attendance thresholds.",
                 "Students cannot mentally compute dynamic recovery rates on the fly.",
                 "Late discovery of shortage leads to exam detentions and debars.",
                 "Traditional college portals show static percentages without action guidance."
             ], "ACADEMIC PENALTY", STATUS_WARN)

    add_card(s2, Inches(8.9), Inches(1.8), Inches(3.6), Inches(5.0),
             "Fragmented Workflows",
             [
                 "Syllabi, PYQ question papers, and lab files scattered across WhatsApp & Drives.",
                 "Weekly timetables are static pictures, failing to alert before class start.",
                 "Study timers (Pomodoro) live disconnected from course deadlines.",
                 "Lack of an integrated single-pane student cockpit."
             ], "WORKFLOW LOSS", ACCENT_PURPLE)

    # =========================================================================
    # SLIDE 3: THE EDUPULSE SOLUTION
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3)
    add_header(s3, "Product Innovation", "EduPulse: Proactive Academic Guard", "Engineered specifically to solve academic anxiety through mathematical alerts and focus tools")

    add_card(s3, Inches(0.8), Inches(1.8), Inches(2.7), Inches(5.0),
             "Multi-Stage Alarms",
             [
                 "6 progressive countdown stages (7d, 3d, 1d, 3h, 1h, 0h).",
                 "Web Audio API synthesized siren for urgent alerts.",
                 "State-synchronized dismissals cancel future alerts when completed."
             ], "ALARM ENGINE", STATUS_CRITICAL)

    add_card(s3, Inches(3.75), Inches(1.8), Inches(2.7), Inches(5.0),
             "Attendance Math",
             [
                 "Formula-driven recovery calculator.",
                 "Computes exact classes needed to reach safe zone (e.g., 75%).",
                 "Shows safe absences allowance before dropping into critical danger."
             ], "RECOVERY MATH", STATUS_SAFE)

    add_card(s3, Inches(6.7), Inches(1.8), Inches(2.7), Inches(5.0),
             "Deep Focus Engine",
             [
                 "Built-in 25/5 Pomodoro and flexible Stopwatch modes.",
                 "Direct logging against registered course subjects.",
                 "Daily 120-minute target tracker with crystal bell completion tones."
             ], "FOCUS & TRACKER", ACCENT_CYAN)

    add_card(s3, Inches(9.65), Inches(1.8), Inches(2.8), Inches(5.0),
             "College ERP Bridge",
             [
                 "Direct CSV & LMS parser compatible with Linways exports.",
                 "Instantly imports weekly timetables and attendance registers.",
                 "Certified PDF report generator for academic review."
             ], "ERP INTEGRATION", ACCENT_PURPLE)

    # =========================================================================
    # SLIDE 4: SYSTEM ARCHITECTURE
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4)
    add_header(s4, "System Engineering", "Robust Full-Stack & Native Android Architecture", "High availability, zero-duplicate scheduling, and offline-first capabilities")

    add_card(s4, Inches(0.8), Inches(1.8), Inches(3.6), Inches(5.0),
             "Frontend & PWA Layer",
             [
                 "Dark Navy & Purple Theme (Tailwind CSS with zero flash).",
                 "Responsive Layout: Mobile Bottom Navigation + Desktop Sidebar.",
                 "HTML5 Web Audio API sound synthesizer (no external audio assets needed).",
                 "Chart.js interactive weekly study curves & subject bars.",
                 "Service Worker PWA for offline asset caching."
             ], "CLIENT EXPERIENCE", ACCENT_CYAN)

    add_card(s4, Inches(4.85), Inches(1.8), Inches(3.6), Inches(5.0),
             "FastAPI Backend & Engine",
             [
                 "Python 3.13 REST API with 25+ comprehensive endpoints.",
                 "Background Async Worker running periodic alarm evaluations.",
                 "Idempotent reminder deduplication engine.",
                 "ReportLab automated PDF generation with attendance charts.",
                 "Supabase PostgreSQL + SQLite hybrid persistence."
             ], "CORE BACKEND", ACCENT_PURPLE)

    add_card(s4, Inches(8.9), Inches(1.8), Inches(3.6), Inches(5.0),
             "Native Android & Cloud",
             [
                 "Android WebView + Java Native AlarmBridge (AlarmManager).",
                 "BootReceiver: Restores scheduled alarms upon device restart.",
                 "Cloud Deployment on Render with dynamic PORT binding.",
                 "GitHub Actions CI/CD compiling automated debug APK artifacts.",
                 "Offline asset fallback for instant boot."
             ], "MOBILE & CLOUD", STATUS_SAFE)

    # =========================================================================
    # SLIDE 5: ATTENDANCE RECOVERY ALGORITHM
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5)
    add_header(s5, "Mathematical Foundation", "Attendance Recovery Formula & Live Simulation", "Empowering students with exact numbers instead of vague percentage indicators")

    # Left Box - Mathematical Formulas
    f_card = slide_card = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0))
    f_card.fill.solid()
    f_card.fill.fore_color.rgb = CARD_BG
    f_card.line.color.rgb = CARD_BORDER
    f_card.line.width = Pt(1.5)

    f_tf = f_card.text_frame
    f_tf.word_wrap = True
    fp0 = f_tf.paragraphs[0]
    fp0.text = "Mathematical Formulations"
    fp0.font.size = Pt(18)
    fp0.font.bold = True
    fp0.font.color.rgb = TEXT_WHITE

    fp1 = f_tf.add_paragraph()
    fp1.text = "Where: A = Classes Attended, N = Total Classes, T = Threshold (e.g. 0.75)"
    fp1.font.size = Pt(11)
    fp1.font.color.rgb = ACCENT_CYAN
    fp1.space_after = Pt(12)

    fp2 = f_tf.add_paragraph()
    fp2.text = "1. Classes Needed to Recover (When A / N < T):"
    fp2.font.size = Pt(13)
    fp2.font.bold = True
    fp2.font.color.rgb = STATUS_WARN

    fp3 = f_tf.add_paragraph()
    fp3.text = "    X = ceil( (T * N - A) / (1 - T) )"
    fp3.font.size = Pt(15)
    fp3.font.bold = True
    fp3.font.color.rgb = TEXT_WHITE
    fp3.space_after = Pt(12)

    fp4 = f_tf.add_paragraph()
    fp4.text = "2. Safe Absences Allowed (When A / N >= T):"
    fp4.font.size = Pt(13)
    fp4.font.bold = True
    fp4.font.color.rgb = STATUS_SAFE

    fp5 = f_tf.add_paragraph()
    fp5.text = "    Y = floor( (A - T * N) / T )"
    fp5.font.size = Pt(15)
    fp5.font.bold = True
    fp5.font.color.rgb = TEXT_WHITE
    fp5.space_after = Pt(12)

    fp6 = f_tf.add_paragraph()
    fp6.text = "3. Dynamic What-If Simulation:"
    fp6.font.size = Pt(13)
    fp6.font.bold = True
    fp6.font.color.rgb = ACCENT_PURPLE

    fp7 = f_tf.add_paragraph()
    fp7.text = "    • If Present Today: (A + 1) / (N + 1)\n    • If Absent Today: A / (N + 1)"
    fp7.font.size = Pt(13)
    fp7.font.color.rgb = TEXT_MUTED

    # Right Box - Live Case Study
    add_card(s5, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0),
             "Real Case Study: Alex Chen (CS301 Data Comms)",
             [
                 "Current Record: 25 attended out of 35 conducted (71.4%).",
                 "Institutional Requirement: Minimum 75% threshold.",
                 "Current Status: CRITICAL (Below requirement).",
                 "",
                 "Algorithm Evaluation:",
                 "    • Required: ceil( (0.75 * 35 - 25) / (1 - 0.75) )",
                 "    • ceil( (26.25 - 25) / 0.25 ) = ceil( 5.0 ) = 5 classes",
                 "",
                 "Actionable Directive Shown to Student:",
                 "    🚨 'Attend next 5 consecutive classes to reach 75.0%!'",
                 "    ⚠️ 'Absent today drops percentage to 69.4% (need 7 classes)'."
             ], "LIVE AUDIT CASE", STATUS_CRITICAL)

    # =========================================================================
    # SLIDE 6: MULTI-STAGE DEADLINE & ALARM ENGINE
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6)
    add_header(s6, "Core Innovation", "Multi-Interval Academic Alarm Engine", "Graduated cadence ensures awareness without alert fatigue, escalating to audio siren")

    add_card(s6, Inches(0.8), Inches(1.8), Inches(3.6), Inches(5.0),
             "6-Stage Timeline",
             [
                 "T - 7 Days: Early awareness notification.",
                 "T - 3 Days: Milestone checklist & prep review.",
                 "T - 1 Day: Submission alert & warning tone.",
                 "T - 3 Hours: Urgent banner & high-pitch chime.",
                 "T - 1 Hour: Final alarm with action requirement.",
                 "T - 0 Hour: Overdue alarm & oscillating siren."
             ], "INTERVAL SCHEDULE", ACCENT_CYAN)

    add_card(s6, Inches(4.85), Inches(1.8), Inches(3.6), Inches(5.0),
             "Synthesized Web Audio",
             [
                 "Zero external MP3 dependencies: 100% synthesized in-browser.",
                 "Urgent Siren: Sawtooth oscillator sweeping 800Hz to 1200Hz.",
                 "Warning Chord: Dual sine waves (523Hz & 659Hz).",
                 "Gentle Chime: Exponential frequency ramp (880Hz to 1760Hz).",
                 "Focus Bell: Harmonic triad (587Hz, 880Hz, 1174Hz)."
             ], "AUDIO SYNTHESIZER", STATUS_CRITICAL)

    add_card(s6, Inches(8.9), Inches(1.8), Inches(3.6), Inches(5.0),
             "State Synchronization",
             [
                 "Idempotency Keys: Hash-based reminder deduplication.",
                 "Auto-Cancellation: Marking task 'Completed' instantly purges all pending future alarms.",
                 "Reschedule Intelligence: Changing deadline cancels old jobs and recalculates the 6 stages.",
                 "Quiet Hours: Honors student sleep windows (default 23:00 - 07:00)."
             ], "ENGINE RELIABILITY", STATUS_SAFE)

    # =========================================================================
    # SLIDE 7: TIMETABLE & COLLEGE ERP / LINWAYS IMPORT
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7)
    add_header(s7, "ERP Integration", "College ERP & Linways Data Importer", "Frictionless synchronization from official college portals into smart alert rules")

    add_card(s7, Inches(0.8), Inches(1.8), Inches(3.6), Inches(5.0),
             "Timetable Lead Alerts",
             [
                 "Synchronized with college lecture hours.",
                 "Pre-class alarm (configurable 5 to 15 min lead time).",
                 "Alert details include course name, room number, and faculty.",
                 "Auto-highlights today's next upcoming lecture on dashboard."
             ], "TIMETABLE RADAR", ACCENT_CYAN)

    add_card(s7, Inches(4.85), Inches(1.8), Inches(3.6), Inches(5.0),
             "Linways CSV Importer",
             [
                 "Accepts direct copy-paste or CSV export from Linways/Moodle.",
                 "Parser detects: SubjectCode, Attended, Total, Day, StartTime.",
                 "Bulk upsert into SQLite/Postgres with transaction safety.",
                 "Immediately triggers dynamic attendance recalculation on import."
             ], "CSV INGESTION", STATUS_WARN)

    add_card(s7, Inches(8.9), Inches(1.8), Inches(3.6), Inches(5.0),
             "Study Materials & PYQs",
             [
                 "Organized by Subject & Module (Modules 1 through 5).",
                 "Indexes previous year question papers (PYQs).",
                 "Downloadable PDF syllabus and faculty lecture notes.",
                 "Direct link between pending assignments and library notes."
             ], "RESOURCE REPOSITORY", ACCENT_PURPLE)

    # =========================================================================
    # SLIDE 8: 20-TABLE DATABASE & ARCHITECTURE SCHEMA
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8)
    add_header(s8, "Database Design", "Comprehensive 20-Table Relational Schema", "Full student isolation, transactional logging, and historical audit capability")

    add_card(s8, Inches(0.8), Inches(1.8), Inches(2.7), Inches(5.0),
             "Identity & Profile",
             [
                 "profiles",
                 "student_settings",
                 "academic_semesters",
                 "audit_logs",
                 "Multi-student tenant isolation with UUID foreign keys."
             ], "CORE IDENTITY", ACCENT_CYAN)

    add_card(s8, Inches(3.75), Inches(1.8), Inches(2.7), Inches(5.0),
             "Course & Timetable",
             [
                 "subjects",
                 "timetable_slots",
                 "attendance_logs",
                 "modules",
                 "study_materials",
                 "Tracks attended/total count and room allocations."
             ], "ACADEMIC FABRIC", STATUS_SAFE)

    add_card(s8, Inches(6.7), Inches(1.8), Inches(2.7), Inches(5.0),
             "Tasks & Deadlines",
             [
                 "tasks",
                 "task_reminders",
                 "exams",
                 "exam_schedules",
                 "project_milestones",
                 "Stores deadline status, urgency levels, and lead intervals."
             ], "DEADLINE PIPELINE", STATUS_CRITICAL)

    add_card(s8, Inches(9.65), Inches(1.8), Inches(2.8), Inches(5.0),
             "Study & Analytics",
             [
                 "study_sessions",
                 "daily_study_goals",
                 "notifications",
                 "reports_history",
                 "linways_import_logs",
                 "Tracks focus minutes, streaks, and generated report cards."
             ], "FOCUS & AUDIT", ACCENT_PURPLE)

    # =========================================================================
    # SLIDE 9: VERIFICATION & ACCEPTANCE TESTING
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_background(s9)
    add_header(s9, "Quality Assurance", "Rigorous 14-Scenario Acceptance Test Suite", "Every core requirement mathematically and programmatically verified")

    add_card(s9, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
             "Test Coverage Matrix (14 / 14 Passed)",
             [
                 "[PASS] Test 1: Assignment Due Tomorrow (4 scheduled jobs)",
                 "[PASS] Test 2: Overdue Assignment Detection & Status Update",
                 "[PASS] Test 3: Task Completion & Automatic Reminder Purge",
                 "[PASS] Test 4: Low Attendance Detection (< 75% -> 5 needed)",
                 "[PASS] Test 5: Attendance Recalculation (71.4% -> 73.7%)",
                 "[PASS] Test 6: Timetable Lead-Time Class Reminders",
                 "[PASS] Test 7: Study Session Logging & Daily Accumulation"
             ], "TEST SUITE PART 1", STATUS_SAFE)

    add_card(s9, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0),
             "Enterprise Reliability & Tenancy",
             [
                 "[PASS] Test 8: PYQ & Study Material Library Indexing",
                 "[PASS] Test 9: Project Milestone Multi-Task Alerting",
                 "[PASS] Test 10: Server Reboot & Persistence Recovery",
                 "[PASS] Test 11: Multi-Student Tenant Isolation & Privacy",
                 "[PASS] Test 12: Reminder Deduplication (Zero Duplicate Keys)",
                 "[PASS] Test 13: Deadline Rescheduling & Orphan Clean-up",
                 "[PASS] Test 14: Notification Read/Resolve Synchronization"
             ], "TEST SUITE PART 2", STATUS_SAFE)

    # =========================================================================
    # SLIDE 10: DEPLOYMENT & ECOSYSTEM
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_background(s10)
    add_header(s10, "Ecosystem Delivery", "Live Production Deployments & Artifacts", "Seamless availability across web, cloud, and native mobile environments")

    add_card(s10, Inches(0.8), Inches(1.8), Inches(3.6), Inches(5.0),
             "Android Native App",
             [
                 "Artifact: EduPulse.apk (5.62 MB).",
                 "Targeting Android API 34 (Android 14 ready).",
                 "Exact alarm scheduling via Android AlarmManager.",
                 "Hardware acceleration & native WebChromeClient.",
                 "Available on Desktop and Downloads."
             ], "MOBILE CLIENT", STATUS_SAFE)

    add_card(s10, Inches(4.85), Inches(1.8), Inches(3.6), Inches(5.0),
             "Cloud Web Backend",
             [
                 "Live URL: https://edupulse-4sft.onrender.com",
                 "Docker containerized + dynamic PORT support.",
                 "Automated health-checks and database seeding.",
                 "ReportLab PDF streaming directly from cloud API."
             ], "RENDER CLOUD", ACCENT_CYAN)

    add_card(s10, Inches(8.9), Inches(1.8), Inches(3.6), Inches(5.0),
             "GitHub CI/CD Pipeline",
             [
                 "Repository: github.com/Riyas-del/edupulse",
                 "Automated APK compilation on every push to main.",
                 "Pre-configured Ubuntu runner with JDK 17 & Gradle 8.5.",
                 "Automatic artifact upload and distribution."
             ], "GITHUB DEVOPS", ACCENT_PURPLE)

    # =========================================================================
    # SLIDE 11: SUMMARY & CONCLUSION
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_background(s11)
    add_header(s11, "Project Summary", "EduPulse: Redefining Student Academic Discipline", "Transforming passive calendars into proactive, life-saving academic copilots")

    summary_card = s11.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(11.7), Inches(4.0))
    summary_card.fill.solid()
    summary_card.fill.fore_color.rgb = CARD_BG
    summary_card.line.color.rgb = CARD_BORDER
    summary_card.line.width = Pt(1.5)

    s_tf = summary_card.text_frame
    s_tf.word_wrap = True

    sp0 = s_tf.paragraphs[0]
    sp0.text = "Key Takeaways & Academic Impact"
    sp0.font.size = Pt(20)
    sp0.font.bold = True
    sp0.font.color.rgb = TEXT_WHITE
    sp0.space_after = Pt(14)

    bullets = [
        "Eliminates Academic Blindspots: Students always know the exact number of classes required to remain eligible for examinations.",
        "Zero Missed Deadlines: Multi-interval escalation with Web Audio synthesizer alarms ensures critical assignments cannot be forgotten.",
        "Single Integrated Environment: Timetable, focus timer, study analytics, syllabus notes, and college ERP all in one dark-themed UI.",
        "Production-Grade Architecture: Built with FastAPI, SQLite/PostgreSQL, ReportLab PDFs, and Android Native bridge.",
        "Verified & Certified: 100% acceptance test success across 14 rigorous academic scenarios."
    ]

    for b in bullets:
        p = s_tf.add_paragraph()
        p.text = f"✔  {b}"
        p.font.size = Pt(13)
        p.font.color.rgb = TEXT_MUTED
        p.space_after = Pt(8)

    # Bottom Contact Bar
    bottom_bar = s11.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(6.0), Inches(11.7), Inches(0.8))
    bottom_bar.fill.solid()
    bottom_bar.fill.fore_color.rgb = RGBColor(30, 27, 75)
    bottom_bar.line.color.rgb = ACCENT_CYAN
    bb_tf = bottom_bar.text_frame
    bb_tf.word_wrap = True
    bb_p = bb_tf.paragraphs[0]
    bb_p.text = "Live Demo: https://edupulse-4sft.onrender.com  |  Demo Account: alex.chen@nit.edu / StudyGuard@2026"
    bb_p.font.size = Pt(12)
    bb_p.font.bold = True
    bb_p.font.color.rgb = ACCENT_CYAN
    bb_p.alignment = PP_ALIGN.CENTER

    # Save to targets
    targets = [
        r'C:\Users\JCET\Desktop\EduPulse_Presentation.pptx',
        r'C:\Users\JCET\Downloads\EduPulse_Presentation.pptx',
        r'C:\Users\JCET\.gemini\antigravity\scratch\edupulse\EduPulse_Presentation.pptx'
    ]

    for t in targets:
        os.makedirs(os.path.dirname(t), exist_ok=True)
        prs.save(t)
        print(f"Presentation saved to: {t} ({os.path.getsize(t)/1024:.1f} KB)")

if __name__ == '__main__':
    create_presentation()
