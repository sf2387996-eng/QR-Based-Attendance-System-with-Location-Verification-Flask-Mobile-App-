from flask import Blueprint, request, jsonify
from sqlalchemy import func, case
from datetime import datetime, timedelta
from models import db, Attendance, Student, Course
from routes.auth import token_required

attendance_bp = Blueprint('attendance', __name__)

# ── List attendance with filters ─────────────────────
@attendance_bp.route('/api/attendance', methods=['GET'])
@token_required
def get_attendance(current_admin):
    page       = request.args.get('page', 1, type=int)
    per_page   = request.args.get('per_page', 10, type=int)
    date_from  = request.args.get('date_from')
    date_to    = request.args.get('date_to')
    student_id = request.args.get('student_id', type=int)
    course_id  = request.args.get('course_id', type=int)
    status     = request.args.get('status', '').strip()

    q = Attendance.query

    if date_from:
        q = q.filter(Attendance.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    if date_to:
        q = q.filter(Attendance.date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    if student_id:
        q = q.filter_by(student_id=student_id)
    if course_id:
        q = q.filter_by(course_id=course_id)
    if status:
        q = q.filter_by(status=status)

    pagination = q.order_by(Attendance.date.desc(), Attendance.marked_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'attendance': [a.to_dict() for a in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })

# ── Dashboard statistics ─────────────────────────────
@attendance_bp.route('/api/dashboard', methods=['GET'])
@token_required
def dashboard(current_admin):
    from models import Teacher
    total_students = Student.query.count()
    total_teachers = Teacher.query.count()
    total_courses  = Course.query.count()

    today = datetime.utcnow().date()
    week_start = today - timedelta(days=today.weekday())

    today_present = Attendance.query.filter(
        Attendance.date == today, Attendance.status == 'Present'
    ).count()
    today_absent = Attendance.query.filter(
        Attendance.date == today, Attendance.status == 'Absent'
    ).count()
    today_late = Attendance.query.filter(
        Attendance.date == today, Attendance.status == 'Late'
    ).count()
    today_total = today_present + today_absent + today_late

    # Weekly attendance breakdown (last 7 days)
    weekly_data = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        present = Attendance.query.filter(Attendance.date == d, Attendance.status == 'Present').count()
        absent  = Attendance.query.filter(Attendance.date == d, Attendance.status == 'Absent').count()
        late    = Attendance.query.filter(Attendance.date == d, Attendance.status == 'Late').count()
        weekly_data.append({
            'date': d.isoformat(),
            'day': d.strftime('%a'),
            'present': present, 'absent': absent, 'late': late
        })

    return jsonify({
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_courses': total_courses,
        'today': {
            'present': today_present,
            'absent': today_absent,
            'late': today_late,
            'total': today_total
        },
        'weekly': weekly_data
    })

# ── Attendance percentage per student ────────────────
@attendance_bp.route('/api/attendance/stats', methods=['GET'])
@token_required
def attendance_stats(current_admin):
    course_id  = request.args.get('course_id', type=int)

    q = db.session.query(
        Attendance.student_id,
        Student.name,
        func.count(Attendance.id).label('total'),
        func.sum(case((Attendance.status == 'Present', 1), else_=0)).label('present'),
        func.sum(case((Attendance.status == 'Absent', 1), else_=0)).label('absent'),
        func.sum(case((Attendance.status == 'Late', 1), else_=0)).label('late')
    ).join(Student, Attendance.student_id == Student.id)

    if course_id:
        q = q.filter(Attendance.course_id == course_id)

    results = q.group_by(Attendance.student_id, Student.name).all()

    stats = []
    for r in results:
        pct = round((r.present / r.total) * 100, 1) if r.total > 0 else 0
        stats.append({
            'student_id': r.student_id, 'student': r.name,
            'total': r.total, 'present': int(r.present),
            'absent': int(r.absent), 'late': int(r.late),
            'percentage': pct
        })

    return jsonify(stats)

# ── Students list (for filter dropdown) ──────────────
@attendance_bp.route('/api/students', methods=['GET'])
@token_required
def get_students(current_admin):
    students = Student.query.order_by(Student.name).all()
    return jsonify([{'id': s.id, 'name': s.name} for s in students])
