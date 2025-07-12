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
import mimetypes
import logging
from werkzeug.utils import secure_filename

# === Setup ===
drive_bp = Blueprint("drive", __name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DriveAPI")
TEMP_DIR = "/tmp"
os.makedirs(TEMP_DIR, exist_ok=True)

# === Universal Upload ===
@drive_bp.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("file")
    folder = request.form.get("folder", "").strip()  # optional subfolder path

    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    results = []
    for file in files:
        filename = file.filename.strip()
        if not filename:
            results.append({"filename": None, "result": "❌ Empty filename skipped"})
            continue

        try:
            safe_filename = secure_filename(filename)
            final_key = os.path.join(folder, safe_filename) if folder else safe_filename

            temp_path = os.path.join(TEMP_DIR, safe_filename)
            file.save(temp_path)

            upload_result = upload_file_to_b2(temp_path, final_key)
            os.remove(temp_path)

            logger.info(f"✅ Uploaded: {final_key}")
            results.append({
                "original": filename,
                "filename": final_key,
                "display_name": filename,
                "result": upload_result
            })

        except Exception as e:
            logger.error(f"❌ Upload error [{filename}]: {e}")
            results.append({"filename": filename, "result": f"❌ Upload failed: {str(e)}"})

    return jsonify(results), 207 if any(r["result"].startswith("❌") for r in results) else 200

# === File Listing ===
@drive_bp.route("/files", methods=["GET"])
def list_files():
    try:
        raw_files = list_files_in_b2()
        result = []

        for obj in raw_files:
            key = obj.get("filename") or obj.get("Key")
            size = obj.get("size") or obj.get("Size", 0)

            if not key or key.endswith("/"):
                continue

            mime_type, _ = mimetypes.guess_type(key)
            file_type = mime_type.split("/")[0] if mime_type else "file"
            download_url = get_file_download_url(key)

            if not download_url or isinstance(download_url, dict):
                continue

            result.append({
                "filename": key,
                "name": key,
                "display_name": os.path.basename(key),
                "type": file_type,
                "size": size,
                "download_url": download_url
            })

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"❌ Error listing files: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# === Download URL ===
@drive_bp.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    try:
        safe_filename = secure_filename(filename)
        url = get_file_download_url(safe_filename)
        if not url or isinstance(url, dict):
            return jsonify({"error": f"{filename} not found"}), 404
        return jsonify({"download_url": url}), 200
    except Exception as e:
        logger.error(f"❌ Download URL error: {e}")
        return jsonify({"error": str(e)}), 500


# === Delete File ===
@drive_bp.route("/<filename>", methods=["DELETE"])
def delete_file(filename):
    try:
        safe_filename = secure_filename(filename)
        result = delete_file_from_b2(safe_filename)
        if result.startswith("✅"):
            logger.info(f"✅ Deleted from B2: {filename}")
            return jsonify({"filename": filename, "result": result}), 200
        else:
            return jsonify({"filename": filename, "result": result}), 404
    except Exception as e:
        logger.error(f"❌ Delete error: {e}")
        return jsonify({"filename": filename, "error": str(e)}), 500


# === Rename File ===
@drive_bp.route("/rename", methods=["POST"])
def rename_file():
    data = request.json or {}
    old_name = data.get("old_name")
    new_name = data.get("new_name")

    if not old_name or not new_name:
        return jsonify({"error": "Both 'old_name' and 'new_name' are required"}), 400

    try:
        result = rename_file_in_b2(old_name, new_name)
        logger.info(f"✅ Renamed: {old_name} → {new_name}")
        return jsonify({"result": result}), 200
    except Exception as e:
        logger.error(f"❌ Rename error: {e}")
        return jsonify({"error": str(e)}), 500


# === Move File (simulate folders) ===
@drive_bp.route("/move", methods=["POST"])
def move_file():
    data = request.json or {}
    filename = data.get("filename")
    target_folder = data.get("target_folder")

    if not filename or not target_folder:
        return jsonify({"error": "'filename' and 'target_folder' are required"}), 400

    try:
        result = move_file_to_folder(filename, target_folder)
        logger.info(f"✅ Moved: {filename} → {target_folder}/")
        return jsonify({"result": result}), 200
    except Exception as e:
        logger.error(f"❌ Move error: {e}")
        return jsonify({"error": str(e)}), 500
