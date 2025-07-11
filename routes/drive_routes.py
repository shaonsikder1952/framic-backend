from flask import Blueprint, request, jsonify
from services.backblaze_service import upload_file_to_b2
import os  # ✅ Needed to delete temp file later

drive_bp = Blueprint("drive", __name__)

@drive_bp.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    file_path = f"/tmp/{file.filename}"
    file.save(file_path)

    try:
        result = upload_file_to_b2(file_path, file.filename)
        return jsonify({"result": result})
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)  # ✅ Clean up temp file
