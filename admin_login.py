from flask import Blueprint, request, jsonify,session
from flask_bcrypt import Bcrypt
from db import get_db_connection


admin_bp = Blueprint('admin', __name__)
bcrypt = Bcrypt()

@admin_bp.route('/admin/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT password FROM admins WHERE username = %s", (username,))
    row = cur.fetchone()

    cur.close()
    conn.close()
    
    
    print(f"Login attempt for: {username}")
    if row:
        print(f"Stored hash: {row[0]}")
        print(f"Password match: {bcrypt.check_password_hash(row[0], password)}")
    if row and bcrypt.check_password_hash(row[0], password):
        session['is_admin'] = True
        session['username'] = username
        return jsonify({"message": "Login successful"}), 200
    else:
        return jsonify({"message": "Invalid credentials"}), 401

@admin_bp.route('/admin/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


@admin_bp.route('/admin/status', methods=['GET'])
def admin_status():
    is_admin = session.get('is_admin', False)
    return jsonify({"is_admin": is_admin}), 200