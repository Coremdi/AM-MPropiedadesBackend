from flask import Blueprint, request, jsonify
from db import get_db_connection
from datetime import datetime
import os

# Supabase setup if deployed
SUPABASE_ENABLED = os.getenv("RENDER_DEPLOYMENT", "false").lower() == "true"
if SUPABASE_ENABLED:
    from supabase import create_client
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    SUPABASE_BUCKET = "images"

upload_images_bp = Blueprint('upload_images', __name__)

@upload_images_bp.route('/admin/upload-images/<int:property_id>', methods=['POST'])
def upload_images(property_id):
    images = request.files.getlist("images")
    if not images:
        return jsonify({"error": "No images provided"}), 400

    image_urls = []
    last_updated = datetime.now()

    try:
        with get_db_connection() as conn, conn.cursor() as cur:
            for img in images:
                filename = f"{property_id}_{img.filename}"

                if SUPABASE_ENABLED:
                    try:
                        response = supabase.storage.from_(SUPABASE_BUCKET).upload(
                            filename, img.stream.read(), {"content-type": img.content_type}
                        )
                        if hasattr(response, "error") and response.error is not None:
                            print(f"⚠️ Supabase upload failed for {filename}: {response.error}")
                            continue

                        image_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename}"

                    except Exception as upload_error:
                        print(f"❌ Error uploading {filename} to Supabase: {upload_error}")
                        continue

                else:
                    # Save locally
                    os.makedirs("./static/images", exist_ok=True)
                    save_path = os.path.join("static", "images", filename)
                    img.save(save_path)
                    image_url = f"/static/images/{filename}"
                    print(f"🖼️ Saved image locally: {save_path}")

                # Insert into DB
                try:
                    cur.execute(
                        "INSERT INTO images (property_id, url, last_updated) VALUES (%s, %s, %s)",
                        (property_id, image_url, last_updated)
                    )
                    image_urls.append(image_url)
                    print(f"🖼️ Image record added to DB: {image_url}")
                except Exception as db_err:
                    print(f"❌ Failed to insert {filename} into DB: {db_err}")

            conn.commit()

        return jsonify({"message": "Images uploaded successfully", "images": image_urls}), 200

    except Exception as e:
        print("❌ Upload error:", e)
        return jsonify({"error": str(e)}), 500


