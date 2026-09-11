import pytest

from app.core.config import settings
from app.integrations.factory import get_storage_provider
from app.integrations.storage.local import LocalStorageProvider
from app.integrations.storage.s3 import S3StorageProvider


def test_factory_defaults_to_local():
    assert isinstance(get_storage_provider(), LocalStorageProvider)


def test_factory_falls_back_to_local_when_s3_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "storage_provider", "s3")
    monkeypatch.setattr(settings, "s3_bucket", "")
    assert isinstance(get_storage_provider(), LocalStorageProvider)


def test_s3_provider_requires_bucket(monkeypatch):
    monkeypatch.setattr(settings, "s3_bucket", "")
    with pytest.raises(RuntimeError, match="S3_BUCKET"):
        S3StorageProvider()
