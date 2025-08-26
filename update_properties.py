from flask import Blueprint, request, jsonify, current_app
from db import get_db_connection
from datetime import datetime, timezone

#seguir con la parte del update del price history table

admin_property_bp = Blueprint('admin_properties', __name__)

@admin_property_bp.route("/admin/properties/<int:property_id>", methods=["PATCH"])
def update_property(property_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    allowed_fields = {
        "title", "location", "price", "bedrooms", "bathrooms",
        "superficie", "type", "description", "operation", "status",
    }

    update_fields = {k: v for k, v in data.items() if k in allowed_fields}

    if not update_fields and "amenities" not in data:
        return jsonify({"error": "No valid fields to update"}), 400

    update_fields["last_updated"] = datetime.now(timezone.utc)

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # --- Check if price changed ---
                price_changed = False
                new_price = data.get("price")
                if new_price is not None:
                    cur.execute("SELECT price FROM properties WHERE id = %s", (property_id,))
                    result = cur.fetchone()
                    if result:
                        current_price = result[0]
                        if current_price != new_price:
                            price_changed = True

                # --- Update property ---
                if update_fields:
                    set_clause = ", ".join([f"{key} = %s" for key in update_fields])
                    values = list(update_fields.values())
                    query = f"UPDATE properties SET {set_clause} WHERE id = %s"
                    values.append(property_id)
                    cur.execute(query, values)

                # --- Insert new price history if price changed ---
                if price_changed:
                    now = datetime.now(timezone.utc)
                    cur.execute(
                        "INSERT INTO price_history (property_id, price, last_updated) VALUES (%s, %s, %s)",
                        (property_id, new_price, now)
                    )

                # --- Update amenities if present ---
                if "amenities" in data and isinstance(data["amenities"], list):
                    cur.execute("DELETE FROM amenities WHERE property_id = %s", (property_id,))
                    now = datetime.now(timezone.utc)
                    for amenity in data["amenities"]:
                        cur.execute(
                            "INSERT INTO amenities (property_id, name, last_updated) VALUES (%s, %s, %s)",
                            (property_id, amenity.strip(), now)
                        )

                conn.commit()

        return jsonify({"message": "Property updated successfully"}), 200

    except Exception as e:
        current_app.logger.error(f"Error updating property {property_id}: {e}")
        return jsonify({"error": "Database update failed"}), 500