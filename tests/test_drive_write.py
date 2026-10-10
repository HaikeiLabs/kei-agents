"""Tests for the harness-side Drive doc write tools (fake HTTP client only)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import pytest

from agents import (
    ALL_TOOL_DEFINITIONS,
    DRIVE_WRITE_TOOL_DEFINITIONS,
    Permission,
    ToolCategory,
    validate_tool_definitions,
)
from agents.drive_write import (
    DRIVE_FILE_SCOPE,
    GOOGLE_DOC_MIME_TYPE,
    MAX_MARKDOWN_BYTES,
    DriveHTTPResponse,
    DriveWriteError,
    commit_drive_write,
    drive_write_resource,
    preview_create_doc,
    preview_drive_write,
    preview_update_doc,
)

FOLDER = "1FolderAbCdEfGh0123"
DOC = "1DocQrStUvWxYz4567"
TOKEN = "ya29.user-oauth-token-never-logged"
MARKDOWN = "# Guide\n\nHello **Drive**.\n"
DELEGATED = {"tenant_id", "drive_id", "workspace", "access_token", "token"}


@dataclass
class FakeHTTP:
    """Records requests and replies with a canned response."""

    response: DriveHTTPResponse = field(
        default_factory=lambda: DriveHTTPResponse(
            200,
            json.dumps(
                {"id": "1NewDoc000000", "name": "Guide", "webViewLink": "doc-link"}
            ).encode(),
        )
    )
    raises: Exception | None = None
    calls: list[tuple[str, str, dict[str, str], bytes]] = field(default_factory=list)

    def send(
        self, method: str, url: str, headers: Mapping[str, str], body: bytes
    ) -> DriveHTTPResponse:
        self.calls.append((method, url, dict(headers), body))
        if self.raises is not None:
            raise self.raises
        return self.response


def _commit(preview: Any, http: FakeHTTP, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("confirmation", preview.digest)
    kwargs.setdefault("access_token", TOKEN)
    return commit_drive_write(preview, http=http, **kwargs)


class TestToolDefinitions:
    def test_registered_and_valid(self) -> None:
        names = {t.name for t in ALL_TOOL_DEFINITIONS}
        assert {"drive_create_doc", "drive_update_doc"} <= names
        assert validate_tool_definitions(ALL_TOOL_DEFINITIONS) == []

    @pytest.mark.parametrize("tool", DRIVE_WRITE_TOOL_DEFINITIONS, ids=lambda t: t.name)
    def test_action_tool_not_connector_capability(self, tool: Any) -> None:
        assert tool.permission is Permission.DRIVE_WRITE
        assert tool.category is ToolCategory.DRIVE
        assert tool.service == "drive"
        assert tool.binding is None and tool.handler is None
        assert "confirm-required" in tool.tags
        assert not DELEGATED & {p.name for p in tool.parameters}

    def test_create_carries_parent_folder(self) -> None:
        params = {p.name: p for p in DRIVE_WRITE_TOOL_DEFINITIONS[0].parameters}
        assert params["folder_id"].required
        assert params["title"].required and params["markdown"].required

    def test_update_targets_doc(self) -> None:
        params = {p.name: p for p in DRIVE_WRITE_TOOL_DEFINITIONS[1].parameters}
        assert set(params) == {"doc_id", "markdown"}
        assert all(p.required for p in params.values())


class TestPreview:
    def test_create_preview_writes_nothing(self) -> None:
        preview = preview_create_doc(FOLDER, " Guide ", MARKDOWN)
        result = preview.to_tool_result()
        assert result["status"] == "confirmation_required"
        assert result["resource"] == f"drive:folder/{FOLDER}"
        assert result["folder_id"] == FOLDER and result["title"] == "Guide"
        assert result["markdown_chars"] == len(MARKDOWN)
        # The confirmation digest is for the harness, never the model.
        assert preview.digest and preview.digest not in json.dumps(result)

    def test_update_preview(self) -> None:
        result = preview_update_doc(DOC, MARKDOWN).to_tool_result()
        assert result["resource"] == f"drive:doc/{DOC}"
        assert result["doc_id"] == DOC and "title" not in result

    def test_excerpt_is_bounded(self) -> None:
        result = preview_update_doc(DOC, "x" * 5000).to_tool_result()
        assert len(result["markdown_excerpt"]) == 1200
        assert result["markdown_chars"] == 5000

    def test_dispatch_by_tool_name(self) -> None:
        create = preview_drive_write(
            "drive_create_doc",
            {"folder_id": FOLDER, "title": "Guide", "markdown": MARKDOWN},
        )
        assert create == preview_create_doc(FOLDER, "Guide", MARKDOWN)
        update = preview_drive_write("drive_update_doc", {"doc_id": DOC, "markdown": MARKDOWN})
        assert update.digest == preview_update_doc(DOC, MARKDOWN).digest

    def test_digest_binds_content(self) -> None:
        a = preview_create_doc(FOLDER, "Guide", MARKDOWN)
        assert a.digest != preview_create_doc(FOLDER, "Guide", MARKDOWN + "!").digest
        assert a.digest != preview_create_doc(FOLDER, "Other", MARKDOWN).digest
        assert a.digest != preview_create_doc("1OtherFolder00", "Guide", MARKDOWN).digest

    @pytest.mark.parametrize(
        ("tool", "args", "message"),
        [
            ("drive_create_doc", {"title": "T", "markdown": "m"}, "folder_id"),
            ("drive_create_doc", {"folder_id": "../etc", "title": "T", "markdown": "m"}, "folder_id"),
            ("drive_create_doc", {"folder_id": FOLDER, "title": " ", "markdown": "m"}, "title"),
            ("drive_create_doc", {"folder_id": FOLDER, "title": "x" * 257, "markdown": "m"}, "title"),
            ("drive_create_doc", {"folder_id": FOLDER, "title": "T", "markdown": ""}, "markdown"),
            ("drive_update_doc", {"doc_id": "a/b?c=d", "markdown": "m"}, "doc_id"),
            ("drive_update_doc", {"doc_id": DOC, "markdown": "x" * (MAX_MARKDOWN_BYTES + 1)}, "markdown"),
            ("drive_delete_doc", {"doc_id": DOC}, "not a Drive write tool"),
        ],
    )
    def test_rejects_bad_args(self, tool: str, args: dict[str, Any], message: str) -> None:
        with pytest.raises(DriveWriteError, match=message):
            preview_drive_write(tool, args)

    def test_authorize_resource(self) -> None:
        assert drive_write_resource("drive_create_doc", {"folder_id": FOLDER}) == (
            f"drive:folder/{FOLDER}"
        )
        assert drive_write_resource("drive_update_doc", {"doc_id": DOC}) == f"drive:doc/{DOC}"
        with pytest.raises(DriveWriteError):
            drive_write_resource("drive_create_doc", {})


class TestCommit:
    def test_create_after_confirmation(self) -> None:
        http = FakeHTTP()
        preview = preview_create_doc(FOLDER, "Guide", MARKDOWN)
        result = _commit(preview, http)
        assert result == {
            "tool": "drive_create_doc",
            "resource": f"drive:folder/{FOLDER}",
            "status": "created",
            "doc_id": "1NewDoc000000",
            "title": "Guide",
            "url": "doc-link",
        }
        [(method, url, headers, body)] = http.calls
        assert method == "POST"
        assert url.startswith("https://www.googleapis.com/upload/drive/v3/files?")
        assert "uploadType=multipart" in url and "supportsAllDrives=true" in url
        assert headers["Authorization"] == f"Bearer {TOKEN}"
        boundary = headers["Content-Type"].split("boundary=")[1]
        assert headers["Content-Type"].startswith("multipart/related")
        text = body.decode()
        metadata = json.loads(text.split("\r\n\r\n")[1].split("\r\n")[0])
        assert metadata == {
            "mimeType": GOOGLE_DOC_MIME_TYPE,
            "name": "Guide",
            "parents": [FOLDER],
        }
        assert "Content-Type: text/markdown" in text and MARKDOWN in text
        assert text.endswith(f"--{boundary}--\r\n")
        # The token goes in the header only, never the body.
        assert TOKEN not in text

    def test_update_after_confirmation(self) -> None:
        http = FakeHTTP(DriveHTTPResponse(200, json.dumps({"id": DOC, "name": "Guide"}).encode()))
        result = _commit(preview_update_doc(DOC, MARKDOWN), http)
        assert result["status"] == "updated" and result["doc_id"] == DOC
        [(method, url, headers, body)] = http.calls
        assert method == "PATCH"
        assert f"/upload/drive/v3/files/{DOC}?uploadType=media" in url
        assert headers["Content-Type"].startswith("text/markdown")
        assert body == MARKDOWN.encode()

    @pytest.mark.parametrize("confirmation", [None, "", "yes", "0" * 64])
    def test_no_write_without_confirmation(self, confirmation: str | None) -> None:
        http = FakeHTTP()
        result = _commit(preview_create_doc(FOLDER, "Guide", MARKDOWN), http, confirmation=confirmation)
        assert result["status"] == "not_confirmed"
        assert http.calls == []

    def test_confirmation_is_for_the_exact_preview(self) -> None:
        http = FakeHTTP()
        confirmed = preview_create_doc(FOLDER, "Guide", MARKDOWN)
        changed = preview_create_doc(FOLDER, "Guide", MARKDOWN + "edited")
        assert _commit(changed, http, confirmation=confirmed.digest)["status"] == "not_confirmed"
        assert http.calls == []

    def test_missing_token(self) -> None:
        http = FakeHTTP()
        result = _commit(preview_update_doc(DOC, MARKDOWN), http, access_token="")
        assert result["error"] == "missing_user_token" and http.calls == []

    def test_drive_error_is_bounded_and_token_free(self) -> None:
        body = json.dumps({"error": {"code": 404, "message": "File not found: x" * 50}}).encode()
        http = FakeHTTP(DriveHTTPResponse(404, body))
        result = _commit(preview_create_doc(FOLDER, "Guide", MARKDOWN), http)
        assert result["status"] == "error" and result["error"] == "drive_http_404"
        assert len(result["message"]) == 200
        assert TOKEN not in json.dumps(result)

    def test_transport_error_never_leaks(self) -> None:
        http = FakeHTTP(raises=RuntimeError(f"connect failed, Authorization: Bearer {TOKEN}"))
        result = _commit(preview_update_doc(DOC, MARKDOWN), http)
        assert result["error"] == "transport_error" and result["detail"] == "RuntimeError"
        assert TOKEN not in json.dumps(result)

    def test_repr_hides_content_and_digest(self) -> None:
        preview = preview_create_doc(FOLDER, "Guide", MARKDOWN)
        assert MARKDOWN not in repr(preview) and preview.digest not in repr(preview)

    def test_boundary_never_collides_with_content(self) -> None:
        first = preview_create_doc(FOLDER, "Guide", MARKDOWN)
        collide = f"kei-agents-{first.digest[:32]}"
        # A body that happens to contain the short boundary still parses.
        preview = preview_create_doc(FOLDER, "Guide", MARKDOWN)
        object.__setattr__(preview, "markdown", collide)
        http = FakeHTTP()
        _commit(preview, http)
        boundary = http.calls[0][2]["Content-Type"].split("boundary=")[1]
        assert boundary != collide


def test_scope_is_drive_file() -> None:
    assert DRIVE_FILE_SCOPE.endswith("/auth/drive.file")
