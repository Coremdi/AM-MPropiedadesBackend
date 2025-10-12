from flask import Blueprint, request, jsonify, session, current_app
from flask_bcrypt import Bcrypt
from db import get_db_connection

admin_bp = Blueprint('admin', __name__)
bcrypt = Bcrypt()

@admin_bp.route('/admin/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"message": "Username and password are required"}), 400

        # ✅ Use the connection pool safely
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT password FROM admins WHERE username = %s", (username,))
                row = cur.fetchone()

        print(f"🔐 Login attempt for: {username}")

        if row:
            print(f"Stored hash: {row[0]}")
            password_match = bcrypt.check_password_hash(row[0], password)
            print(f"Password match: {password_match}")
        else:
            print("⚠️ User not found in admins table.")
            return jsonify({"message": "Invalid credentials"}), 401

        if password_match:
            session['is_admin'] = True
            session['username'] = username
            return jsonify({"message": "Login successful"}), 200
        else:
            return jsonify({"message": "Invalid credentials"}), 401

    except Exception as e:
        current_app.logger.error(f"❌ Error during login: {e}")
        return jsonify({"message": "Internal server error"}), 500


@admin_bp.route('/admin/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


@admin_bp.route('/admin/status', methods=['GET'])
def admin_status():
    is_admin = session.get('is_admin', False)
    return jsonify({"is_admin": is_admin}), 200
