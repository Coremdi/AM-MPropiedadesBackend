from flask import Blueprint, request, jsonify, current_app
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

create_property_bp = Blueprint('create_admin_properties', __name__)

@create_property_bp.route('/admin/createproperty', methods=['POST'])
def create_property():
    try:
        images = request.files.getlist("images")
        if len(images) > 10:
            return jsonify({"error": "You can upload a maximum of 10 images."}), 400
        if len(images) == 0:
            return jsonify({"error": "At least one image is required."}), 400

        # Extract form fields
        title = request.form.get("title")
        location = request.form.get("location")
        price = int(request.form.get("price", 0))
        bedrooms = int(request.form.get("bedrooms", 0))
        bathrooms = int(request.form.get("bathrooms", 0))
        superficie = int(request.form.get("superficie", 0))
        operation = request.form.get("operation")
        type_ = request.form.get("type")
        description = request.form.get("description")
        status = request.form.get("status")
        amenities = request.form.get("amenities")
        listed_date = last_updated = datetime.now()

        # ✅ Use the pool connection safely
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Insert property
                insert_query = """
                    INSERT INTO properties (
                        title, location, price, bedrooms, bathrooms, superficie,
                        operation, type, description, url, listed_date, last_updated, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, '', %s, %s, %s)
                    RETURNING id;
                """
                cur.execute(insert_query, (
                    title, location, price, bedrooms, bathrooms, superficie,
                    operation, type_, description, listed_date, last_updated, status
                ))
                property_id = cur.fetchone()[0]

                # Insert price history
                cur.execute(
                    "INSERT INTO price_history (property_id, last_updated, price) VALUES (%s, %s, %s)",
                    (property_id, last_updated, price)
                )

                # Insert amenities
                if amenities:
                    for amenity in [a.strip() for a in amenities.split(",") if a.strip()]:
                        cur.execute(
                            "INSERT INTO amenities (property_id, name, last_updated) VALUES (%s, %s, %s)",
                            (property_id, amenity, last_updated)
                        )

                # Insert contact
                cur.execute(
                    "INSERT INTO contacts (property_id, whatsapp, email) VALUES (%s, %s, %s)",
                    (property_id, "+5492616086463", "amympropiedades@gmail.com")
                )

                # Commit the inserts before handling images (to avoid lock if upload is slow)
                conn.commit()

        # ✅ Upload images outside the DB transaction
        image_urls = []
        for img in images:
            filename = f"{property_id}_{img.filename}"

            try:
                if SUPABASE_ENABLED:
                    response = supabase.storage.from_(SUPABASE_BUCKET).upload(
                        filename, img.stream.read(), {"content-type": img.content_type}
                    )
                    if hasattr(response, "error") and response.error is not None:
                        print(f"⚠️ Supabase upload failed for {filename}: {response.error}")
                        continue
                    image_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename}"
                    print(f"🖼️ Uploaded to Supabase: {image_url}")
                else:
                    os.makedirs("./static/images", exist_ok=True)
                    save_path = os.path.join("static", "images", filename)
                    img.save(save_path)
                    image_url = f"/static/images/{filename}"
                    print(f"🖼️ Saved locally: {save_path}")

                image_urls.append(image_url)

                # ✅ Insert each image in a new lightweight connection
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO images (property_id, url, last_updated) VALUES (%s, %s, %s)",
                            (property_id, image_url, last_updated)
                        )
                        conn.commit()

            except Exception as upload_error:
                print(f"❌ Error uploading image {filename}: {upload_error}")

        # ✅ Update preview image (again with short pooled connection)
        if image_urls:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE properties SET url = %s WHERE id = %s", (image_urls[0], property_id))
                    conn.commit()

        return jsonify({"message": "Property created", "id": property_id, "images": image_urls}), 201

    except Exception as e:
        current_app.logger.error(f"❌ Error creating property: {e}")
        return jsonify({"error": f"Error creating property: {str(e)}"}), 500
