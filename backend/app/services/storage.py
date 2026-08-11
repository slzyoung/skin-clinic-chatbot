"""S3-compatible object storage via boto3 (MinIO, AWS S3, etc.)."""
import uuid
from loguru import logger
from app.core.config import settings

try:
    import boto3
    from botocore.config import Config
    HAS_BOTO3 = True
except ImportError:
    boto3 = None
    Config = None
    HAS_BOTO3 = False


def _bucket() -> str:
    return settings.S3_BUCKET


def _get_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path" if settings.S3_USE_PATH_STYLE else "auto"}
        ),
        region_name=settings.S3_REGION,
    )


def _ensure_bucket():
    try:
        client = _get_client()
        try:
            client.head_bucket(Bucket=_bucket())
        except Exception:
            client.create_bucket(Bucket=_bucket())
            logger.info(f"Created MinIO bucket: '{_bucket()}'")
    except Exception as e:
        logger.warning(f"Could not connect or ensure MinIO bucket '{_bucket()}': {e}")


def upload_image(content: bytes, filename: str, content_type: str = "image/png") -> dict:
    """
    Synchronously uploads image binary content to MinIO bucket and returns s3_key & presigned_url.
    Returns fallback local info if MinIO is unavailable.
    """
    s3_key = f"images/{uuid.uuid4().hex}_{filename}"
    if not HAS_BOTO3:
        logger.warning(f"boto3 package not installed. Returning fallback image info for '{filename}'.")
        return {
            "s3_key": s3_key,
            "image_url": f"/static/images/{filename}",
            "size": len(content),
            "status": "fallback"
        }
    try:
        _ensure_bucket()
        client = _get_client()

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        client.put_object(
            Bucket=_bucket(),
            Key=s3_key,
            Body=content,
            **extra_args
        )

        presigned_url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": _bucket(), "Key": s3_key},
            ExpiresIn=604800  # 7 days
        )

        logger.info(f"Successfully uploaded image '{filename}' to MinIO key '{s3_key}'")
        return {
            "s3_key": s3_key,
            "image_url": presigned_url,
            "size": len(content),
            "status": "success"
        }
    except Exception as e:
        logger.warning(f"MinIO upload failed for '{filename}': {e}. Returning fallback key.")
        return {
            "s3_key": s3_key,
            "image_url": f"/static/images/{filename}",
            "size": len(content),
            "status": "fallback"
        }


def get_presigned_url(s3_key: str, expires: int = 604800) -> str:
    """Generates presigned GET URL for an existing S3 object key."""
    try:
        client = _get_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": _bucket(), "Key": s3_key},
            ExpiresIn=expires
        )
    except Exception as e:
        logger.warning(f"Failed to generate presigned URL for key '{s3_key}': {e}")
        return s3_key


def delete_image(s3_key: str) -> None:
    """Deletes an image object from MinIO bucket."""
    try:
        client = _get_client()
        client.delete_object(Bucket=_bucket(), Key=s3_key)
        logger.info(f"Deleted MinIO object: '{s3_key}'")
    except Exception as e:
        logger.warning(f"Failed to delete MinIO object '{s3_key}': {e}")
