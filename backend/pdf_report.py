import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from database import get_connection
from reminder_engine import calculate_attendance_metrics

def generate_student_pdf_report(user_id: str, output_path: str) -> str:
    conn = get_connection()
    cursor = conn.cursor()

    # Fetch profile
    cursor.execute("SELECT * FROM profiles WHERE id = ?", (user_id,))
    profile = cursor.fetchone()
    student_name = profile["full_name"] if profile else "Student"
    college = profile["college_name"] if profile else "College"
    dept = profile["department"] if profile else "Dept"
    sem = profile["current_semester"] if profile else "Semester 5"

    # Fetch subjects & attendance
    cursor.execute("SELECT * FROM subjects WHERE user_id = ?", (user_id,))
    subjects = cursor.fetchall()

    # Fetch tasks & assignments
    cursor.execute("SELECT * FROM tasks WHERE user_id = ?", (user_id,))
    tasks = cursor.fetchall()
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t["status"] == "completed")
    overdue_tasks = sum(1 for t in tasks if t["status"] == "overdue")

    cursor.execute("SELECT * FROM assignments WHERE user_id = ?", (user_id,))
    assignments = cursor.fetchall()
    total_asg = len(assignments)
    completed_asg = sum(1 for a in assignments if a["status"] == "completed")
    overdue_asg = sum(1 for a in assignments if a["status"] == "overdue")

    # Fetch study sessions
    cursor.execute("SELECT SUM(duration_minutes) as total_mins FROM study_sessions WHERE user_id = ?", (user_id,))
    study_res = cursor.fetchone()
    total_study_mins = study_res["total_mins"] or 0
    total_study_hours = round(total_study_mins / 60.0, 1)

    # Fetch upcoming exams
    cursor.execute("SELECT e.*, s.name as subject_name FROM exams e JOIN subjects s ON e.subject_id = s.id WHERE e.user_id = ? ORDER BY e.exam_date ASC", (user_id,))
    exams = cursor.fetchall()

    conn.close()

    # Create PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1E1B4B'),
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#6366F1'),
        fontName='Helvetica'
    )
    section_style = ParagraphStyle(
        'SectionHead',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold',
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    story = []

    # Header
    story.append(Paragraph("EDUPULSE ACADEMIC PERFORMANCE & MONITORING REPORT", title_style))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y - %H:%M')} | Confidential Student Analytics", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#6366F1'), spaceAfter=12))

    # Student Summary Box
    summary_data = [
        [Paragraph(f"<b>Student:</b> {student_name}", body_style), Paragraph(f"<b>College:</b> {college}", body_style)],
        [Paragraph(f"<b>Department:</b> {dept}", body_style), Paragraph(f"<b>Academic Level:</b> {sem}", body_style)],
        [Paragraph(f"<b>Study Recorded:</b> {total_study_hours} hrs", body_style), Paragraph(f"<b>On-Time Completion Rate:</b> {round((completed_tasks/max(1, total_tasks))*100)}%", body_style)]
    ]
    t_summary = Table(summary_data, colWidths=[260, 260])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 12))

    # Attendance Health Table
    story.append(Paragraph("1. Subject Attendance Standing & Minimum Threshold Audit", section_style))
    att_table_data = [["Subject Name", "Code", "Conducted", "Attended", "Current %", "Target", "Standing", "Action Needed"]]
    
    total_att = 0
    total_cond = 0
    for s in subjects:
        total_att += s["attended_classes"]
        total_cond += s["total_classes"]
        m = calculate_attendance_metrics(s["attended_classes"], s["total_classes"], s["target_attendance"])
        
        status_color = "#10B981" if m["status"] == "Safe" else ("#F59E0B" if m["status"] == "Warning" else "#EF4444")
        action_text = f"Need {m['classes_needed']} classes" if m['classes_needed'] > 0 else f"Can miss {m['can_miss']} classes"
        
        att_table_data.append([
            s["name"][:26],
            s["code"],
            str(s["total_classes"]),
            str(s["attended_classes"]),
            f"{m['percentage']}%",
            f"{s['target_attendance']}%",
            m["status"],
            action_text
        ])

    overall_pct = round((total_att / max(1, total_cond)) * 100, 1)
    t_att = Table(att_table_data, colWidths=[160, 45, 50, 45, 50, 40, 55, 75])
    t_att.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E1B4B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('FONTSIZE', (0,1), (-1,-1), 7.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
    ]))
    story.append(t_att)
    story.append(Paragraph(f"<b>Overall Aggregate Attendance:</b> {overall_pct}% across {total_cond} total lecture hours.", body_style))
    story.append(Spacer(1, 10))

    # Tasks & Assignment Compliance
    story.append(Paragraph("2. Assignment Compliance & Overdue Status", section_style))
    task_table_data = [["Title", "Subject", "Due Date", "Priority", "Status"]]
    for a in assignments[:6]:
        task_table_data.append([
            a["title"][:30],
            a["subject_id"],
            f"{a['due_date']} {a['due_time']}",
            a["priority"].upper(),
            a["status"].replace("_", " ").upper()
        ])
    for t in tasks[:4]:
        task_table_data.append([
            t["title"][:30],
            t["subject_id"] or "General",
            f"{t['due_date']} {t['due_time']}",
            t["priority"].upper(),
            t["status"].replace("_", " ").upper()
        ])

    t_tasks = Table(task_table_data, colWidths=[190, 80, 95, 65, 90])
    t_tasks.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#312E81')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('FONTSIZE', (0,1), (-1,-1), 7.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
    ]))
    story.append(t_tasks)
    story.append(Spacer(1, 10))

    # Upcoming Examinations & Action Plan
    story.append(Paragraph("3. Upcoming Examinations & Strategic Revision Targets", section_style))
    exam_table_data = [["Exam Title", "Subject", "Date & Time", "Venue", "Target Marks"]]
    for e in exams:
        exam_table_data.append([
            e["title"][:30],
            e["subject_name"][:22],
            f"{e['exam_date']} {e['start_time']}",
            e["classroom"] or "Exam Hall",
            f"{e['target_marks'] or 0}/{e['max_marks']}"
        ])
    t_exams = Table(exam_table_data, colWidths=[180, 130, 95, 65, 50])
    t_exams.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4C1D95')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('FONTSIZE', (0,1), (-1,-1), 7.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
    ]))
    story.append(t_exams)
    story.append(Spacer(1, 12))

    # Actionable AI-Driven Recommendations
    story.append(Paragraph("4. Recommended Academic Intervention & Action Plan", section_style))
    recs = [
        "<b>[CRITICAL ATTENDANCE]:</b> Prioritize attending Discrete Mathematics lectures without fail. You currently need 5 consecutive attendances to exit the red zone.",
        "<b>[IMMEDIATE OVERDUE]:</b> Submit the Operating Systems Kernel Lab Record immediately to avoid permanent grading penalty.",
        "<b>[STUDY PACING]:</b> Allocate at least 90 minutes tonight toward Database Query Indexing to ensure submission before the 23:59 deadline.",
        "<b>[EXAM READINESS]:</b> Begin reviewing Computer Networks Units 1 & 2 formula sheets and previous-year question papers stored in EduPulse Library."
    ]
    for r in recs:
        story.append(Paragraph(f"• {r}", body_style))
        story.append(Spacer(1, 3))

    doc.build(story)
    return output_path
