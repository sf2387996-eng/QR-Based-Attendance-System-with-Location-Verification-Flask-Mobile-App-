import io, csv
from flask import Blueprint, request, jsonify, send_file
from sqlalchemy import func, case
from datetime import datetime
from models import db, Attendance, Student, Course
from routes.auth import token_required

reports_bp = Blueprint('reports', __name__)

# ── Student-wise report ──────────────────────────────
@reports_bp.route('/api/reports/student', methods=['GET'])
@token_required
def student_report(current_admin):
    fmt        = request.args.get('format', 'json')         # json | csv | pdf
    student_id = request.args.get('student_id', type=int)
    date_from  = request.args.get('date_from')
    date_to    = request.args.get('date_to')

    q = db.session.query(
        Student.name.label('student'),
        Course.name.label('course'),
        func.count(Attendance.id).label('total'),
        func.sum(case((Attendance.status == 'Present', 1), else_=0)).label('present'),
        func.sum(case((Attendance.status == 'Absent', 1), else_=0)).label('absent'),
        func.sum(case((Attendance.status == 'Late', 1), else_=0)).label('late')
    ).join(Student, Attendance.student_id == Student.id
    ).join(Course, Attendance.course_id == Course.id)

    if student_id:
        q = q.filter(Attendance.student_id == student_id)
    if date_from:
        q = q.filter(Attendance.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    if date_to:
        q = q.filter(Attendance.date <= datetime.strptime(date_to, '%Y-%m-%d').date())

    results = q.group_by(Student.name, Course.name).all()

    rows = []
    for r in results:
        pct = round((r.present / r.total) * 100, 1) if r.total > 0 else 0
        rows.append({
            'student': r.student, 'course': r.course,
            'total': r.total, 'present': int(r.present),
            'absent': int(r.absent), 'late': int(r.late),
            'percentage': pct
        })

    if fmt == 'csv':
        return _send_csv(rows, 'student_report.csv')
    if fmt == 'pdf':
        return _send_pdf(rows, 'Student-wise Attendance Report',
                         ['Student', 'Course', 'Total', 'Present', 'Absent', 'Late', '%'],
                         'student_report.pdf')
    return jsonify(rows)

# ── Subject-wise report ──────────────────────────────
@reports_bp.route('/api/reports/subject', methods=['GET'])
@token_required
def subject_report(current_admin):
    fmt       = request.args.get('format', 'json')
    course_id = request.args.get('course_id', type=int)
    date_from = request.args.get('date_from')
    date_to   = request.args.get('date_to')

    q = db.session.query(
        Course.name.label('course'),
        func.count(Attendance.id).label('total'),
        func.sum(case((Attendance.status == 'Present', 1), else_=0)).label('present'),
        func.sum(case((Attendance.status == 'Absent', 1), else_=0)).label('absent'),
        func.sum(case((Attendance.status == 'Late', 1), else_=0)).label('late')
    ).join(Course, Attendance.course_id == Course.id)

    if course_id:
        q = q.filter(Attendance.course_id == course_id)
    if date_from:
        q = q.filter(Attendance.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    if date_to:
        q = q.filter(Attendance.date <= datetime.strptime(date_to, '%Y-%m-%d').date())

    results = q.group_by(Course.name).all()

    rows = []
    for r in results:
        pct = round((r.present / r.total) * 100, 1) if r.total > 0 else 0
        rows.append({
            'course': r.course,
            'total': r.total, 'present': int(r.present),
            'absent': int(r.absent), 'late': int(r.late),
            'percentage': pct
        })

    if fmt == 'csv':
        return _send_csv(rows, 'subject_report.csv')
    if fmt == 'pdf':
        return _send_pdf(rows, 'Subject-wise Attendance Report',
                         ['Course', 'Total', 'Present', 'Absent', 'Late', '%'],
                         'subject_report.pdf')
    return jsonify(rows)

# ═══════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════

def _send_csv(rows, filename):
    if not rows:
        return jsonify({'error': 'No data to export'}), 404
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    mem = io.BytesIO(output.getvalue().encode())
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name=filename)


def _send_pdf(rows, title, headers, filename):
    if not rows:
        return jsonify({'error': 'No data to export'}), 404
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        return jsonify({'error': 'reportlab not installed'}), 500

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 12))

    table_data = [headers]
    for r in rows:
        table_data.append([str(v) for v in r.values()])

    t = Table(table_data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4361ee')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE',   (0, 0), (-1, 0), 11),
        ('FONTSIZE',   (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID',       (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
    ]))
    elements.append(t)
    doc.build(elements)
    buf.seek(0)
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=filename)
