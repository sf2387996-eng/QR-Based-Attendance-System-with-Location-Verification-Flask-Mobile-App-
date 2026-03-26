"""
Mobile API endpoints for the Android Attendance App.

Provides:
  POST /api/auth/login          – Unified student/teacher login
  GET  /api/users/me            – Current user profile
  POST /api/attendance/scan_qr  – Student scans QR
  POST /api/attendance/generate_qr – Teacher generates QR session
  GET  /api/attendance/my_attendance – Student attendance history
  GET  /api/attendance/teacher/sessions – Teacher's sessions
  GET  /api/attendance/session/<id> – Session detail with records
"""

import uuid, io, math, base64
from functools import wraps
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify
import jwt
from werkzeug.security import check_password_hash

from config import Config
from models import db, Student, Teacher, Course, Attendance, AttendanceSession

mobile_bp = Blueprint('mobile', __name__)

# ── QR configuration ────────────────────────────────
QR_EXPIRY_SECONDS = 600        # 10 minutes
MAX_DISTANCE_METERS = 200      # max GPS distance for attendance


# ═══════════════════════════════════════════════════════
# JWT decorator for mobile (student / teacher)
# ═══════════════════════════════════════════════════════

def mobile_token_required(f):
    """Decode JWT that contains either student_id+role or teacher_id+role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        parts = auth_header.split()
        if len(parts) == 2 and parts[0] == 'Bearer':
            token = parts[1]

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        role = data.get('role', '')
        user = None

        if role == 'student':
            user = Student.query.get(data.get('student_id'))
        elif role == 'teacher':
            user = Teacher.query.get(data.get('teacher_id'))

        if not user:
            return jsonify({'error': 'Invalid token – user not found'}), 401

        return f(user, role, *args, **kwargs)
    return decorated


# ═══════════════════════════════════════════════════════
# Authentication
# ═══════════════════════════════════════════════════════

@mobile_bp.route('/api/auth/login', methods=['POST'])
def unified_login():
    """
    Unified login: try Student first, then Teacher.
    Request body: { email, password }
    Response: { token, user }
    """
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    email = data['email'].strip()
    password = data['password']

    # Try student
    student = Student.query.filter_by(email=email).first()
    if student and check_password_hash(student.password, password):
        token = jwt.encode({
            'student_id': student.id,
            'role': 'student',
            'exp': datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS)
        }, Config.SECRET_KEY, algorithm='HS256')
        return jsonify({'token': token, 'user': student.to_dict()})

    # Try teacher
    teacher = Teacher.query.filter_by(email=email).first()
    if teacher and check_password_hash(teacher.password, password):
        token = jwt.encode({
            'teacher_id': teacher.id,
            'role': 'teacher',
            'exp': datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS)
        }, Config.SECRET_KEY, algorithm='HS256')
        return jsonify({'token': token, 'user': teacher.to_dict()})

    return jsonify({'error': 'Invalid email or password'}), 401


@mobile_bp.route('/api/users/me', methods=['GET'])
@mobile_token_required
def get_me(current_user, role):
    """Return current user profile."""
    return jsonify({'user': current_user.to_dict()})


# ═══════════════════════════════════════════════════════
# Student endpoints
# ═══════════════════════════════════════════════════════

@mobile_bp.route('/api/attendance/scan_qr', methods=['POST'])
@mobile_token_required
def scan_qr(current_user, role):
    """
    Student scans QR code to mark attendance.
    Body: { qr_data, latitude, longitude }
    """
    if role != 'student':
        return jsonify({'error': 'Only students can scan QR'}), 403

    data = request.get_json()
    if not data or not data.get('qr_data'):
        return jsonify({'error': 'qr_data is required'}), 400

    qr_token = data['qr_data'].strip()
    student_lat = data.get('latitude', 0.0)
    student_lng = data.get('longitude', 0.0)

    # Find session by QR token
    session = AttendanceSession.query.filter_by(qr_token=qr_token).first()
    if not session:
        return jsonify({'error': 'Invalid QR code – session not found'}), 404

    # Check expiry
    now = datetime.utcnow()
    if now > session.expires_at:
        return jsonify({'error': 'QR code has expired'}), 410

    # Check GPS distance
    distance = _haversine(student_lat, student_lng,
                          float(session.latitude or 0), float(session.longitude or 0))
    if distance > MAX_DISTANCE_METERS:
        return jsonify({
            'error': f'You are {distance:.0f}m away from the class (max {MAX_DISTANCE_METERS}m)',
            'distance_from_class': distance
        }), 403

    # Check duplicate
    existing = Attendance.query.filter_by(
        student_id=current_user.id,
        course_id=session.course_id,
        date=now.date()
    ).first()
    if existing:
        return jsonify({'error': 'Attendance already recorded for this session'}), 409

    # Mark attendance
    record = Attendance(
        student_id=current_user.id,
        course_id=session.course_id,
        date=now.date(),
        status='Present',
        latitude=student_lat,
        longitude=student_lng,
        marked_at=now,
        session_id=session.id
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({
        'message': 'Attendance recorded successfully!',
        'record': record.to_dict(),
        'distance_from_class': round(distance, 1)
    })


@mobile_bp.route('/api/attendance/my_attendance', methods=['GET'])
@mobile_token_required
def my_attendance(current_user, role):
    """
    Student's attendance history with per-subject stats.
    Returns: { records, subject_stats, overall_percentage,
               total_classes, total_classes_attended }
    """
    if role != 'student':
        return jsonify({'error': 'Only students can view their attendance'}), 403

    records = Attendance.query.filter_by(student_id=current_user.id) \
        .order_by(Attendance.date.desc(), Attendance.marked_at.desc()).all()

    # Per-subject stats
    subject_stats = {}
    total_present = 0
    for r in records:
        name = r.course.name if r.course else 'Unknown'
        if name not in subject_stats:
            subject_stats[name] = {'present': 0, 'total': 0, 'percentage': 0.0}
        subject_stats[name]['total'] += 1
        if r.status == 'Present':
            subject_stats[name]['present'] += 1
            total_present += 1

    for name, stat in subject_stats.items():
        stat['percentage'] = round(
            (stat['present'] / stat['total']) * 100, 1
        ) if stat['total'] > 0 else 0.0

    total_classes = len(records)
    overall_pct = round(
        (total_present / total_classes) * 100, 1
    ) if total_classes > 0 else 0.0

    return jsonify({
        'records': [r.to_dict() for r in records],
        'subject_stats': subject_stats,
        'overall_percentage': overall_pct,
        'total_classes': total_classes,
        'total_classes_attended': total_present
    })


# ═══════════════════════════════════════════════════════
# Teacher endpoints
# ═══════════════════════════════════════════════════════

@mobile_bp.route('/api/attendance/generate_qr', methods=['POST'])
@mobile_token_required
def generate_qr(current_user, role):
    """
    Teacher generates a QR code for an attendance session.
    Body: { subject_id, latitude, longitude }
    Returns: { message, session, qr_image (base64 PNG), expires_in_seconds }
    """
    if role != 'teacher':
        return jsonify({'error': 'Only teachers can generate QR'}), 403

    data = request.get_json()
    subject_id = data.get('subject_id') if data else None
    if not subject_id:
        return jsonify({'error': 'subject_id is required'}), 400

    # Verify the course exists and is assigned to this teacher
    course = Course.query.filter_by(id=subject_id, teacher_id=current_user.id).first()
    if not course:
        return jsonify({'error': 'Subject not found or not assigned to you'}), 404

    lat = data.get('latitude', 0.0)
    lng = data.get('longitude', 0.0)

    # Create session
    qr_token = uuid.uuid4().hex
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=QR_EXPIRY_SECONDS)

    session = AttendanceSession(
        course_id=course.id,
        teacher_id=current_user.id,
        qr_token=qr_token,
        latitude=lat,
        longitude=lng,
        created_at=now,
        expires_at=expires_at
    )
    db.session.add(session)
    db.session.commit()

    # Generate QR image (base64 PNG)
    qr_image_b64 = _generate_qr_image(qr_token)

    return jsonify({
        'message': f'QR generated for {course.name}',
        'session': session.to_dict(),
        'qr_image': qr_image_b64,
        'expires_in_seconds': QR_EXPIRY_SECONDS
    })


@mobile_bp.route('/api/attendance/teacher/sessions', methods=['GET'])
@mobile_token_required
def teacher_sessions(current_user, role):
    """Teacher's generated attendance sessions."""
    if role != 'teacher':
        return jsonify({'error': 'Only teachers can view sessions'}), 403

    sessions = AttendanceSession.query.filter_by(teacher_id=current_user.id) \
        .order_by(AttendanceSession.created_at.desc()).all()

    return jsonify({'sessions': [s.to_dict() for s in sessions]})


@mobile_bp.route('/api/attendance/session/<int:session_id>', methods=['GET'])
@mobile_token_required
def session_detail(current_user, role, session_id):
    """Session detail with attendance records."""
    session = AttendanceSession.query.get_or_404(session_id)

    # Only the session's teacher or a student who attended can view
    if role == 'teacher' and session.teacher_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    records = Attendance.query.filter_by(session_id=session.id).all()

    return jsonify({
        'session': session.to_dict(),
        'records': [r.to_dict() for r in records]
    })


@mobile_bp.route('/api/attendance/teacher/subjects', methods=['GET'])
@mobile_token_required
def teacher_subjects(current_user, role):
    """Return courses assigned to the logged-in teacher."""
    if role != 'teacher':
        return jsonify({'error': 'Only teachers can view their subjects'}), 403

    courses = Course.query.filter_by(teacher_id=current_user.id).all()
    subjects = [{
        'subject_id': c.id,
        'subject_name': c.name,
        'code': c.code,
        'teacher_id': c.teacher_id
    } for c in courses]

    return jsonify({'subjects': subjects})


# ═══════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════

def _haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two GPS coordinates."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlam = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _generate_qr_image(data_string):
    """Generate a QR code as base64-encoded PNG using qrcode library.
       Falls back to a placeholder if qrcode is not installed."""
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=10, border=4,
                            error_correction=qrcode.constants.ERROR_CORRECT_H)
        qr.add_data(data_string)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except ImportError:
        # Fallback: Return the token as a simple text placeholder
        # In production, install qrcode: pip install qrcode[pil]
        return base64.b64encode(data_string.encode('utf-8')).decode('utf-8')
