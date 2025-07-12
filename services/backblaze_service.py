import os
import boto3
import logging
from dotenv import load_dotenv
from botocore.exceptions import ClientError

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
    region_name=B2_REGION
)

# === HELPERS ===
def file_exists(key: str) -> bool:
    try:
        s3.head_object(Bucket=B2_BUCKET, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise

# === MAIN FUNCTIONS ===

def upload_file_to_b2(file_path: str, file_key: str) -> str:
    try:
        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"

        if file_exists(file_key):
            return f"⚠️ File already exists: {file_key}"

        s3.upload_file(file_path, B2_BUCKET, file_key)
        logger.info(f"✅ Uploaded {file_key} to {B2_BUCKET}")
        return f"✅ Uploaded {file_key} to {B2_BUCKET}"
    except Exception as e:
        logger.error(f"❌ Upload failed: {file_key}", exc_info=True)
        return f"❌ Upload failed: {str(e)}"

def list_files_in_b2():
    try:
        result = []
        paginator = s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=B2_BUCKET):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                size = obj["Size"]
                url = get_file_download_url(key)
                if isinstance(url, dict) and "error" in url:
                    url = None

                result.append({
                    "filename": key,
                    "size": size,
                    "download_url": url
                })

        return result
    except Exception as e:
        logger.error("❌ Error listing files", exc_info=True)
        raise RuntimeError(f"❌ B2 list failed: {str(e)}")

def get_file_download_url(filename: str):
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": B2_BUCKET, "Key": filename},
            ExpiresIn=3600
        )
        return url
    except Exception as e:
        logger.error(f"❌ Failed to generate URL for {filename}", exc_info=True)
        return {"error": str(e)}

def delete_file_from_b2(filename: str) -> str:
    try:
        if not file_exists(filename):
            return f"❌ File not found: {filename}"

        s3.delete_object(Bucket=B2_BUCKET, Key=filename)
        logger.info(f"✅ Deleted {filename} from {B2_BUCKET}")
        return f"✅ Deleted {filename}"
    except Exception as e:
        logger.error(f"❌ Delete failed: {filename}", exc_info=True)
        return f"❌ Delete failed: {str(e)}"

def rename_file_in_b2(old_name: str, new_name: str) -> str:
    try:
        if not file_exists(old_name):
            return f"❌ File not found: {old_name}"

        s3.copy_object(
            Bucket=B2_BUCKET,
            CopySource={"Bucket": B2_BUCKET, "Key": old_name},
            Key=new_name
        )
        s3.delete_object(Bucket=B2_BUCKET, Key=old_name)

        logger.info(f"✅ Renamed {old_name} to {new_name}")
        return f"✅ Renamed {old_name} to {new_name}"
    except Exception as e:
        logger.error(f"❌ Rename failed: {old_name} → {new_name}", exc_info=True)
        return f"❌ Rename failed: {str(e)}"

def move_file_to_folder(filename: str, target_folder: str) -> str:
    try:
        safe_folder = target_folder.strip().rstrip("/")
        new_key = f"{safe_folder}/{os.path.basename(filename)}"
        return rename_file_in_b2(filename, new_key)
    except Exception as e:
        logger.error(f"❌ Move failed: {filename} → {target_folder}", exc_info=True)
        return f"❌ Move failed: {str(e)}"
