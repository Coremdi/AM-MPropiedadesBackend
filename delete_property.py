from flask import Blueprint, request, jsonify, current_app
from db import get_db_connection
import os

# --- Supabase setup ---
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

        # --- 1️⃣ Obtener las imágenes antes de eliminar ---
        image_rows = []
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT url FROM images WHERE property_id = %s", (property_id,))
                image_rows = cur.fetchall()

        # --- 2️⃣ Borrar los archivos físicamente (locales o en Supabase) ---
        for (url,) in image_rows:
            try:
                if SUPABASE_ENABLED:
                    filename = url.split("/")[-1]
                    res = supabase.storage.from_(SUPABASE_BUCKET).remove([filename])
                    if hasattr(res, "error") and res.error is not None:
                        current_app.logger.warning(f"⚠️ Supabase delete failed for {filename}: {res.error}")
                    else:
                        current_app.logger.info(f"🧹 Deleted from Supabase: {filename}")

                elif url.startswith("/static/images/"):
                    image_path = os.path.join(".", url.lstrip("/"))
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        current_app.logger.info(f"🧹 Deleted local file: {image_path}")
                    else:
                        current_app.logger.warning(f"⚠️ File not found: {image_path}")

            except Exception as supa_err:
                current_app.logger.error(f"❌ Error deleting file {url}: {supa_err}")
                continue

        # --- 3️⃣ Borrar registros en la base (orden correcto: hijos → padre) ---
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM images WHERE property_id = %s", (property_id,))
                cur.execute("DELETE FROM amenities WHERE property_id = %s", (property_id,))
                cur.execute("DELETE FROM contacts WHERE property_id = %s", (property_id,))
                cur.execute("DELETE FROM price_history WHERE property_id = %s", (property_id,))
                cur.execute("DELETE FROM properties WHERE id = %s", (property_id,))
                conn.commit()

        current_app.logger.info(f"✅ Property {property_id} and related data deleted successfully")
        return jsonify({"message": f"Property {property_id} deleted successfully"}), 200

    except Exception as e:
        current_app.logger.error(f"❌ Error deleting property {property_id}: {e}")
        return jsonify({"error": f"Failed to delete property: {str(e)}"}), 500



