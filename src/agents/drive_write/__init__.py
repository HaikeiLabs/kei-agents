"""Harness-side Google Drive doc writes (owner decision 2026-10-09).

Drive writes are agent action tools that the harness runs with the
invoking user's own Google OAuth access token (scope ``drive.file``). They
are not Kei connector capabilities. kei-proxy ``authorize`` still gates each
write, on the resource this module derives (``drive:folder/<id>`` for a
create, ``drive:doc/<id>`` for an update).

The write is confirm-required and happens in two steps:

1. :func:`preview_drive_write` validates the model's arguments and returns a
   :class:`DriveWritePreview`. The harness hands
   :meth:`DriveWritePreview.to_tool_result` back to the model and shows the
   preview to the user. Nothing is written.
2. After the user confirms that exact preview, the harness calls
   :func:`commit_drive_write` with ``confirmation=preview.digest``, the
   user's access token, and its own HTTP client. A missing or stale
   confirmation writes nothing.

This module holds no credentials and no HTTP library: the harness injects
the token and a :class:`DriveHTTPClient`. The token is only ever placed in
the ``Authorization`` header of the request. It is never logged, returned,
or included in an error.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
GOOGLE_DOC_MIME_TYPE = "application/vnd.google-apps.document"
MARKDOWN_MIME_TYPE = "text/markdown"

CREATE_DOC_TOOL = "drive_create_doc"
UPDATE_DOC_TOOL = "drive_update_doc"

# Drive's simple and multipart uploads accept up to 5 MB.
MAX_MARKDOWN_BYTES = 5 * 1024 * 1024
MAX_TITLE_CHARS = 256
PREVIEW_EXCERPT_CHARS = 1200
_MAX_ERROR_MESSAGE_CHARS = 200

_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
_RESPONSE_FIELDS = "id,name,webViewLink"
_DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,128}$")


class DriveWriteError(ValueError):
    """The model's arguments cannot become a Drive write."""


@dataclass(frozen=True)
class DriveHTTPResponse:
    """What the harness's HTTP client got back from Drive."""

    status: int
    body: bytes


class DriveHTTPClient(Protocol):
    """The harness's HTTP transport (for example a thin httpx wrapper)."""

    def send(
        self, method: str, url: str, headers: Mapping[str, str], body: bytes
    ) -> DriveHTTPResponse:
        """Send one request; raise only on a transport failure."""
        ...


@dataclass(frozen=True)
class DriveWritePreview:
    """A validated, not-yet-confirmed Drive write.

    ``digest`` binds a confirmation to this exact tool, target, title, and
    content. It is for the harness's confirm step only and is not part of the
    model-facing tool result.
    """

    tool: str
    resource: str
    markdown: str = field(repr=False)
    folder_id: str | None = None
    doc_id: str | None = None
    title: str | None = None
    digest: str = field(default="", repr=False)

    def to_tool_result(self) -> dict[str, Any]:
        """The bounded result returned to the model: a preview, not a write."""
        result: dict[str, Any] = {
            "status": "confirmation_required",
            "tool": self.tool,
            "resource": self.resource,
        }
        if self.folder_id is not None:
            result["folder_id"] = self.folder_id
        if self.doc_id is not None:
            result["doc_id"] = self.doc_id
        if self.title is not None:
            result["title"] = self.title
        result["markdown_chars"] = len(self.markdown)
        result["markdown_excerpt"] = self.markdown[:PREVIEW_EXCERPT_CHARS]
        result["message"] = (
            "Nothing has been written yet. The user must confirm this preview "
            "before the doc is written."
        )
        return result


def _require_drive_id(name: str, value: object) -> str:
    if not isinstance(value, str) or not _DRIVE_ID_RE.fullmatch(value):
        raise DriveWriteError(
            f"{name} must be a Drive file id (10-128 letters, digits, '-' or '_')"
        )
    return value


def _require_markdown(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DriveWriteError("markdown must be non-empty text")
    if len(value.encode("utf-8")) > MAX_MARKDOWN_BYTES:
        raise DriveWriteError(f"markdown exceeds {MAX_MARKDOWN_BYTES} bytes")
    return value


def _require_title(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DriveWriteError("title must be non-empty text")
    if len(value) > MAX_TITLE_CHARS:
        raise DriveWriteError(f"title exceeds {MAX_TITLE_CHARS} characters")
    return value.strip()


def _digest(fields: Mapping[str, str | None]) -> str:
    canonical = json.dumps(fields, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def preview_create_doc(folder_id: str, title: str, markdown: str) -> DriveWritePreview:
    """Preview ``drive_create_doc``: a new Google Doc in a parent folder."""
    folder_id = _require_drive_id("folder_id", folder_id)
    title = _require_title(title)
    markdown = _require_markdown(markdown)
    return DriveWritePreview(
        tool=CREATE_DOC_TOOL,
        resource=f"drive:folder/{folder_id}",
        markdown=markdown,
        folder_id=folder_id,
        title=title,
        digest=_digest(
            {
                "tool": CREATE_DOC_TOOL,
                "folder_id": folder_id,
                "title": title,
                "markdown": markdown,
            }
        ),
    )


def preview_update_doc(doc_id: str, markdown: str) -> DriveWritePreview:
    """Preview ``drive_update_doc``: replace a Google Doc's content."""
    doc_id = _require_drive_id("doc_id", doc_id)
    markdown = _require_markdown(markdown)
    return DriveWritePreview(
        tool=UPDATE_DOC_TOOL,
        resource=f"drive:doc/{doc_id}",
        markdown=markdown,
        doc_id=doc_id,
        digest=_digest(
            {"tool": UPDATE_DOC_TOOL, "doc_id": doc_id, "markdown": markdown}
        ),
    )


def preview_drive_write(tool_name: str, args: Mapping[str, Any]) -> DriveWritePreview:
    """Preview a model tool call by name; raises :class:`DriveWriteError`."""
    if tool_name == CREATE_DOC_TOOL:
        return preview_create_doc(
            args.get("folder_id"), args.get("title"), args.get("markdown")  # type: ignore[arg-type]
        )
    if tool_name == UPDATE_DOC_TOOL:
        return preview_update_doc(args.get("doc_id"), args.get("markdown"))  # type: ignore[arg-type]
    raise DriveWriteError(f"not a Drive write tool: {tool_name!r}")


def drive_write_resource(tool_name: str, args: Mapping[str, Any]) -> str:
    """The kei-proxy authorize resource for a Drive write tool call."""
    if tool_name == CREATE_DOC_TOOL:
        return f"drive:folder/{_require_drive_id('folder_id', args.get('folder_id'))}"
    if tool_name == UPDATE_DOC_TOOL:
        return f"drive:doc/{_require_drive_id('doc_id', args.get('doc_id'))}"
    raise DriveWriteError(f"not a Drive write tool: {tool_name!r}")


def _multipart(metadata: Mapping[str, Any], markdown: str, boundary: str) -> bytes:
    parts = [
        f"--{boundary}",
        "Content-Type: application/json; charset=UTF-8",
        "",
        json.dumps(metadata, sort_keys=True),
        f"--{boundary}",
        f"Content-Type: {MARKDOWN_MIME_TYPE}; charset=UTF-8",
        "",
        markdown,
        f"--{boundary}--",
        "",
    ]
    return "\r\n".join(parts).encode("utf-8")


def _request(preview: DriveWritePreview) -> tuple[str, str, dict[str, str], bytes]:
    """Build (method, url, headers-without-auth, body) for a preview."""
    query = f"fields={_RESPONSE_FIELDS}&supportsAllDrives=true"
    if preview.tool == CREATE_DOC_TOOL:
        boundary = f"kei-agents-{preview.digest[:32]}"
        if boundary in preview.markdown:
            boundary = f"kei-agents-{preview.digest}"
        metadata = {
            "name": preview.title,
            "mimeType": GOOGLE_DOC_MIME_TYPE,
            "parents": [preview.folder_id],
        }
        return (
            "POST",
            f"{_UPLOAD_URL}?uploadType=multipart&{query}",
            {"Content-Type": f"multipart/related; boundary={boundary}"},
            _multipart(metadata, preview.markdown, boundary),
        )
    return (
        "PATCH",
        f"{_UPLOAD_URL}/{preview.doc_id}?uploadType=media&{query}",
        {"Content-Type": f"{MARKDOWN_MIME_TYPE}; charset=UTF-8"},
        preview.markdown.encode("utf-8"),
    )


def _error_message(body: bytes) -> str:
    try:
        payload = json.loads(body)
        message = payload["error"]["message"]
    except (ValueError, KeyError, TypeError):
        return ""
    return str(message)[:_MAX_ERROR_MESSAGE_CHARS]


def commit_drive_write(
    preview: DriveWritePreview,
    *,
    confirmation: str | None,
    access_token: str,
    http: DriveHTTPClient,
) -> dict[str, Any]:
    """Write a confirmed preview to Drive with the user's own token.

    ``confirmation`` must equal ``preview.digest``; the harness passes it only
    after the user confirms this preview. Returns a bounded result and never
    raises for a Drive or transport failure.
    """
    base: dict[str, Any] = {"tool": preview.tool, "resource": preview.resource}
    if not confirmation or not hmac.compare_digest(confirmation, preview.digest):
        return {**base, "status": "not_confirmed"}
    if not access_token:
        return {**base, "status": "error", "error": "missing_user_token"}
    method, url, headers, body = _request(preview)
    headers = {**headers, "Authorization": f"Bearer {access_token}"}
    try:
        response = http.send(method, url, headers, body)
    except Exception as exc:  # noqa: BLE001 - never surface transport detail
        return {
            **base,
            "status": "error",
            "error": "transport_error",
            "detail": type(exc).__name__,
        }
    if not 200 <= response.status < 300:
        result = {**base, "status": "error", "error": f"drive_http_{response.status}"}
        message = _error_message(response.body)
        if message:
            result["message"] = message
        return result
    try:
        payload = json.loads(response.body)
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    return {
        **base,
        "status": "created" if preview.tool == CREATE_DOC_TOOL else "updated",
        "doc_id": payload.get("id", preview.doc_id),
        "title": payload.get("name", preview.title),
        "url": payload.get("webViewLink"),
    }


__all__ = [
    "CREATE_DOC_TOOL",
    "DRIVE_FILE_SCOPE",
    "GOOGLE_DOC_MIME_TYPE",
    "MARKDOWN_MIME_TYPE",
    "MAX_MARKDOWN_BYTES",
    "MAX_TITLE_CHARS",
    "UPDATE_DOC_TOOL",
    "DriveHTTPClient",
    "DriveHTTPResponse",
    "DriveWriteError",
    "DriveWritePreview",
    "commit_drive_write",
    "drive_write_resource",
    "preview_create_doc",
    "preview_drive_write",
    "preview_update_doc",
]
