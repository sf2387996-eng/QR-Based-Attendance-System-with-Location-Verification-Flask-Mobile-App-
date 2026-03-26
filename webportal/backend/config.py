import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'qr-attendance-secret-key-change-in-production')

    # For MySQL: set DATABASE_URL env var, e.g.
    #   mysql+pymysql://root:password@localhost/qr_attendance
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qr_attendance.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_EXPIRATION_HOURS = 24
