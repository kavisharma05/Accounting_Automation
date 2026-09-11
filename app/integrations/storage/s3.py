import asyncio
from functools import partial

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import settings
from app.integrations.protocols import StorageProvider


class S3StorageProvider(StorageProvider):
    def __init__(self):
        if not settings.s3_bucket:
            raise RuntimeError("S3_BUCKET is not configured")
        if not settings.aws_access_key_id or not settings.aws_secret_access_key:
            raise RuntimeError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required")
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            config=BotoConfig(signature_version="s3v4"),
        )

    async def put(self, key: str, content: bytes, mime_type: str) -> str:
        await asyncio.to_thread(
            partial(
                self.client.put_object,
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType=mime_type,
            )
        )
        return key

    async def get(self, key: str) -> tuple[bytes, str]:
        try:
            obj = await asyncio.to_thread(
                partial(self.client.get_object, Bucket=self.bucket, Key=key)
            )
        except ClientError as e:
            raise FileNotFoundError(f"S3 object not found: {key}") from e
        content = await asyncio.to_thread(obj["Body"].read)
        mime = obj.get("ContentType") or "application/octet-stream"
        return content, mime

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(
            partial(self.client.delete_object, Bucket=self.bucket, Key=key)
        )
