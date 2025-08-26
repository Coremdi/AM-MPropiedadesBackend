from flask import Blueprint, request, jsonify
from db import get_db_connection
from datetime import datetime, timezone
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

        conn = get_db_connection()
        cur = conn.cursor()
        last_updated = datetime.now()
        listed_date = datetime.now()

        # Extract fields
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
        print(f"✅ Property created with ID: {property_id}")

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
            (property_id, "+5491123456789", "info@realestate.com")
        )

        # Handle images
        image_urls = []
        for img in images:
            filename = f"{property_id}_{img.filename}"

            if SUPABASE_ENABLED:
                # Upload to Supabase
                res = supabase.storage.from_bucket(SUPABASE_BUCKET).upload(
                    filename, img.stream.read(), {"content-type": img.content_type}
                )
                if res.get("error"):
                    print(f"⚠️ Supabase upload failed for {filename}: {res['error']}")
                    continue
                image_url = f"https://{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename}"
                print(f"🖼️ Uploaded to Supabase: {image_url}")
            else:
                # Local save
                os.makedirs("./static/images", exist_ok=True)
                save_path = os.path.join("static", "images", filename)
                img.save(save_path)
                image_url = f"/static/images/{filename}"
                print(f"🖼️ Saved image locally: {save_path}")

            # Insert image record
            cur.execute(
                "INSERT INTO images (property_id, url, last_updated) VALUES (%s, %s, %s)",
                (property_id, image_url, last_updated)
            )
            image_urls.append(image_url)

        # Set preview image
        if image_urls:
            cur.execute("UPDATE properties SET url = %s WHERE id = %s", (image_urls[0], property_id))

        conn.commit()
        return jsonify({"message": "Property created", "id": property_id, "images": image_urls}), 201

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"error": f"Error creating property: {str(e)}"}), 500

