# Harness-side Google Drive doc writes

`drive_create_doc(folder_id, title, markdown)` and
`drive_update_doc(doc_id, markdown)` publish Markdown as Google Docs. They
are **agent action tools** gated by `Permission.DRIVE_WRITE`, not Kei
connector capabilities. The owner decided on 2026-10-09 that Drive writes
happen on the harness side: the harness calls the Drive REST API with the
**invoking user's own Google OAuth token**. kei-connector-runtime has no
Drive write capability.

| Piece | Where it lives |
| --- | --- |
| Tool definitions (`DRIVE_WRITE_TOOL_DEFINITIONS`) | `agents.drive_write.tools`, part of `ALL_TOOL_DEFINITIONS` |
| Preview, confirmation digest, authorize resource, request shape | `agents.drive_write` |
| HTTP transport | the harness (`DriveHTTPClient` protocol) |
| User's OAuth access token (`drive.file`) | the harness context; never stored here |
| Allow/deny | kei-proxy `authorize` via agentware, like every other tool |

kei-agents still holds no credentials and has no HTTP dependency. The
harness passes in both the token and the transport.

## Flow

```text
model calls drive_create_doc(folder_id, title, markdown)
  -> harness: agentware policy / KeiProxyEvaluator authorize (tool name;
     resource drive:folder/<folder_id> for audit and resources_touched)
  -> preview_drive_write(...)               # validates args, writes nothing
  -> model gets preview.to_tool_result()    # status: confirmation_required
  -> harness shows the preview; the user confirms it
  -> commit_drive_write(preview, confirmation=preview.digest,
                        access_token=<user token>, http=<harness client>)
```

- **Confirm-required.** A write happens only when `confirmation` equals
  `preview.digest`. The digest covers the tool, the target id, the title,
  and the full Markdown, so any edit needs a new confirmation. The digest
  is never in the model-facing result, so the model cannot confirm its own
  write. This confirmation is harness UX. It is not a policy decision
  (ADR-027 removed per-call approval), and kei-proxy `authorize` stays the
  allow/deny gate.
- **Semantics.** A new doc carries its parent `folder_id`. An update
  carries `doc_id`. The drive, tenant, and token are never arguments; the
  eval cases check this with `forbidden_arg_keys`.
- **Resources.** `drive_write_resource()` returns `drive:folder/<id>` for a
  create and `drive:doc/<id>` for an update.
- **Request.** A create is `POST upload/drive/v3/files?uploadType=multipart`
  with metadata `{"name", "mimeType": "application/vnd.google-apps.document",
  "parents": [folder_id]}` and a `text/markdown` media part, so Drive
  converts the Markdown into a Google Doc. An update is
  `PATCH upload/drive/v3/files/<doc_id>?uploadType=media` with the Markdown.
  Both set `supportsAllDrives=true`.
- **Token hygiene.** The token appears only in the `Authorization` header.
  Results and errors never contain it. A Drive error returns only
  `drive_http_<status>` and Google's message, truncated to 200 characters.
  A transport error returns only the exception type name.
- **Scope.** `drive.file` (`DRIVE_FILE_SCOPE`). With `drive.file`, Google
  may hide a folder that the OAuth client did not create or open, and Drive
  then answers 404 for that `folder_id`. The harness should surface that
  404 rather than retry with a broader scope.

## pydantic-ai harness sketch

```python
from agents.drive_write import commit_drive_write, preview_drive_write

@agent.tool
def drive_create_doc(ctx, folder_id: str, title: str, markdown: str) -> dict:
    preview = preview_drive_write(
        "drive_create_doc",
        {"folder_id": folder_id, "title": title, "markdown": markdown},
    )
    ctx.deps.pending_writes[preview.digest] = preview  # shown to the user
    return preview.to_tool_result()

# Later, when the user clicks "Confirm" on that preview:
result = commit_drive_write(
    preview,
    confirmation=confirmed_digest,
    access_token=deps.user_google_token(),  # the user's own OAuth, drive.file
    http=deps.drive_http,
)
```

Coding harnesses (Claude Code, Codex) use the curl recipe in the
`google-drive-connector` skill instead.

## Evals

`evals/suites/drive_publish.json` (target `drive_publish`) covers:

- a create with `folder_id` present;
- an update that must not create a new doc;
- a find before an update;
- no tool when the folder is missing;
- explaining the confirm step;
- two deny cases (an unconfirmed or read-only write must be denied, and the
  reply must not claim the doc was written).
