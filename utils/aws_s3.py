# utils/aws_s3.py
import aioboto3
from fastapi.responses import StreamingResponse, Response
from config.config import (
    S3_BUCKET_NAME,
    S3_BUCKET_REGION,
    S3_BUCKET_ACCESS_KEY,
    S3_BUCKET_SECRET_KEY,
)

# ── S3 Client Session ─────────────────────────────────────────────────────────
def _get_session():
   return aioboto3.Session(
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name='us-east-1' 
    )


    # return aioboto3.Session(
    #     aws_access_key_id     = S3_BUCKET_ACCESS_KEY,
    #     aws_secret_access_key = S3_BUCKET_SECRET_KEY,
    #     region_name           = S3_BUCKET_REGION,
    # )


# ── Build S3 URL ──────────────────────────────────────────────────────────────

S3_BUCKET_NAME = "test-bucket"
S3_ENDPOINT_URL = "http://localhost:5000"

def build_s3_url(key: str) -> str:
    """
    Returns a URL to access a file in the local Moto S3 bucket.
    This mimics the standard S3 URL format.
    """
    return f"{S3_ENDPOINT_URL}/{S3_BUCKET_NAME}/{key}"

# ── Enable Versioning ─────────────────────────────────────────────────────────
async def enable_aws_s3_versioning():
    try:
        async with _get_session().client("s3", endpoint_url='http://localhost:5000') as s3:
            await s3.put_bucket_versioning(
                Bucket=S3_BUCKET_NAME,
                VersioningConfiguration={"Status": "Enabled"},
            )
        print("✅ S3 bucket versioning enabled.")
    except Exception as e:
        print(f"❌ Error enabling S3 versioning: {e}")


# ── Upload to S3 ──────────────────────────────────────────────────────────────
async def upload_to_s3(buffer: bytes, key: str, content_type: str) -> dict:
    try:
        async with _get_session().client("s3", endpoint_url='http://localhost:5000') as s3:
            await s3.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=key,
                Body=buffer,
                ContentType=content_type,
            )
        return {
            "Location": build_s3_url(key),
            "Key":      key,
        }
    except Exception as e:
        raise Exception(f"Error uploading to S3: {e}")


# ── Delete from S3 ────────────────────────────────────────────────────────────
async def delete_from_s3(key: str):
    try:
        async with _get_session().client("s3", endpoint_url='http://localhost:5000') as s3:
            await s3.delete_object(Bucket=S3_BUCKET_NAME, Key=key)
    except Exception as e:
        raise Exception(f"Error deleting from S3: {e}")


# ── Delete Directory from S3 ──────────────────────────────────────────────────
async def delete_directory_from_s3(s3_key: str):
    try:
        async with _get_session().client("s3",  endpoint_url='http://localhost:5000') as s3:
            listed = await s3.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=s3_key)
            contents = listed.get("Contents", [])
            if contents:
                await s3.delete_objects(
                    Bucket=S3_BUCKET_NAME,
                    Delete={"Objects": [{"Key": obj["Key"]} for obj in contents]},
                )
    except Exception as e:
        print(f"Error deleting S3 directory: {e}")


# ── Stream S3 File ────────────────────────────────────────────────────────────
async def stream_s3_file(key: str) -> StreamingResponse | Response:
    try:
        async with _get_session().client("s3", endpoint_url='http://localhost:5000') as s3:

            # head request — get metadata
            head = await s3.head_object(Bucket=S3_BUCKET_NAME, Key=key)

            headers = {
                "Content-Type": head.get("ContentType", "application/octet-stream"),
            }
            if head.get("ContentLength"):
                headers["Content-Length"] = str(head["ContentLength"])
            if head.get("CacheControl"):
                headers["Cache-Control"] = head["CacheControl"]

            # get object — stream body
            obj = await s3.get_object(Bucket=S3_BUCKET_NAME, Key=key)
            body = obj.get("Body")

            if not body:
                return Response(content="File not found", status_code=404)

            async def _iter():
                async for chunk in body.iter_chunks(chunk_size=1024 * 64):
                    yield chunk

            return StreamingResponse(_iter(), headers=headers)

    except Exception as e:
        print(f"S3 streaming error: {e}")
        return Response(content="Error fetching file", status_code=500)