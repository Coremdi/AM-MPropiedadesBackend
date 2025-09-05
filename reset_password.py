import hashlib, secrets
from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
from db import get_db_connection
from flask_mail import Mail, Message
import os

SUPABASE_ENABLED = os.getenv("RENDER_DEPLOYMENT", "false").lower() == "true"
if SUPABASE_ENABLED:
    from supabase import create_client
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    SUPABASE_TABLE = "admins"  # table name in Supabase

resetpassword_bp = Blueprint('resetPassword', __name__)
bcrypt = Bcrypt()
mail = Mail()

# ---- Forgot Password Route ----
@resetpassword_bp.route('/admin/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    username = data.get('username')

    if not username:
        return jsonify({"message": "Username required"}), 400

    raw_token = secrets.token_urlsafe(32)
    hashed_token = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now() + timedelta(hours=1)

    try:
        if SUPABASE_ENABLED:
            # Check user in Supabase
            user_res = supabase.table(SUPABASE_TABLE).select("username").eq("username", username).execute()
            if not user_res.data or len(user_res.data) == 0:
                return jsonify({"message": "User not found"}), 404

            # Insert reset token in Supabase
            supabase.table("password_resets").insert({
                "username": username,
                "token": hashed_token,
                "expires_at": expires_at.isoformat(),
                "used": False
            }).execute()
        else:
            # Postgres workflow
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT username FROM admins WHERE username = %s", (username,))
            user = cur.fetchone()
            if not user:
                cur.close()
                conn.close()
                return jsonify({"message": "User not found"}), 404

            cur.execute("""
                INSERT INTO password_resets (username, token, expires_at, used)
                VALUES (%s, %s, %s, FALSE)
            """, (username, hashed_token, expires_at))
            conn.commit()
            cur.close()
            conn.close()

        # Send email
        FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
        reset_link = f"{FRONTEND_URL}/admin/reset-password?token={raw_token}"

        msg = Message(
            "Password Reset Request",
            sender="yourapp@example.com",
            recipients=[username]  # username is email
        )
        msg.body = f"Click the link to reset your password: {reset_link}"
        mail.send(msg)

        return jsonify({"message": "Password reset link sent"}), 200

    except Exception as e:
        print("❌ Error in forgot password:", e)
        return jsonify({"error": str(e)}), 500


# ---- Reset Password Route ----
@resetpassword_bp.route('/admin/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    raw_token = data.get('token')
    new_password = data.get('new_password')

    if not raw_token or not new_password:
        return jsonify({"message": "Missing data"}), 400

    hashed_token = hashlib.sha256(raw_token.encode()).hexdigest()
    bcrypt_password = bcrypt.generate_password_hash(new_password).decode('utf-8')

    try:
        if SUPABASE_ENABLED:
            # Get token info from Supabase
            token_res = supabase.table("password_resets").select("*").eq("token", hashed_token).execute()
            if not token_res.data or token_res.data[0]["used"] or datetime.fromisoformat(token_res.data[0]["expires_at"]) < datetime.now():
                return jsonify({"message": "Invalid or expired token"}), 400

            username = token_res.data[0]["username"]

            # Update password in Supabase
            supabase.table(SUPABASE_TABLE).update({"password": bcrypt_password}).eq("username", username).execute()

            # Mark token as used
            supabase.table("password_resets").update({"used": True}).eq("token", hashed_token).execute()

        else:
            # Postgres workflow
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT username, expires_at, used FROM password_resets WHERE token = %s", (hashed_token,))
            row = cur.fetchone()
            if not row or row[2] or row[1] < datetime.now():
                cur.close()
                conn.close()
                return jsonify({"message": "Invalid or expired token"}), 400

            cur.execute("UPDATE admins SET password = %s WHERE username = %s", (bcrypt_password, row[0]))
            cur.execute("UPDATE password_resets SET used = TRUE WHERE token = %s", (hashed_token,))
            conn.commit()
            cur.close()
            conn.close()

        return jsonify({"message": "Password reset successful"}), 200

    except Exception as e:
        print("❌ Error resetting password:", e)
        return jsonify({"error": str(e)}), 500
