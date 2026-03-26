from flask import Blueprint, request, jsonify
from datetime import datetime
from models import db, Course, Timetable, Teacher, Department
from routes.auth import token_required

courses_bp = Blueprint('courses', __name__)

# ── List courses ─────────────────────────────────────
@courses_bp.route('/api/courses', methods=['GET'])
@token_required
def get_courses(current_admin):
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search   = request.args.get('search', '').strip()

    q = Course.query
    if search:
        q = q.filter(Course.name.ilike(f'%{search}%') | Course.code.ilike(f'%{search}%'))

    pagination = q.order_by(Course.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'courses': [c.to_dict() for c in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })

# ── All courses (no pagination, for dropdowns) ──────
@courses_bp.route('/api/courses/all', methods=['GET'])
@token_required
def get_all_courses(current_admin):
    courses = Course.query.order_by(Course.name).all()
    return jsonify([c.to_dict() for c in courses])

# ── Create course ────────────────────────────────────
@courses_bp.route('/api/courses', methods=['POST'])
@token_required
def create_course(current_admin):
    data = request.get_json()
    if not data or not data.get('name') or not data.get('code'):
        return jsonify({'error': 'Name and code are required'}), 400

    if Course.query.filter_by(code=data['code']).first():
        return jsonify({'error': 'Course code already exists'}), 409

    course = Course(
        name=data['name'], code=data['code'],
        department_id=data.get('department_id'),
        teacher_id=data.get('teacher_id')
    )
    db.session.add(course)
    db.session.commit()
    return jsonify(course.to_dict()), 201

# ── Update course ────────────────────────────────────
@courses_bp.route('/api/courses/<int:course_id>', methods=['PUT'])
@token_required
def update_course(current_admin, course_id):
    data = request.get_json()
    course = Course.query.get_or_404(course_id)

    if data.get('name'):  course.name = data['name']
    if data.get('code'):  course.code = data['code']
    if 'department_id' in data: course.department_id = data['department_id']
    if 'teacher_id' in data:    course.teacher_id = data['teacher_id']

    db.session.commit()
    return jsonify(course.to_dict())

# ── Delete course ────────────────────────────────────
@courses_bp.route('/api/courses/<int:course_id>', methods=['DELETE'])
@token_required
def delete_course(current_admin, course_id):
    from models import Attendance, AttendanceSession
    course = Course.query.get_or_404(course_id)
    try:
        # Delete related records first to avoid FK constraint errors
        Attendance.query.filter_by(course_id=course_id).delete()
        AttendanceSession.query.filter_by(course_id=course_id).delete()
        Timetable.query.filter_by(course_id=course_id).delete()
        db.session.delete(course)
        db.session.commit()
        return jsonify({'message': 'Course deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete course: {str(e)}'}), 500

# ── Teachers list (for assigning) ────────────────────
@courses_bp.route('/api/teachers', methods=['GET'])
@token_required
def get_teachers(current_admin):
    teachers = Teacher.query.order_by(Teacher.name).all()
    return jsonify([t.to_dict() for t in teachers])

# ═══════════════════════════════════════════════════════
# Timetable endpoints
# ═══════════════════════════════════════════════════════

@courses_bp.route('/api/timetable', methods=['GET'])
@token_required
def get_timetable(current_admin):
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    course_id = request.args.get('course_id', type=int)

    q = Timetable.query
    if course_id:
        q = q.filter_by(course_id=course_id)

    pagination = q.order_by(Timetable.day_of_week, Timetable.start_time).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        'timetable': [t.to_dict() for t in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })

@courses_bp.route('/api/timetable', methods=['POST'])
@token_required
def create_timetable(current_admin):
    data = request.get_json()
    required = ['course_id', 'day_of_week', 'start_time', 'end_time']
    if not data or not all(data.get(k) for k in required):
        return jsonify({'error': 'course_id, day_of_week, start_time, end_time are required'}), 400

    entry = Timetable(
        course_id=data['course_id'],
        day_of_week=data['day_of_week'],
        start_time=datetime.strptime(data['start_time'], '%H:%M').time(),
        end_time=datetime.strptime(data['end_time'], '%H:%M').time(),
        room=data.get('room')
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify(entry.to_dict()), 201

@courses_bp.route('/api/timetable/<int:entry_id>', methods=['PUT'])
@token_required
def update_timetable(current_admin, entry_id):
    data = request.get_json()
    entry = Timetable.query.get_or_404(entry_id)

    if data.get('course_id'):   entry.course_id = data['course_id']
    if data.get('day_of_week'): entry.day_of_week = data['day_of_week']
    if data.get('start_time'):  entry.start_time = datetime.strptime(data['start_time'], '%H:%M').time()
    if data.get('end_time'):    entry.end_time = datetime.strptime(data['end_time'], '%H:%M').time()
    if 'room' in data:          entry.room = data['room']

    db.session.commit()
    return jsonify(entry.to_dict())

@courses_bp.route('/api/timetable/<int:entry_id>', methods=['DELETE'])
@token_required
def delete_timetable(current_admin, entry_id):
    entry = Timetable.query.get(entry_id)
    if not entry:
        return jsonify({'error': 'Timetable entry not found'}), 404
    try:
        db.session.delete(entry)
        db.session.commit()
        return jsonify({'message': 'Timetable entry deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete timetable entry: {str(e)}'}), 500
