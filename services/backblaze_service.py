# services/backblaze_service.py
import os
import boto3
import logging
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# === CONFIG ===
B2_BUCKET = os.getenv("B2_BUCKET")
B2_ENDPOINT = os.getenv("B2_ENDPOINT")
B2_ACCESS_KEY_ID = os.getenv("B2_ACCESS_KEY_ID")
B2_SECRET_ACCESS_KEY = os.getenv("B2_SECRET_ACCESS_KEY")
B2_REGION = os.getenv("B2_REGION") or "us-west-001"

# === VALIDATE ENV ===
if not all([B2_BUCKET, B2_ENDPOINT, B2_ACCESS_KEY_ID, B2_SECRET_ACCESS_KEY]):
    raise EnvironmentError("❌ Missing required Backblaze environment variables.")

# === LOGGING ===
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# === INIT CLIENT ===
s3 = boto3.client(
    "s3",
    endpoint_url=B2_ENDPOINT if B2_ENDPOINT.startswith("http") else f"https://{B2_ENDPOINT}",
    aws_access_key_id=B2_ACCESS_KEY_ID,
    aws_secret_access_key=B2_SECRET_ACCESS_KEY,
    region_name=B2_REGION,
)

def file_exists(key: str) -> bool:
    try:
        s3.head_object(Bucket=B2_BUCKET, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise

def list_files_in_b2():
    try:
        logger.info(f"Listing objects in bucket: {B2_BUCKET}")
        response = s3.list_objects_v2(Bucket=B2_BUCKET)
        logger.info(f"Response from list_objects_v2: {response}")

        if "Contents" not in response:
            logger.warning("No 'Contents' in response. Bucket empty or no permission.")
            return []

        contents = response.get("Contents", [])
        result = []

        for obj in contents:
            key = obj["Key"]
            size = obj["Size"]
            last_modified = obj["LastModified"]
            url = get_file_download_url(key)
            if isinstance(url, dict) and "error" in url:
                url = None

            result.append({
                "filename": key,
                "size": size,
                "last_modified": last_modified.isoformat(),
                "download_url": url,
            })

        logger.info(f"Found {len(result)} files.")
        return result
    except Exception as e:
        logger.error("Error listing files", exc_info=True)
        return []

def get_file_download_url(filename: str):
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": B2_BUCKET, "Key": filename},
            ExpiresIn=3600,
        )
        return url
    except Exception as e:
        logger.error(f"Failed to generate URL for {filename}", exc_info=True)
        return {"error": str(e)}

# --- Minimal Flask app to test listing ---

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/list-files')
def list_files_route():
    files = list_files_in_b2()
    return jsonify(files)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
