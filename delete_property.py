from flask import Blueprint, request, jsonify
from db import get_db_connection
import os

# Supabase setup if deployed
SUPABASE_ENABLED = os.getenv("RENDER_DEPLOYMENT", "false").lower() == "true"
if SUPABASE_ENABLED:
    from supabase import create_client
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    SUPABASE_BUCKET = "images"

delete_property_bp = Blueprint("delete_property", __name__)

@delete_property_bp.route("/admin/deleteproperty", methods=["POST"])
def delete_property():
    try:
        property_id = request.args.get("id", type=int)
        if not property_id:
            return jsonify({"error": "Missing property ID"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        # 🖼 Fetch image file paths before deleting
        cur.execute("SELECT url FROM images WHERE property_id = %s", (property_id,))
        image_rows = cur.fetchall()

        for (url,) in image_rows:
            # --- Local deletion ---
            if not SUPABASE_ENABLED and url.startswith("/static/images/"):
                image_path = os.path.join(".", url.lstrip("/"))
                if os.path.exists(image_path):
                    os.remove(image_path)
                    print(f"🧹 Deleted file: {image_path}")
                else:
                    print(f"⚠️ File not found: {image_path}")

            # --- Supabase deletion ---
            if SUPABASE_ENABLED:
                filename = url.split("/")[-1]
                res = supabase.storage.from_bucket(SUPABASE_BUCKET).remove([filename])
                if res.get("error"):
                    print(f"⚠️ Supabase delete failed for {filename}: {res['error']}")
                else:
                    print(f"🧹 Deleted from Supabase: {filename}")

        # ❌ Delete from DB (children → parent order)
        cur.execute("DELETE FROM images WHERE property_id = %s", (property_id,))
        cur.execute("DELETE FROM amenities WHERE property_id = %s", (property_id,))
        cur.execute("DELETE FROM contacts WHERE property_id = %s", (property_id,))
        cur.execute("DELETE FROM price_history WHERE property_id = %s", (property_id,))
        cur.execute("DELETE FROM properties WHERE id = %s", (property_id,))

        conn.commit()
        print(f"✅ Property {property_id} and associated data deleted successfully")
        return jsonify({"message": f"Property {property_id} deleted successfully"}), 200

    except Exception as e:
        print("❌ Error deleting property:", e)
        return jsonify({"error": f"Failed to delete property: {str(e)}"}), 500


