import os
import boto3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# DEBUG print for environment values
print("DEBUG ENV:")
print("  B2_ENDPOINT:", os.getenv("B2_ENDPOINT"))
print("  B2_ACCESS_KEY_ID:", os.getenv("B2_ACCESS_KEY_ID"))
print("  B2_SECRET_ACCESS_KEY:", os.getenv("B2_SECRET_ACCESS_KEY"))
print("  B2_BUCKET:", os.getenv("B2_BUCKET"))
print("  B2_REGION:", os.getenv("B2_REGION"))

# Initialize boto3 S3 client for Backblaze B2
s3 = boto3.client(
    's3',
    endpoint_url=f"https://{os.getenv('B2_ENDPOINT')}",
    aws_access_key_id=os.getenv('B2_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('B2_SECRET_ACCESS_KEY'),
    region_name=os.getenv('B2_REGION')
)

def upload_file_to_b2(file_path, file_key):
    try:
        bucket_name = os.getenv("B2_BUCKET")
        print(f"🔁 Uploading {file_key} to bucket {bucket_name} from path {file_path}...")

        # Upload to B2
        s3.upload_file(file_path, bucket_name, file_key)

        print("✅ Upload successful")
        return f"✅ Uploaded {file_key} to {bucket_name}"
    except Exception as e:
        print("❌ Upload failed:", e)
        return f"❌ Upload failed: {e}"
