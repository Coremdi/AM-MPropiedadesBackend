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

bulk_delete_images_bp = Blueprint("bulk_delete_images", __name__)

@bulk_delete_images_bp.route("/admin/delete-images/<int:property_id>", methods=["POST"])
def delete_images(property_id):
    try:
        data = request.get_json()
        image_urls = data.get("images", [])
        if not image_urls:
            return jsonify({"error": "No images provided"}), 400

        deleted_files = []

        for url in image_urls:
            # --- 1️⃣ Delete image file (local or Supabase) ---
            try:
                if SUPABASE_ENABLED:
                    filename = url.split("/")[-1]
                    res = supabase.storage.from_(SUPABASE_BUCKET).remove([filename])

                    if hasattr(res, "error") and res.error is not None:
                        current_app.logger.warning(f"⚠️ Supabase delete failed for {filename}: {res.error}")
                        continue

                    deleted_files.append(url)
                    current_app.logger.info(f"🧹 Deleted from Supabase: {filename}")

                elif url.startswith("/static/images/"):
                    image_path = os.path.join(".", url.lstrip("/"))
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        deleted_files.append(url)
                        current_app.logger.info(f"🧹 Deleted local file: {image_path}")
                    else:
                        current_app.logger.warning(f"⚠️ File not found: {image_path}")

            except Exception as file_err:
                current_app.logger.error(f"❌ Error deleting file {url}: {file_err}")
                continue  # proceed to next image even if one fails

            # --- 2️⃣ Delete record from database ---
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "DELETE FROM images WHERE property_id = %s AND url = %s",
                            (property_id, url)
                        )
                        conn.commit()
                        current_app.logger.info(f"🗑️ Removed DB record for {url}")
            except Exception as db_err:
                current_app.logger.error(f"❌ Error deleting DB record for {url}: {db_err}")

        return jsonify({
            "message": "Images deleted",
            "count": len(deleted_files),
            "deleted_files": deleted_files
        }), 200

    except Exception as e:
        current_app.logger.error(f"❌ Error deleting images: {e}")
        return jsonify({"error": f"Failed to delete images: {str(e)}"}), 500
