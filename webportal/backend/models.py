from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ── Admin ────────────────────────────────────────────
class Admin(db.Model):
    __tablename__ = 'admins'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(150), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'email': self.email,
                'created_at': self.created_at.isoformat()}

# ── Department ───────────────────────────────────────
class Department(db.Model):
    __tablename__ = 'departments'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'name': self.name}

# ── Student ──────────────────────────────────────────
class Student(db.Model):
    __tablename__ = 'students'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False)
    password      = db.Column(db.String(255), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    roll_number   = db.Column(db.String(50), unique=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    department = db.relationship('Department', backref='students', lazy=True)

    def to_dict(self):
        return {
            'id': self.id, 'user_id': self.id,
            'name': self.name, 'email': self.email,
            'role': 'Student',
            'department': self.department.name if self.department else None,
            'department_id': self.department_id,
            'roll_number': self.roll_number,
            'created_at': self.created_at.isoformat()
        }

# ── Teacher ──────────────────────────────────────────
class Teacher(db.Model):
    __tablename__ = 'teachers'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False)
    password      = db.Column(db.String(255), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    department = db.relationship('Department', backref='teachers', lazy=True)

    def to_dict(self):
        return {
            'id': self.id, 'user_id': self.id,
            'name': self.name, 'email': self.email,
            'role': 'Teacher',
            'department': self.department.name if self.department else None,
            'department_id': self.department_id,
            'created_at': self.created_at.isoformat()
        }

# ── Course ───────────────────────────────────────────
class Course(db.Model):
    __tablename__ = 'courses'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(150), nullable=False)
    code          = db.Column(db.String(20), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    teacher_id    = db.Column(db.Integer, db.ForeignKey('teachers.id'))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    department = db.relationship('Department', backref='courses', lazy=True)
    teacher    = db.relationship('Teacher',    backref='courses', lazy=True)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'code': self.code,
            'department': self.department.name if self.department else None,
            'department_id': self.department_id,
            'teacher_id': self.teacher_id,
            'teacher': self.teacher.name if self.teacher else None,
            'created_at': self.created_at.isoformat()
        }

# ── Timetable ────────────────────────────────────────
class Timetable(db.Model):
    __tablename__ = 'timetable'
    id          = db.Column(db.Integer, primary_key=True)
    course_id   = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    day_of_week = db.Column(db.String(10), nullable=False)
    start_time  = db.Column(db.Time, nullable=False)
    end_time    = db.Column(db.Time, nullable=False)
    room        = db.Column(db.String(50))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship('Course', backref='timetable_entries', lazy=True)

    def to_dict(self):
        return {
            'id': self.id, 'course_id': self.course_id,
            'course': self.course.name if self.course else None,
            'course_code': self.course.code if self.course else None,
            'day_of_week': self.day_of_week,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'room': self.room
        }

# ── Attendance (existing admin portal records) ───────
class Attendance(db.Model):
    __tablename__ = 'attendance'
    id         = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    course_id  = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    date       = db.Column(db.Date, nullable=False)
    status     = db.Column(db.String(10), default='Present')
    latitude   = db.Column(db.Numeric(10,8))
    longitude  = db.Column(db.Numeric(11,8))
    marked_at  = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=True)

    student = db.relationship('Student', backref='attendance_records', lazy=True)
    course  = db.relationship('Course',  backref='attendance_records', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'course_id', 'date', name='unique_attendance'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'record_id': self.id,
            'student_id': self.student_id,
            'student': self.student.name if self.student else None,
            'student_name': self.student.name if self.student else None,
            'course_id': self.course_id,
            'course': self.course.name if self.course else None,
            'subject_name': self.course.name if self.course else None,
            'session_id': self.session_id,
            'date': self.date.isoformat(),
            'status': self.status,
            'timestamp': self.marked_at.isoformat() if self.marked_at else None,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'marked_at': self.marked_at.isoformat() if self.marked_at else None
        }

# ── AttendanceSession (QR-based sessions for mobile) ─
class AttendanceSession(db.Model):
    __tablename__ = 'attendance_sessions'
    id          = db.Column(db.Integer, primary_key=True)
    course_id   = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    teacher_id  = db.Column(db.Integer, db.ForeignKey('teachers.id', ondelete='CASCADE'), nullable=False)
    qr_token    = db.Column(db.String(255), unique=True, nullable=False)
    latitude    = db.Column(db.Numeric(10,8))
    longitude   = db.Column(db.Numeric(11,8))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at  = db.Column(db.DateTime, nullable=False)

    course  = db.relationship('Course',  backref='sessions', lazy=True)
    teacher = db.relationship('Teacher', backref='sessions', lazy=True)
    records = db.relationship('Attendance', backref='session', lazy=True,
                              foreign_keys='Attendance.session_id')

    def to_dict(self):
        now = datetime.utcnow()
        return {
            'session_id': self.id,
            'subject_id': self.course_id,
            'subject_name': self.course.name if self.course else None,
            'teacher_id': self.teacher_id,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expiry_time': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': now > self.expires_at if self.expires_at else True,
            'attendance_count': len(self.records) if self.records else 0
        }
