from flask import Blueprint, request, jsonify
from services.backblaze_service import upload_file_to_b2
import os  # ✅ Needed to delete temp file later

drive_bp = Blueprint("drive", __name__)

@drive_bp.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("file")

    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    results = []
    for file in files:
        file_path = f"/tmp/{file.filename}"
        file.save(file_path)
        result = upload_file_to_b2(file_path, file.filename)
        results.append({"filename": file.filename, "result": result})

    return jsonify(results)
