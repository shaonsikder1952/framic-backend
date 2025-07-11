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
        os.remove(file_path)
        results.append({"filename": file.filename, "result": result})

    return jsonify(results)


@drive_bp.route("/files", methods=["GET"])
def list_files():
    result = list_files_in_b2()
    return jsonify(result)


@drive_bp.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    url = get_file_download_url(filename)
    return jsonify({"download_url": url})


@drive_bp.route("/delete/<filename>", methods=["DELETE"])
def delete_file(filename):
    result = delete_file_from_b2(filename)
    return jsonify({"filename": filename, "result": result})


@drive_bp.route("/rename", methods=["POST"])
def rename_file():
    data = request.json
    old_name = data.get("old_name")
    new_name = data.get("new_name")
    result = rename_file_in_b2(old_name, new_name)
    return jsonify(result)


@drive_bp.route("/move", methods=["POST"])
def move_file():
    data = request.json
    filename = data.get("filename")
    target_folder = data.get("target_folder")
    result = move_file_to_folder(filename, target_folder)
    return jsonify(result)
