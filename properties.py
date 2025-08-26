from flask import Blueprint, jsonify, current_app
from db import get_db_connection

properties_bp = Blueprint("properties", __name__)

# Reusable SELECT block (no ORDER BY so WHERE can be appended)
SELECT_JSON_BLOCK = """
SELECT jsonb_build_object(
    'id',         p.id,
    'title',      p.title,
    'location',   p.location,
    'price',      p.price,
    'bedrooms',   p.bedrooms,
    'bathrooms',  p.bathrooms,
    'superficie', p.superficie,
    'operation',  p.operation,
    'type',       p.type,
    'images', (
        SELECT jsonb_agg(i.url) FROM images i WHERE i.property_id = p.id
    ),
    'description', p.description,
    'amenities', (
        SELECT jsonb_agg(a.name) FROM amenities a WHERE a.property_id = p.id
    ),
    'contact', (
        SELECT jsonb_build_object('whatsapp', c.whatsapp, 'email', c.email)
        FROM contacts c WHERE c.property_id = p.id
    ),
    'url',          p.url,
    'listed_date',  p.listed_date,
    'last_updated', p.last_updated,
    'status',       p.status,
    'price_history', (
        SELECT jsonb_agg(
            jsonb_build_object('date', ph.last_updated, 'price', ph.price)
        )
        FROM price_history ph WHERE ph.property_id = p.id
    )
) AS property_json
FROM properties p
"""

def fetch_properties(query, params=None, single=False):
    """Executes a SELECT query and returns JSON objects."""
    try:
        with get_db_connection() as conn, conn.cursor() as cur:
            cur.execute(query, params or ())
            rows = cur.fetchall()
            if single:
                return (rows[0][0] if rows else None), None
            return [r[0] for r in rows], None
    except Exception as e:
        current_app.logger.error(f"Database error: {e}")
        return None, str(e)

# ------------------------- ADMIN ROUTES ----------------------------------

@properties_bp.route("/admin/properties", methods=["GET"])
def list_properties():
    rows, error = fetch_properties(SELECT_JSON_BLOCK + " ORDER BY p.id;")
    if error:
        return jsonify({"error": "Failed to fetch properties"}), 500
    return jsonify(rows), 200

@properties_bp.route("/admin/properties/<int:property_id>", methods=["GET"])
def get_property(property_id):
    row, error = fetch_properties(SELECT_JSON_BLOCK + " WHERE p.id = %s;", (property_id,), single=True)
    if error:
        return jsonify({"error": "Failed to fetch property"}), 500
    if not row:
        return jsonify({"error": "Property not found"}), 404
    return jsonify(row), 200

# ------------------------- PUBLIC ROUTES ---------------------------------

@properties_bp.route("/properties", methods=["GET"])
def public_list_properties():
    rows, error = fetch_properties(SELECT_JSON_BLOCK + " ORDER BY p.id;")
    if error:
        return jsonify({"error": "Failed to fetch properties"}), 500
    return jsonify(rows), 200

@properties_bp.route("/properties/<int:property_id>", methods=["GET"])
def get_public_property(property_id):
    row, error = fetch_properties(SELECT_JSON_BLOCK + " WHERE p.id = %s;", (property_id,), single=True)
    if error:
        return jsonify({"error": "Failed to fetch property"}), 500
    if not row:
        return jsonify({"error": "Property not found"}), 404
    return jsonify(row), 200
