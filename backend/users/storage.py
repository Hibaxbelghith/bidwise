from __future__ import annotations

from io import BytesIO
from pathlib import PurePosixPath

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import File
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible


def _normalize_name(name: str) -> str:
    parts = [
        part
        for part in str(name or "").replace("\\", "/").split("/")
        if part and part not in {".", ".."}
    ]
    return "/".join(parts)


def _split_cloudinary_name(name: str) -> tuple[str, str, str]:
    normalized = _normalize_name(name)
    path = PurePosixPath(normalized)
    extension = path.suffix.lower().lstrip(".")
    public_id = str(path.with_suffix("")) if extension else normalized
    return normalized, public_id, extension


@deconstructible
class ProfileResumeStorage(Storage):
    request_timeout_seconds = 30

    def _local_storage(self) -> FileSystemStorage:
        return FileSystemStorage(
            location=getattr(settings, "MEDIA_ROOT", None),
            base_url=getattr(settings, "MEDIA_URL", None),
        )

    def _use_cloudinary(self) -> bool:
        return bool(getattr(settings, "PROFILE_RESUME_USE_CLOUDINARY", False))

    def _configure_cloudinary(self):
        try:
            import cloudinary
        except ImportError as exc:  # pragma: no cover - exercised in runtime config only
            raise ImproperlyConfigured(
                "Cloudinary resume storage is enabled, but the 'cloudinary' package is not installed."
            ) from exc

        cloud_name = getattr(settings, "CLOUDINARY_CLOUD_NAME", "").strip()
        api_key = getattr(settings, "CLOUDINARY_API_KEY", "").strip()
        api_secret = getattr(settings, "CLOUDINARY_API_SECRET", "").strip()
        if not all((cloud_name, api_key, api_secret)):
            raise ImproperlyConfigured(
                "Cloudinary resume storage is enabled, but Cloudinary credentials are incomplete."
            )

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=bool(getattr(settings, "CLOUDINARY_SECURE", True)),
        )
        return cloudinary

    def _cloudinary_url(self, name: str) -> str:
        self._configure_cloudinary()
        from cloudinary import api
        from cloudinary.exceptions import NotFound
        from cloudinary.utils import cloudinary_url

        normalized, _public_id, extension = _split_cloudinary_name(name)
        try:
            resource = api.resource(normalized, resource_type="raw", type="upload")
        except NotFound:
            resource = None

        secure_url = (resource or {}).get("secure_url") or (resource or {}).get("url")
        if secure_url:
            return secure_url

        url, _options = cloudinary_url(
            normalized,
            resource_type="raw",
            type="upload",
            secure=bool(getattr(settings, "CLOUDINARY_SECURE", True)),
        )
        if url:
            return url

        fallback_public_id = _public_id if extension else normalized
        fallback_url, _options = cloudinary_url(
            fallback_public_id,
            resource_type="raw",
            type="upload",
            format=extension or None,
            secure=bool(getattr(settings, "CLOUDINARY_SECURE", True)),
        )
        return fallback_url or normalized

    def _open(self, name, mode="rb"):
        if not self._use_cloudinary():
            return self._local_storage().open(name, mode)

        response = requests.get(
            self._cloudinary_url(name),
            timeout=self.request_timeout_seconds,
        )
        response.raise_for_status()
        return File(BytesIO(response.content), name=PurePosixPath(_normalize_name(name)).name)

    def _save(self, name, content):
        if not self._use_cloudinary():
            return self._local_storage().save(name, content)

        self._configure_cloudinary()
        from cloudinary import uploader

        normalized, public_id, extension = _split_cloudinary_name(name)
        if hasattr(content, "open"):
            content.open("rb")
        if hasattr(content, "seek"):
            content.seek(0)

        result = uploader.upload(
            content,
            resource_type="raw",
            public_id=public_id,
            overwrite=True,
            unique_filename=False,
            use_filename=False,
            type="upload",
            filename_override=PurePosixPath(normalized).name,
        )
        uploaded_public_id = str(result.get("public_id") or "").strip()
        uploaded_extension = str(result.get("format") or extension or "").lstrip(".")
        if uploaded_public_id:
            if uploaded_extension and not uploaded_public_id.lower().endswith(f".{uploaded_extension.lower()}"):
                return f"{uploaded_public_id}.{uploaded_extension}"
            return uploaded_public_id
        return f"{public_id}.{uploaded_extension}" if uploaded_extension else normalized

    def delete(self, name):
        if not self._use_cloudinary():
            return self._local_storage().delete(name)

        self._configure_cloudinary()
        from cloudinary import api

        normalized, _public_id, _extension = _split_cloudinary_name(name)
        api.delete_resources(
            [normalized],
            resource_type="raw",
            type="upload",
            invalidate=True,
        )

    def exists(self, name):
        if not self._use_cloudinary():
            return self._local_storage().exists(name)
        return False

    def size(self, name):
        if not self._use_cloudinary():
            return self._local_storage().size(name)

        self._configure_cloudinary()
        from cloudinary import api

        normalized, _public_id, _extension = _split_cloudinary_name(name)
        resource = api.resource(normalized, resource_type="raw", type="upload")
        return int(resource.get("bytes") or 0)

    def url(self, name):
        if not self._use_cloudinary():
            return self._local_storage().url(name)
        return self._cloudinary_url(name)
