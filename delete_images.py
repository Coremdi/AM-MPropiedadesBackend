from flask import Blueprint, request, jsonify
from db import get_db_connection
import os
import os.path

# Only import Supabase if we are in deployment
SUPABASE_ENABLED = os.getenv("RENDER_DEPLOYMENT", "false").lower() == "true"
if SUPABASE_ENABLED:
    from supabase import create_client
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    SUPABASE_BUCKET = "images"  # You can change bucket name if needed

bulk_delete_images_bp = Blueprint("bulk_delete_images", __name__)

@bulk_delete_images_bp.route("/admin/delete-images/<int:property_id>", methods=["POST"])
def delete_images(property_id):
    try:
        data = request.get_json()
        image_urls = data.get("images", [])
        if not image_urls:
            return jsonify({"error": "No images provided"}), 400

        conn = get_db_connection()
        cur = conn.cursor()
        deleted_files = []

        for url in image_urls:
            # --- Local deletion ---
            if not SUPABASE_ENABLED and url.startswith("/static/images/"):
                image_path = os.path.join(".", url.lstrip("/"))
                if os.path.exists(image_path):
                    os.remove(image_path)
                    deleted_files.append(url)
                    print(f"🧹 Deleted file: {image_path}")
                else:
                    print(f"⚠️ File not found: {image_path}")

            # --- Supabase deletion ---
            if SUPABASE_ENABLED:
                filename = url.split("/")[-1]  # get the filename from the URL
                try:                    
                    res = supabase.storage.from_(SUPABASE_BUCKET).remove([filename])
                    if hasattr(res, "error") and res.error is not None:
                        print(f"⚠️ Supabase delete failed for {filename}: {res.error}")
                    else:
                        deleted_files.append(url)
                        print(f"🧹 Deleted from Supabase: {filename}")
                except Exception as supa_err:
                    print(f"❌ Error deleting {filename} from Supabase: {supa_err}")

            # --- Delete record from DB ---
            cur.execute(
                "DELETE FROM images WHERE property_id = %s AND url = %s",
                (property_id, url)
            )

        conn.commit()
        print(f"✅ Deleted {len(deleted_files)} images from property {property_id}")
        return jsonify({"message": "Images deleted", "count": len(deleted_files)}), 200

    except Exception as e:
        print("❌ Error deleting images:", e)
        return jsonify({"error": f"Failed to delete images: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


