from __future__ import annotations

from pathlib import Path

from ops.local_db.lib.config import GoogleConfig, sanitize_filename

try:
    from google.auth.transport.requests import Request  # type: ignore
    from google.oauth2.credentials import Credentials  # type: ignore
    from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
    from googleapiclient.discovery import build  # type: ignore
except ImportError:  # pragma: no cover - dependency availability depends on local environment
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None


def build_gmail_service(account_email: str, google_config: GoogleConfig):
    return _build_service("gmail", "v1", account_email, google_config)


def build_calendar_service(account_email: str, google_config: GoogleConfig):
    return _build_service("calendar", "v3", account_email, google_config)


def resolve_token_path(base_token_path: Path, account_email: str) -> Path:
    stem = base_token_path.stem
    suffix = base_token_path.suffix or ".json"
    sanitized = sanitize_filename(account_email)
    return base_token_path.with_name(f"{stem}-{sanitized}{suffix}")


def _build_service(api_name: str, version: str, account_email: str, google_config: GoogleConfig):
    if not all((Request, Credentials, InstalledAppFlow, build)):
        raise RuntimeError(
            "Google API dependencies are missing. Install google-auth-oauthlib and google-api-python-client."
        )

    credentials = _load_credentials(account_email, google_config)
    return build(api_name, version, credentials=credentials, cache_discovery=False)


def _load_credentials(account_email: str, google_config: GoogleConfig):
    token_path = resolve_token_path(google_config.token_path, account_email)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    credentials = None

    required_scopes = set(google_config.scopes)

    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(str(token_path), list(google_config.scopes))
        # If the stored token is missing required scopes, discard it and re-auth
        granted = set(credentials.scopes or []) if credentials else set()
        if credentials and not required_scopes.issubset(granted):
            print(f"[auth] Token at {token_path} is missing scopes: {required_scopes - granted}")
            print("[auth] Re-triggering OAuth consent to acquire all scopes.")
            credentials = None

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        token_path.write_text(credentials.to_json(), encoding="utf-8")
        return credentials

    if credentials and credentials.valid:
        return credentials

    flow = InstalledAppFlow.from_client_secrets_file(
        str(google_config.credentials_path),
        list(google_config.scopes),
    )
    credentials = flow.run_local_server(port=0)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    return credentials
