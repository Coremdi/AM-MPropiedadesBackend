from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from db import get_db_connection

create_user_bp = Blueprint('create_user', __name__)
bcrypt = Bcrypt()

@create_user_bp.route('/admin/create-user', methods=['POST'])
def create_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400

    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO admins (username, password) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (username, hashed_pw)
        )
        conn.commit()
    except Exception as e:
        return jsonify({"message": "Error creating user", "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify({"message": f"User {username} created successfully"}), 201
