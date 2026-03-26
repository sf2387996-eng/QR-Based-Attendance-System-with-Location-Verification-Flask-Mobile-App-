from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from models import db, Student, Teacher, Department
from routes.auth import token_required

users_bp = Blueprint('users', __name__)

# ── List all users (students + teachers) with search & pagination ──
@users_bp.route('/api/users', methods=['GET'])
@token_required
def get_users(current_admin):
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search   = request.args.get('search', '').strip()
    role     = request.args.get('role', '').strip()

    users = []

    if role != 'Teacher':
        q = Student.query
        if search:
            q = q.filter(Student.name.ilike(f'%{search}%') | Student.email.ilike(f'%{search}%'))
        users += [s.to_dict() for s in q.all()]

    if role != 'Student':
        q = Teacher.query
        if search:
            q = q.filter(Teacher.name.ilike(f'%{search}%') | Teacher.email.ilike(f'%{search}%'))
        users += [t.to_dict() for t in q.all()]

    total = len(users)
    start = (page - 1) * per_page
    end   = start + per_page

    return jsonify({
        'users': users[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    })

# ── Get single user ─────────────────────────────────
@users_bp.route('/api/users/<string:role>/<int:user_id>', methods=['GET'])
@token_required
def get_user(current_admin, role, user_id):
    Model = Student if role == 'student' else Teacher
    user = Model.query.get_or_404(user_id)
    return jsonify(user.to_dict())

# ── Create user ──────────────────────────────────────
@users_bp.route('/api/users', methods=['POST'])
@token_required
def create_user(current_admin):
    data = request.get_json()
    if not data or not data.get('name') or not data.get('email') or not data.get('role'):
        return jsonify({'error': 'Name, email, and role are required'}), 400
    if not data.get('password'):
        return jsonify({'error': 'Password is required'}), 400

    role = data['role']
    dept_id = data.get('department_id')
    hashed_pw = generate_password_hash(data['password'])

    if role == 'Student':
        if Student.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 409
        user = Student(
            name=data['name'], email=data['email'],
            password=hashed_pw,
            department_id=dept_id,
            roll_number=data.get('roll_number')
        )
    elif role == 'Teacher':
        if Teacher.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 409
        user = Teacher(
            name=data['name'], email=data['email'],
            password=hashed_pw,
            department_id=dept_id
        )
    else:
        return jsonify({'error': 'Role must be Student or Teacher'}), 400

    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201

# ── Update user ──────────────────────────────────────
@users_bp.route('/api/users/<string:role>/<int:user_id>', methods=['PUT'])
@token_required
def update_user(current_admin, role, user_id):
    data = request.get_json()
    Model = Student if role == 'student' else Teacher
    user = Model.query.get_or_404(user_id)

    if data.get('name'):
        user.name = data['name']
    if data.get('email'):
        user.email = data['email']
    if data.get('password'):
        user.password = generate_password_hash(data['password'])
    if 'department_id' in data:
        user.department_id = data['department_id']
    if role == 'student' and 'roll_number' in data:
        user.roll_number = data['roll_number']

    db.session.commit()
    return jsonify(user.to_dict())

# ── Delete user ──────────────────────────────────────
@users_bp.route('/api/users/<string:role>/<int:user_id>', methods=['DELETE'])
@token_required
def delete_user(current_admin, role, user_id):
    from models import Attendance, AttendanceSession, Course
    Model = Student if role == 'student' else Teacher
    user = Model.query.get_or_404(user_id)
    try:
        if role == 'student':
            Attendance.query.filter_by(student_id=user_id).delete()
        else:
            # Teacher: delete their sessions, then unassign their courses
            AttendanceSession.query.filter_by(teacher_id=user_id).delete()
            Course.query.filter_by(teacher_id=user_id).update({'teacher_id': None})
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete user: {str(e)}'}), 500

# Note: Department routes moved to routes/departments.py
