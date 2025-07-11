import os
import boto3
import logging
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

# === CONFIG ===
B2_BUCKET              = os.getenv("B2_BUCKET")
B2_ENDPOINT            = os.getenv("B2_ENDPOINT")
B2_ACCESS_KEY_ID       = os.getenv("B2_ACCESS_KEY_ID")
B2_SECRET_ACCESS_KEY   = os.getenv("B2_SECRET_ACCESS_KEY")
B2_REGION              = os.getenv("B2_REGION") or "us-west-001"

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

def guess_file_type(filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext in ["jpg","jpeg","png","gif","bmp","webp"]: return "image"
    if ext in ["mp4","mov","avi","mkv","webm"]:       return "video"
    if ext in ["mp3","wav","aac","m4a","ogg"]:         return "audio"
    if ext == "pdf":                                   return "pdf"
    if ext in ["txt","md"]:                            return "text"
    if ext in ["doc","docx","ppt","pptx","xls","xlsx"]:return "document"
    if ext in ["dart","js","py","java","c","cpp","html","css"]: return "code"
    return "file"

# === MAIN FUNCTIONS ===

def upload_file_to_b2(file_path: str, file_key: str) -> str:
    if not os.path.exists(file_path):
        return f"❌ File not found: {file_path}"
    if file_exists(file_key):
        return f"⚠️ File already exists: {file_key}"
    try:
        s3.upload_file(file_path, B2_BUCKET, file_key)
        logger.info(f"✅ Uploaded {file_key}")
        return f"✅ Uploaded {file_key}"
    except Exception as e:
        logger.error(f"❌ Upload failed: {file_key}", exc_info=True)
        return f"❌ Upload failed: {e}"

def list_files_in_b2():
    try:
        resp = s3.list_objects_v2(Bucket=B2_BUCKET)
        out = []
        for obj in resp.get("Contents", []):
            key  = obj["Key"]
            size = obj["Size"]
            lm   = obj["LastModified"]
            out.append({
                "name": key,
                "type": guess_file_type(key),
                "size": size,
                "creationDate": lm.isoformat(),
                "lastModified": lm.isoformat(),
                "download_url": get_file_download_url(key)
            })
        logger.info(f"✅ Listed {len(out)} file(s)")
        return out
    except Exception as e:
        logger.error("❌ Error listing", exc_info=True)
        return []

def get_file_download_url(filename: str):
    try:
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": B2_BUCKET, "Key": filename},
            ExpiresIn=3600
        )
    except Exception as e:
        logger.error(f"❌ URL gen failed: {filename}", exc_info=True)
        return {"error": str(e)}

def delete_file_from_b2(filename: str) -> str:
    if not file_exists(filename):
        return f"❌ Not found: {filename}"
    try:
        s3.delete_object(Bucket=B2_BUCKET, Key=filename)
        logger.info(f"✅ Deleted {filename}")
        return f"✅ Deleted {filename}"
    except Exception as e:
        logger.error(f"❌ Delete failed: {filename}", exc_info=True)
        return f"❌ Delete failed: {e}"

def rename_file_in_b2(old: str, new: str) -> str:
    if not file_exists(old):
        return f"❌ Not found: {old}"
    try:
        s3.copy_object(Bucket=B2_BUCKET, CopySource={"Bucket":B2_BUCKET,"Key":old}, Key=new)
        s3.delete_object(Bucket=B2_BUCKET, Key=old)
        logger.info(f"✅ Renamed {old} → {new}")
        return f"✅ Renamed {old} → {new}"
    except Exception as e:
        logger.error(f"❌ Rename failed: {old}", exc_info=True)
        return f"❌ Rename failed: {e}"

def move_file_to_folder(filename: str, folder: str) -> str:
    target = f"{folder.rstrip('/')}/{filename}"
    return rename_file_in_b2(filename, target)
