from flask import Blueprint, request, jsonify
from models import db, Department
from routes.auth import token_required

departments_bp = Blueprint('departments', __name__)

# ── List all departments ─────────────────────────────
@departments_bp.route('/api/departments', methods=['GET'])
@token_required
def get_departments(current_admin):
    depts = Department.query.order_by(Department.name).all()
    return jsonify([d.to_dict() for d in depts])

# ── Create department ────────────────────────────────
@departments_bp.route('/api/departments', methods=['POST'])
@token_required
def create_department(current_admin):
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'Department name is required'}), 400

    name = data['name'].strip()
    if Department.query.filter_by(name=name).first():
        return jsonify({'error': 'Department already exists'}), 409

    dept = Department(name=name)
    db.session.add(dept)
    db.session.commit()
    return jsonify(dept.to_dict()), 201

# ── Update department ────────────────────────────────
@departments_bp.route('/api/departments/<int:dept_id>', methods=['PUT'])
@token_required
def update_department(current_admin, dept_id):
    data = request.get_json()
    dept = Department.query.get_or_404(dept_id)

    if data.get('name'):
        new_name = data['name'].strip()
        existing = Department.query.filter(
            Department.name == new_name, Department.id != dept_id
        ).first()
        if existing:
            return jsonify({'error': 'Department name already exists'}), 409
        dept.name = new_name

    db.session.commit()
    return jsonify(dept.to_dict())

# ── Delete department ────────────────────────────────
@departments_bp.route('/api/departments/<int:dept_id>', methods=['DELETE'])
@token_required
def delete_department(current_admin, dept_id):
    dept = Department.query.get_or_404(dept_id)
    db.session.delete(dept)
    db.session.commit()
    return jsonify({'message': 'Department deleted'})
