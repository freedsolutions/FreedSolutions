"""Thin, reusable wrapper around the TypeSafe (Jev) System One API.

Ground truth for this module is the installed SDK, not third-party docs:
  base URL   https://api.typesafe.ai      (typesafe_sdk.constants.DEFAULT_BASE_URL)
  path       POST /v1/systemone           (typesafe_sdk._core.constants.SYSTEM_ONE_PATH)
  auth       Authorization: Bearer <key>
  env        TYPESAFE_API_KEY
  model      jev-latest

Do NOT send the key anywhere else. Several third-party "Jev API" sites
instruct you to POST your TYPESAFE_API_KEY to an unrelated host. That is not
the vendor endpoint.

Answer shapes (from typesafe_sdk._schemas.models):
  Choice -> .choice (str), .confidence (0-1), .probabilities {label: p}
  Noul   -> .noul (0-1 probability of yes); NO confidence field
  Score  -> .score (float, may fall between levels), .confidence, .legend,
            .probabilities keyed by int level
"""

from __future__ import annotations

import os
from pathlib import Path

from typesafe_sdk import TypeSafeClient

SECRETS_FILE = Path.home() / ".secrets" / "typesafe.env"


def load_api_key() -> str:
    """Return the API key from the environment, falling back to ~/.secrets/typesafe.env.

    The secrets file is a plain KEY=VALUE file kept outside the repo so it can
    never be committed. The environment always wins.
    """
    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if key:
        return key
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            if name.strip() == "TYPESAFE_API_KEY":
                return value.strip().strip("'\"")
    raise SystemExit(
        f"No TYPESAFE_API_KEY. Set the env var, or write it to {SECRETS_FILE} as\n"
        "  TYPESAFE_API_KEY=<key>"
    )


def client(**kwargs) -> TypeSafeClient:
    """A TypeSafeClient authenticated from the environment or the secrets file."""
    kwargs.setdefault("api_key", load_api_key())
    return TypeSafeClient(**kwargs)


def redact(key: str) -> str:
    """A safe-to-log fingerprint of a key: never print the key itself."""
    return f"{key[:3]}...{key[-4:]} (len {len(key)})" if len(key) > 8 else "(too short)"
