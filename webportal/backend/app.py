import os, sys
from flask import Flask, send_from_directory, request
from flask_cors import CORS
from werkzeug.security import generate_password_hash
from config import Config
from models import db, Admin, Department

def create_app():
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)
    CORS(app)
    db.init_app(app)

    # Register blueprints
    from routes.auth        import auth_bp
    from routes.users       import users_bp
    from routes.courses     import courses_bp
    from routes.attendance  import attendance_bp
    from routes.reports     import reports_bp
    from routes.departments import departments_bp
    from routes.mobile      import mobile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(departments_bp)
    app.register_blueprint(mobile_bp)

    # Serve frontend static files
    frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')

    @app.route('/')
    def serve_index():
        return send_from_directory(frontend_dir, 'login.html')

    @app.route('/<path:path>')
    def serve_static(path):
        # Don't serve static files for API routes
        if path.startswith('api/'):
            return {'error': 'Not found'}, 404
        return send_from_directory(frontend_dir, path)

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return {'error': 'Not found'}, 404
        return send_from_directory(frontend_dir, 'login.html')

    # Create tables & seed admin on first run
    with app.app_context():
        db.create_all()
        if not Admin.query.filter_by(email='admin@admin.com').first():
            admin = Admin(
                name='Administrator',
                email='admin@admin.com',
                password=generate_password_hash('admin123')
            )
            db.session.add(admin)
            db.session.commit()
           

        # Seed default departments
        default_depts = ['Computer Science', 'Electronics', 'Mechanical', 'Civil']
        for dept_name in default_depts:
            if not Department.query.filter_by(name=dept_name).first():
                db.session.add(Department(name=dept_name))
        db.session.commit()
        print('[OK] Default departments seeded')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
