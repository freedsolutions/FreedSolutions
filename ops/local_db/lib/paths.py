from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
OPS_ROOT = PACKAGE_ROOT.parent
REPO_ROOT = OPS_ROOT.parent
RUNTIME_ROOT = OPS_ROOT / "local_db"
DEFAULT_CONFIG_PATH = RUNTIME_ROOT / "config.yaml"
DEFAULT_SCHEMA_PATH = RUNTIME_ROOT / "schema.sql"
