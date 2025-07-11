
from flask import Blueprint, request, jsonify
from services.backblaze_service import (
    upload_file_to_b2,
    list_files_in_b2,
    get_file_download_url,
    delete_file_from_b2,
    rename_file_in_b2,
    move_file_to_folder
)
import os
import logging

drive_bp = Blueprint("drive", __name__)
logging.basicConfig(level=logging.INFO)

@drive_bp.route("/upload", methods=["POST"])
def upload():
    from uuid import uuid4

    files = request.files.getlist("file")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    results = []
    for file in files:
        if file.filename.strip() == "":
            results.append({"filename": None, "result": "❌ Skipped empty filename"})
            continue
        try:
            # ✅ Keep original extension
            original_name = file.filename
            ext = os.path.splitext(original_name)[1]  # e.g., ".jpg"
            unique_name = f"{uuid4().hex}{ext}"       # e.g., "b83ad1d9f3844e1e9a0c.jpg"

            # 🔒 Save to temp path
            temp_path = f"/tmp/{unique_name}"
            file.save(temp_path)

            # ⬆️ Upload to Backblaze
            result = upload_file_to_b2(temp_path, unique_name)

            # 🧹 Clean up
            os.remove(temp_path)

            # ✅ Return uploaded file name
            results.append({
                "original": original_name,
                "filename": unique_name,
                "result": result
            })
            logging.info(f"✅ Uploaded: {unique_name}")

        except Exception as e:
            results.append({
                "filename": file.filename,
                "result": f"❌ Failed: {str(e)}"
            })
            logging.error(f"❌ Upload error: {file.filename} | {e}")

    return jsonify(results)


@drive_bp.route("/files", methods=["GET"])
def list_files():
    try:
        result = list_files_in_b2()
        return jsonify(result)
    except Exception as e:
        logging.error(f"❌ Error listing files: {e}")
        return jsonify({"error": str(e)}), 500

@drive_bp.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    try:
        url = get_file_download_url(filename)
        if isinstance(url, str):
            return jsonify({"download_url": url})
        else:
            return jsonify({"error": url.get("error", "Unknown error")}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@drive_bp.route("/delete/<filename>", methods=["DELETE"])
def delete_file(filename):
    try:
        result = delete_file_from_b2(filename)
        return jsonify({"filename": filename, "result": result})
    except Exception as e:
        return jsonify({"filename": filename, "result": f"❌ Delete failed: {str(e)}"}), 500

@drive_bp.route("/rename", methods=["POST"])
def rename_file():
    data = request.json
    old_name = data.get("old_name")
    new_name = data.get("new_name")
    if not old_name or not new_name:
        return jsonify({"error": "Both old_name and new_name required"}), 400
    try:
        result = rename_file_in_b2(old_name, new_name)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@drive_bp.route("/move", methods=["POST"])
def move_file():
    data = request.json
    filename = data.get("filename")
    target_folder = data.get("target_folder")
    if not filename or not target_folder:
        return jsonify({"error": "filename and target_folder required"}), 400
    try:
        result = move_file_to_folder(filename, target_folder)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
