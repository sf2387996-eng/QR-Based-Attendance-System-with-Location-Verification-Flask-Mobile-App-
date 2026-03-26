from functools import wraps
from flask import Blueprint, request, jsonify
import jwt, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Admin, Student, Teacher
from config import Config

auth_bp = Blueprint('auth', __name__)

# ── JWT decorator ────────────────────────────────────
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            current_admin = Admin.query.get(data['admin_id'])
            if not current_admin:
                return jsonify({'error': 'Invalid token'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(current_admin, *args, **kwargs)
    return decorated

# ── Admin Login ──────────────────────────────────────
@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    admin = Admin.query.filter_by(email=data['email']).first()
    if not admin or not check_password_hash(admin.password, data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = jwt.encode({
        'admin_id': admin.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    }, Config.SECRET_KEY, algorithm='HS256')

    return jsonify({
        'token': token,
        'admin': admin.to_dict()
    })

# ── Student Login (for Android app) ─────────────────
@auth_bp.route('/api/student/login', methods=['POST'])
def student_login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    student = Student.query.filter_by(email=data['email']).first()
    if not student or not check_password_hash(student.password, data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = jwt.encode({
        'student_id': student.id,
        'role': 'student',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    }, Config.SECRET_KEY, algorithm='HS256')

    return jsonify({
        'token': token,
        'user': student.to_dict()
    })

# ── Teacher Login (for Android app) ─────────────────
@auth_bp.route('/api/teacher/login', methods=['POST'])
def teacher_login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    teacher = Teacher.query.filter_by(email=data['email']).first()
    if not teacher or not check_password_hash(teacher.password, data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = jwt.encode({
        'teacher_id': teacher.id,
        'role': 'teacher',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    }, Config.SECRET_KEY, algorithm='HS256')

    return jsonify({
        'token': token,
        'user': teacher.to_dict()
    })

# ── Verify token (for frontend session check) ───────
@auth_bp.route('/api/verify', methods=['GET'])
@token_required
def verify_token(current_admin):
    return jsonify({'admin': current_admin.to_dict()})
