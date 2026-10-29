"""Permission scopes used by agent and workflow metadata."""

from enum import Enum


class Permission(str, Enum):
    """Available permission scopes for tools."""

    SEARCH_WIKI = "search_wiki"
    WEB_SEARCH = "web_search"
    SCHEDULE_MEETINGS = "schedule_meetings"
    GITHUB_READ = "github_read"
    GITHUB_WRITE = "github_write"
    LINEAR_READ = "linear_read"
    LINEAR_WRITE = "linear_write"
    DRIVE_READ = "drive_read"
    DRIVE_WRITE = "drive_write"
    S3_READ = "s3_read"
    HTTP_API_READ = "http_api_read"
    NOTION_READ = "notion_read"
    GMAIL_READ = "gmail_read"
    TITO_READ = "tito_read"
    PROJECT_HOURS_READ = "project_hours_read"
    SEMANTIC_MODEL_READ = "semantic_model_read"
