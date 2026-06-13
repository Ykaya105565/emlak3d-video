import boto3
from botocore.client import Config
from app.core.config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def upload_file(bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    client = get_s3_client()
    client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
    return key


def get_presigned_url(bucket: str, key: str, expires: int = 3600) -> str:
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires,
    )
