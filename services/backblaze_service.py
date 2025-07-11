import os
import boto3
from dotenv import load_dotenv

load_dotenv()

B2_BUCKET = os.getenv("B2_BUCKET")
B2_ENDPOINT = os.getenv("B2_ENDPOINT")
B2_REGION = os.getenv("B2_REGION")
B2_ACCESS_KEY_ID = os.getenv("B2_ACCESS_KEY_ID")
B2_SECRET_ACCESS_KEY = os.getenv("B2_SECRET_ACCESS_KEY")

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{B2_ENDPOINT}",
    aws_access_key_id=B2_ACCESS_KEY_ID,
    aws_secret_access_key=B2_SECRET_ACCESS_KEY,
    region_name=B2_REGION
)

def upload_file_to_b2(file_path, file_key):
    try:
        s3.upload_file(file_path, B2_BUCKET, file_key)
        return f"✅ Uploaded {file_key} to {B2_BUCKET}"
    except Exception as e:
        return f"❌ Upload failed: {str(e)}"

def list_files_in_b2():
    try:
        response = s3.list_objects_v2(Bucket=B2_BUCKET)
        files = response.get("Contents", [])
        return [{"filename": obj["Key"], "size": obj["Size"]} for obj in files]
    except Exception as e:
        return {"error": str(e)}

def get_file_download_url(file_key, expires_in=3600):
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": B2_BUCKET, "Key": file_key},
            ExpiresIn=expires_in
        )
        return url
    except Exception as e:
        return {"error": str(e)}

def delete_file_from_b2(file_key):
    try:
        s3.delete_object(Bucket=B2_BUCKET, Key=file_key)
        return f"✅ Deleted {file_key}"
    except Exception as e:
        return f"❌ Delete failed: {str(e)}"

def rename_file_in_b2(old_name, new_name):
    try:
        copy_source = {"Bucket": B2_BUCKET, "Key": old_name}
        s3.copy_object(
            Bucket=B2_BUCKET,
            CopySource=copy_source,
            Key=new_name
        )
        s3.delete_object(Bucket=B2_BUCKET, Key=old_name)
        return f"✅ Renamed {old_name} to {new_name}"
    except Exception as e:
        return f"❌ Rename failed: {str(e)}"

def move_file_to_folder(file_key, folder_name):
    try:
        new_key = f"{folder_name}/{os.path.basename(file_key)}"
        return rename_file_in_b2(file_key, new_key)
    except Exception as e:
        return f"❌ Move failed: {str(e)}"
