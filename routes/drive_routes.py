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
from uuid import uuid4

drive_bp = Blueprint("drive", __name__)

# 🚨 Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DriveAPI")

# 📁 Config
TEMP_DIR = "/tmp"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)


# 🚀 Upload Route
@drive_bp.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("file")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    results = []

    for file in files:
        if not file.filename.strip():
            results.append({"filename": None, "result": "❌ Empty filename skipped"})
            continue

        try:
            ext = os.path.splitext(file.filename)[1]
            unique_name = f"{uuid4().hex}{ext}"
            temp_path = os.path.join(TEMP_DIR, unique_name)
            file.save(temp_path)

            upload_result = upload_file_to_b2(temp_path, unique_name)
            os.remove(temp_path)

            logger.info(f"✅ Uploaded: {file.filename} -> {unique_name}")
            results.append({
                "original": file.filename,
                "filename": unique_name,
                "result": upload_result
            })

        except Exception as e:
            logger.error(f"❌ Upload error [{file.filename}]: {e}")
            results.append({
                "filename": file.filename,
                "result": f"❌ Upload failed: {str(e)}"
            })

    return jsonify(results), 207 if any(r["result"].startswith("❌") for r in results) else 200


# 📂 List Files
@drive_bp.route("/files", methods=["GET"])
def list_files():
    try:
        files = list_files_in_b2()
        return jsonify(files), 200
    except Exception as e:
        logger.error(f"❌ Error listing files: {e}")
        return jsonify({"error": str(e)}), 500


# ⬇️ Generate Download URL
@drive_bp.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    try:
        url = get_file_download_url(filename)
        if not url:
            return jsonify({"error": f"{filename} not found"}), 404
        return jsonify({"download_url": url}), 200
    except Exception as e:
        logger.error(f"❌ Download URL error: {e}")
        return jsonify({"error": str(e)}), 500


# 🗑️ Delete File
@drive_bp.route("/<filename>", methods=["DELETE"])
def delete_file(filename):
    try:
        success = delete_file_from_b2(filename)
        if success:
            logger.info(f"✅ Deleted from B2: {filename}")
            return jsonify({"filename": filename, "result": "✅ Deleted"}), 200
        else:
            logger.warning(f"⚠️ File not found in B2: {filename}")
            return jsonify({"filename": filename, "result": "❌ Not Found"}), 404
    except Exception as e:
        logger.error(f"❌ Delete error [{filename}]: {e}")
        return jsonify({"filename": filename, "error": str(e)}), 500


# ✏️ Rename File
@drive_bp.route("/rename", methods=["POST"])
def rename_file():
    data = request.json or {}
    old_name = data.get("old_name")
    new_name = data.get("new_name")

    if not old_name or not new_name:
        return jsonify({"error": "Both 'old_name' and 'new_name' are required"}), 400

    try:
        result = rename_file_in_b2(old_name, new_name)
        logger.info(f"✅ Renamed: {old_name} -> {new_name}")
        return jsonify({"result": result}), 200
    except Exception as e:
        logger.error(f"❌ Rename error: {e}")
        return jsonify({"error": str(e)}), 500


# 📦 Move File to Folder (simulate folder via prefix)
@drive_bp.route("/move", methods=["POST"])
def move_file():
    data = request.json or {}
    filename = data.get("filename")
    target_folder = data.get("target_folder")

    if not filename or not target_folder:
        return jsonify({"error": "'filename' and 'target_folder' required"}), 400

    try:
        result = move_file_to_folder(filename, target_folder)
        logger.info(f"✅ Moved: {filename} -> {target_folder}/")
        return jsonify({"result": result}), 200
    except Exception as e:
        logger.error(f"❌ Move error: {e}")
        return jsonify({"error": str(e)}), 500
