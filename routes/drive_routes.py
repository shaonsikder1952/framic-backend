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

# === Blueprint Setup ===
drive_bp = Blueprint("drive", __name__)

# === Logging Setup ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DriveAPI")

# === Temp folder setup ===
TEMP_DIR = "/tmp"
os.makedirs(TEMP_DIR, exist_ok=True)

# === Upload Files ===
@drive_bp.route("/drive/upload", methods=["POST"])
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

            logger.info(f"✅ Uploaded: {file.filename} → {unique_name}")
            results.append({
                "original": file.filename,
                "filename": unique_name,
                "display_name": file.filename,
                "result": upload_result
            })

        except Exception as e:
            logger.error(f"❌ Upload error [{file.filename}]: {e}")
            results.append({
                "filename": file.filename,
                "result": f"❌ Upload failed: {str(e)}"
            })

    return jsonify(results), 207 if any(r["result"].startswith("❌") for r in results) else 200

# === List Files ===@drive_bp.route("/files", methods=["GET"])
def list_files():
    try:
        raw_files = list_files_in_b2()
        result = []

        logger.info(f"📦 Total files fetched from B2: {len(raw_files)}")

        for obj in raw_files:
            key = obj.get("filename") or obj.get("Key")
            size = obj.get("size") or obj.get("Size", 0)

            if not key:
                logger.warning("⚠️ Skipping file with empty key.")
                continue

            # ⛔ Skip folder keys
            if key.endswith("/"):
                logger.info(f"📁 Skipping folder key: {key}")
                continue

            # 🔍 Type detection
            ext = os.path.splitext(key)[1].lower()
            if ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
                file_type = "image"
            elif ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
                file_type = "video"
            elif ext in [".mp3", ".wav", ".aac", ".m4a", ".ogg"]:
                file_type = "audio"
            elif ext in [".pdf"]:
                file_type = "pdf"
            elif ext in [".txt", ".md"]:
                file_type = "text"
            elif ext in [".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"]:
                file_type = "document"
            elif ext in [".py", ".js", ".ts", ".java", ".cpp", ".c", ".html", ".css", ".dart", ".go", ".rs", ".rb"]:
                file_type = "code"
            else:
                file_type = "file"

            download_url = get_file_download_url(key)
            if not download_url or isinstance(download_url, dict):
                logger.warning(f"❌ No download URL for: {key}")
                continue

            logger.info(f"✅ File: {key} | Type: {file_type} | Size: {size}")

            result.append({
    "filename": key,
    "name": key,  # 👈 Add this to keep frontend happy
    "display_name": key,  # 👈 optional — use if you track original
    "type": file_type,
    "size": size,
    "download_url": download_url
})

        logger.info(f"✅ Returning {len(result)} valid files to client.")
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"❌ Error listing files: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# === Download URL ===
@drive_bp.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    try:
        url = get_file_download_url(filename)
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
        result = delete_file_from_b2(filename)
        if result.startswith("✅"):
            logger.info(f"✅ Deleted from B2: {filename}")
            return jsonify({"filename": filename, "result": result}), 200
        else:
            logger.warning(f"⚠️ File not found or delete failed: {filename}")
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
