import hashlib, datetime, secrets
from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
from db import get_db_connection
from flask_mail import Mail, Message
import os


resetpassword_bp = Blueprint('resetPassword', __name__)
bcrypt = Bcrypt()

# configure mail (put in app.py ideally)
mail = Mail()

# ---- Forgot Password Route ----
@resetpassword_bp.route('/admin/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    username = data.get('username')

    if not username:
        return jsonify({"message": "Username required"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT username FROM admins WHERE username = %s", (username,))
    user = cur.fetchone()

    if not user:
        cur.close()
        conn.close()
        return jsonify({"message": "User not found"}), 404

    raw_token = secrets.token_urlsafe(32)
    hashed_token = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now() + timedelta(hours=1)

    cur.execute("""
        INSERT INTO password_resets (username, token, expires_at)
        VALUES (%s, %s, %s)
    """, (username, hashed_token, expires_at))
    conn.commit()
    cur.close()
    conn.close()

    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
    reset_link = f"{FRONTEND_URL}/admin/reset-password?token={raw_token}"

    try:
        msg = Message("Password Reset Request",
                      sender="yourapp@example.com",
                      recipients=[f"pablocort94@hotmail.com"])
        msg.body = f"Click the link to reset your password: {reset_link}"
        mail.send(msg)
    except Exception as e:
        print("Email sending failed:", e)

    return jsonify({"message": "Password reset link sent"}), 200


# ---- Reset Password Route ----
@resetpassword_bp.route('/admin/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    raw_token = data.get('token')
    new_password = data.get('new_password')

    if not raw_token or not new_password:
        return jsonify({"message": "Missing data"}), 400

    hashed_token = hashlib.sha256(raw_token.encode()).hexdigest()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, expires_at, used FROM password_resets WHERE token = %s", (hashed_token,))
    row = cur.fetchone()

    if not row or row[2] or row[1] < datetime.now():
        cur.close()
        conn.close()
        return jsonify({"message": "Invalid or expired token"}), 400

    bcrypt_password = bcrypt.generate_password_hash(new_password).decode('utf-8')

    cur.execute("UPDATE admins SET password = %s WHERE username = %s",
                (bcrypt_password, row[0]))
    cur.execute("UPDATE password_resets SET used = TRUE WHERE token = %s", (hashed_token,))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Password reset successful"}), 200
