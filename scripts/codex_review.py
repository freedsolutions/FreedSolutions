#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from fnmatch import fnmatch
from typing import Any

DEFAULT_MODEL = ""
DEFAULT_CONFIG_PATH = Path(".claude/skills/codex-review/config.json")
DEFAULT_OUTPUT_PATH = Path(".claude/tmp/codex-review/latest.json")
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

DEFAULT_CONFIG: dict[str, Any] = {
    "include_root_claude": True,
    "include_root_readme": True,
    "include_nearest_claude": True,
    "include_nearest_readme": True,
    "extra_context_files": [],
    "exclude_globs": [
        ".git/**",
        ".playwright-mcp/**",
        "brand/**",
        "node_modules/**",
        "**/__pycache__/**",
        "**/*.pyc",
        "**/*.png",
        "**/*.jpg",
        "**/*.jpeg",
        "**/*.gif",
        "**/*.webp",
        "**/*.pdf",
    ],
    "max_context_file_chars": 24000,
    "max_changed_file_chars": 40000,
    "max_total_chars": 350000,
}

REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "status",
        "summary",
        "safe_to_autofix",
        "issue_counts",
        "issues",
        "follow_up_tests",
    ],
    "properties": {
        "status": {
            "type": "string",
            "enum": ["pass", "fail"],
        },
        "summary": {"type": "string"},
        "safe_to_autofix": {"type": "boolean"},
        "issue_counts": {
            "type": "object",
            "additionalProperties": False,
            "required": ["critical", "high", "medium", "low"],
            "properties": {
                "critical": {"type": "integer"},
                "high": {"type": "integer"},
                "medium": {"type": "integer"},
                "low": {"type": "integer"},
            },
        },
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "severity",
                    "category",
                    "file",
                    "line",
                    "title",
                    "detail",
                    "recommendation",
                ],
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low"],
                    },
                    "category": {
                        "type": "string",
                        "enum": [
                            "bug",
                            "regression",
                            "security",
                            "performance",
                            "maintainability",
                            "test_gap",
                            "other",
                        ],
                    },
                    "file": {"type": "string"},
                    "line": {
                        "anyOf": [
                            {"type": "integer"},
                            {"type": "null"},
                        ]
                    },
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                    "recommendation": {"type": "string"},
                },
            },
        },
        "follow_up_tests": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}

DEVELOPER_PROMPT = """You are Codex performing code review on a local git worktree.

Focus on the highest-signal issues:
- functional bugs
- regressions
- security problems
- incorrect assumptions
- missing or inadequate tests for risky changes

Be conservative. If a possible issue is speculative, either omit it or mark it low severity.

Return pass only when there are no meaningful issues.

Severity guidance:
- critical: data loss, severe security issue, broken core path
- high: likely bug or regression with meaningful user impact
- medium: correctness, maintainability, or coverage issue worth fixing soon
- low: minor issue, edge case, or polish-level review note

The response must satisfy the provided JSON schema exactly.

Return only raw JSON with no markdown fences or commentary.
"""


def main() -> int:
    args = parse_args()
    configure_console_streams()
    repo_root = Path(run_git(["rev-parse", "--show-toplevel"]).strip())
    os.chdir(repo_root)

    config = load_config(repo_root / args.config)
    base_ref = resolve_base_ref()
    status_entries = parse_git_status()
    changed_entries = filter_changed_entries(status_entries, config, args.pathspec)

    if not changed_entries:
        report = {
            "generated_at": now_iso(),
            "mode": args.mode,
            "focus": args.focus,
            "model": args.model or "cli_default",
            "repo_root": str(repo_root),
            "base_ref": base_ref,
            "manifest": {
                "changed_files": [],
                "context_files": [],
                "diff_chars": 0,
                "prompt_chars": 0,
                "estimated_tokens": 0,
                "pathspecs": args.pathspec,
            },
            "review": {
                "status": "pass",
                "summary": "No changed files found in the current git worktree.",
                "safe_to_autofix": False,
                "issue_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "issues": [],
                "follow_up_tests": [],
            },
        }
        write_json(repo_root / args.output, report)
        print_summary(repo_root / args.output, report["review"])
        return 0

    diff_text = get_tracked_diff(base_ref, changed_entries)
    changed_file_blobs = collect_changed_file_blobs(repo_root, changed_entries, config)
    context_blobs = collect_context_blobs(repo_root, changed_entries, config)
    prompt_text = build_prompt(
        args.mode,
        args.focus,
        base_ref,
        changed_entries,
        context_blobs,
        diff_text,
        changed_file_blobs,
    )

    manifest = {
        "changed_files": [
            {
                "path": entry["path"],
                "status": entry["status"],
                "exists": entry["exists"],
                "included_full_content": entry["included_full_content"],
                "truncated": entry["truncated"],
                "skipped_reason": entry["skipped_reason"],
            }
            for entry in changed_file_blobs
        ],
        "context_files": [
            {
                "path": entry["path"],
                "chars": entry["chars"],
                "truncated": entry["truncated"],
            }
            for entry in context_blobs
        ],
        "diff_chars": len(diff_text),
        "prompt_chars": len(prompt_text),
        "estimated_tokens": estimate_tokens(prompt_text),
        "pathspecs": args.pathspec,
    }

    report: dict[str, Any] = {
        "generated_at": now_iso(),
        "mode": args.mode,
        "focus": args.focus,
        "model": args.model or "cli_default",
        "repo_root": str(repo_root),
        "base_ref": base_ref,
        "manifest": manifest,
    }

    max_total_chars = int(config["max_total_chars"])
    if len(prompt_text) > max_total_chars:
        report["error"] = {
            "type": "payload_too_large",
            "message": (
                f"Prompt size {len(prompt_text)} chars exceeds configured limit "
                f"of {max_total_chars} chars. Narrow the review scope or raise "
                "max_total_chars in .claude/skills/codex-review/config.json."
            ),
        }
        write_json(repo_root / args.output, report)
        print(report["error"]["message"], file=sys.stderr)
        return 2

    if args.dry_run:
        report["dry_run"] = True
        write_json(repo_root / args.output, report)
        print(
            f"Dry run OK: {len(changed_entries)} changed files, "
            f"{len(context_blobs)} context files, "
            f"{manifest['estimated_tokens']} est tokens."
        )
        print(f"Report: {repo_root / args.output}")
        return 0

    review_result = run_codex_review(
        args.model,
        prompt_text,
        repo_root,
        args.codex_bin,
        args.auth_file,
    )
    review = review_result["review"]
    report["review"] = review
    report["runner"] = review_result["runner"]
    if review_result.get("usage"):
        report["usage"] = review_result["usage"]
    if review_result.get("codex_cli"):
        report["codex_cli"] = review_result["codex_cli"]
    write_json(repo_root / args.output, report)
    print_summary(repo_root / args.output, review)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a Codex-backed git worktree review.")
    parser.add_argument("--mode", choices=["review", "apply"], default="review")
    parser.add_argument("--focus", default="", help="Optional review focus hint.")
    parser.add_argument("--model", default=os.environ.get("CODEX_REVIEW_MODEL", DEFAULT_MODEL))
    parser.add_argument(
        "--codex-bin",
        default=os.environ.get("CODEX_REVIEW_CODEX_BIN", ""),
        help="Optional path to the Codex CLI executable.",
    )
    parser.add_argument(
        "--auth-file",
        default=os.environ.get("CODEX_REVIEW_AUTH_FILE", ""),
        help="Optional path to a Codex auth.json file.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the codex-review config JSON.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Path to the JSON report artifact.",
    )
    parser.add_argument(
        "--pathspec",
        action="append",
        default=[],
        help="Limit review to repo-relative paths or glob patterns. Repeat for multiple values.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Build the payload without calling the API.")
    return parser.parse_args()


def configure_console_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            continue


def run_git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def resolve_base_ref() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return "HEAD"
    return EMPTY_TREE


def load_config(path: Path) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    if not path.exists():
        return config
    loaded = json.loads(path.read_text(encoding="utf-8"))
    for key, value in loaded.items():
        config[key] = value
    return config


def parse_git_status() -> list[dict[str, str]]:
    raw = run_git(["status", "--porcelain=v1", "--untracked-files=all"])
    entries: list[dict[str, str]] = []
    for line in raw.splitlines():
        if not line:
            continue
        status = line[:2]
        raw_path = line[3:]
        if " -> " in raw_path:
            path = raw_path.split(" -> ", 1)[1]
        else:
            path = raw_path
        entries.append({"status": status, "path": path})
    return entries


def filter_changed_entries(
    entries: list[dict[str, str]],
    config: dict[str, Any],
    pathspecs: list[str],
) -> list[dict[str, str]]:
    filtered: list[dict[str, str]] = []
    for entry in entries:
        status = entry["status"]
        if status == "!!":
            continue
        if is_excluded(entry["path"], config):
            continue
        if not matches_pathspec(entry["path"], pathspecs):
            continue
        filtered.append(entry)
    return filtered


def get_tracked_diff(base_ref: str, changed_entries: list[dict[str, str]]) -> str:
    tracked_paths = [entry["path"] for entry in changed_entries if entry["status"] != "??"]
    if not tracked_paths:
        return ""
    completed = subprocess.run(
        ["git", "diff", "--no-color", "--find-renames=50%", base_ref, "--", *tracked_paths],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def matches_pathspec(path: str, pathspecs: list[str]) -> bool:
    if not pathspecs:
        return True

    normalized_path = path.replace("\\", "/")
    for raw_pathspec in pathspecs:
        normalized_pathspec = raw_pathspec.replace("\\", "/").strip()
        if not normalized_pathspec:
            continue
        if any(char in normalized_pathspec for char in "*?[]"):
            if fnmatch(normalized_path, normalized_pathspec):
                return True
            continue
        normalized_pathspec = normalized_pathspec.rstrip("/")
        if normalized_path == normalized_pathspec:
            return True
        if normalized_path.startswith(f"{normalized_pathspec}/"):
            return True

    return False


def collect_changed_file_blobs(
    repo_root: Path,
    changed_entries: list[dict[str, str]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    max_chars = int(config["max_changed_file_chars"])
    blobs: list[dict[str, Any]] = []
    for entry in changed_entries:
        rel_path = entry["path"]
        path = repo_root / rel_path
        exists = path.exists() and path.is_file()
        included_full_content = False
        truncated = False
        skipped_reason = ""
        content = ""
        if exists:
            maybe_text = read_text_if_reasonable(path)
            if maybe_text is None:
                skipped_reason = "binary_or_unreadable"
            else:
                if len(maybe_text) > max_chars:
                    content = maybe_text[:max_chars] + "\n\n[TRUNCATED FOR CHANGED FILE BUDGET]\n"
                    truncated = True
                    skipped_reason = "truncated_for_budget"
                else:
                    content = maybe_text
                    included_full_content = True
        else:
            skipped_reason = "deleted_or_missing"
        blobs.append(
            {
                "path": rel_path.replace("\\", "/"),
                "status": entry["status"],
                "exists": exists,
                "included_full_content": included_full_content,
                "truncated": truncated,
                "skipped_reason": skipped_reason,
                "language": fence_language(rel_path),
                "content": content,
            }
        )
    return blobs


def collect_context_blobs(
    repo_root: Path,
    changed_entries: list[dict[str, str]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    max_chars = int(config["max_context_file_chars"])
    changed_paths = {entry["path"].replace("\\", "/") for entry in changed_entries}
    candidates: list[Path] = []

    if config.get("include_root_claude") and (repo_root / "CLAUDE.md").exists():
        candidates.append(repo_root / "CLAUDE.md")
    if config.get("include_root_readme") and (repo_root / "README.md").exists():
        candidates.append(repo_root / "README.md")

    for rel_path in changed_paths:
        current = repo_root / rel_path
        parent = current.parent if current.suffix else current
        while True:
            if config.get("include_nearest_claude"):
                candidate = parent / "CLAUDE.md"
                if candidate.exists():
                    candidates.append(candidate)
            if config.get("include_nearest_readme"):
                candidate = parent / "README.md"
                if candidate.exists():
                    candidates.append(candidate)
            if parent == repo_root:
                break
            parent = parent.parent

    for extra in config.get("extra_context_files", []):
        candidate = repo_root / extra
        if candidate.exists():
            candidates.append(candidate)

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        rel = candidate.relative_to(repo_root).as_posix()
        if rel in seen:
            continue
        if rel in changed_paths:
            continue
        if is_excluded(rel, config):
            continue
        seen.add(rel)
        unique.append(candidate)

    blobs: list[dict[str, Any]] = []
    for candidate in unique:
        rel = candidate.relative_to(repo_root).as_posix()
        maybe_text = read_text_if_reasonable(candidate)
        if maybe_text is None:
            continue
        truncated = False
        if len(maybe_text) > max_chars:
            maybe_text = maybe_text[:max_chars] + "\n\n[TRUNCATED FOR CONTEXT BUDGET]\n"
            truncated = True
        blobs.append(
            {
                "path": rel,
                "chars": len(maybe_text),
                "truncated": truncated,
                "language": fence_language(rel),
                "content": maybe_text,
            }
        )
    return blobs


def is_excluded(rel_path: str, config: dict[str, Any]) -> bool:
    rel_path = rel_path.replace("\\", "/")
    for pattern in config.get("exclude_globs", []):
        if fnmatch(rel_path, pattern):
            return True
    return False


def read_text_if_reasonable(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:8192]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


def build_prompt(
    mode: str,
    focus: str,
    base_ref: str,
    changed_entries: list[dict[str, str]],
    context_blobs: list[dict[str, Any]],
    diff_text: str,
    changed_file_blobs: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append("REVIEW REQUEST")
    lines.append(f"Mode: {mode}")
    lines.append(f"Base ref: {base_ref}")
    lines.append(f"Focus: {focus or 'general review'}")
    lines.append("")
    lines.append("REQUIRED OUTPUT")
    lines.append("Return only a JSON object matching this schema:")
    lines.append(json.dumps(REVIEW_SCHEMA, indent=2))
    lines.append("")
    lines.append("CHANGED FILES")
    for entry in changed_entries:
        lines.append(f"- {entry['status']} {entry['path'].replace('\\', '/')}")
    lines.append("")
    lines.append("PROJECT CONTEXT FILES")
    if context_blobs:
        for blob in context_blobs:
            lines.append(f"### {blob['path']}")
            lines.append(f"```{blob['language']}")
            lines.append(blob["content"])
            lines.append("```")
            lines.append("")
    else:
        lines.append("(none)")
        lines.append("")
    lines.append("TRACKED GIT DIFF")
    if diff_text:
        lines.append("```diff")
        lines.append(diff_text)
        lines.append("```")
    else:
        lines.append("(no tracked diff)")
    lines.append("")
    lines.append("FULL CHANGED FILE CONTENTS")
    for blob in changed_file_blobs:
        lines.append(f"### {blob['path']}")
        lines.append(f"Status: {blob['status']}")
        if blob["content"]:
            if blob["truncated"]:
                lines.append("[CONTENT TRUNCATED FOR BUDGET]")
            lines.append(f"```{blob['language']}")
            lines.append(blob["content"])
            lines.append("```")
        else:
            lines.append(f"[CONTENT NOT INCLUDED: {blob['skipped_reason']}]")
        lines.append("")
    return "\n".join(lines)


def run_codex_review(
    model: str,
    prompt_text: str,
    repo_root: Path,
    codex_bin_override: str,
    auth_file_override: str,
) -> dict[str, Any]:
    codex_bin = resolve_codex_bin(codex_bin_override)
    auth_file = resolve_auth_file(auth_file_override)

    with tempfile.TemporaryDirectory(prefix="codex-review-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        temp_codex_home = temp_dir / "home"
        temp_codex_home.mkdir(parents=True, exist_ok=True)
        shutil.copy2(auth_file, temp_codex_home / "auth.json")

        last_message_path = temp_dir / "last-message.txt"
        cmd = build_codex_command(codex_bin, model, last_message_path)

        env = os.environ.copy()
        env["CODEX_HOME"] = str(temp_codex_home)
        completed = subprocess.run(
            cmd,
            input=build_codex_input(prompt_text),
            capture_output=True,
            cwd=repo_root,
            env=env,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(format_codex_failure(completed))

        if not last_message_path.exists():
            raise RuntimeError("Codex CLI completed without writing the last agent message.")

        review = extract_review_text(last_message_path.read_text(encoding="utf-8"))
        result = {
            "runner": "codex_cli_chatgpt_auth",
            "review": review,
            "codex_cli": {
                "binary": str(codex_bin),
                "model": model or "cli_default",
                "auth": "codex_auth_json",
            },
        }
        usage = extract_usage_from_jsonl(completed.stdout)
        if usage:
            result["usage"] = usage
        return result


def resolve_codex_bin(configured: str) -> Path:
    configured = configured.strip()
    if configured:
        path = Path(configured).expanduser()
        if path.exists():
            return path
        raise RuntimeError(f"Configured Codex CLI binary does not exist: {path}")

    seen: set[str] = set()
    for candidate_name in ("codex", "codex.exe", "codex.cmd", "codex.ps1"):
        which = shutil.which(candidate_name)
        if not which or which in seen:
            continue
        seen.add(which)
        return Path(which)

    windows_bin = windows_codex_binary()
    if windows_bin:
        return windows_bin

    raise RuntimeError(
        "Could not find the Codex CLI. Install @openai/codex or set CODEX_REVIEW_CODEX_BIN."
    )


def windows_codex_binary() -> Path | None:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    candidate = (
        Path(appdata)
        / "npm"
        / "node_modules"
        / "@openai"
        / "codex"
        / "bin"
        / "codex-x86_64-pc-windows-msvc.exe"
    )
    if candidate.exists():
        return candidate
    return None


def resolve_auth_file(configured: str) -> Path:
    configured = configured.strip()
    if configured:
        path = Path(configured).expanduser()
    else:
        codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
        path = codex_home / "auth.json"
    if not path.exists():
        raise RuntimeError(
            f"Could not find Codex auth at {path}. Run `codex login` first or set CODEX_REVIEW_AUTH_FILE."
        )
    return path


def build_codex_input(prompt_text: str) -> str:
    return "\n\n".join([DEVELOPER_PROMPT.strip(), prompt_text.strip()]) + "\n"


def build_codex_command(codex_bin: Path, model: str, last_message_path: Path) -> list[str]:
    base_args = [
        "exec",
        "--json",
        "--color",
        "never",
        "--sandbox",
        "read-only",
        "--output-last-message",
        str(last_message_path),
    ]
    if model:
        base_args.extend(["--model", model])
    base_args.append("-")

    suffix = codex_bin.suffix.lower()
    if suffix == ".ps1":
        return [
            "powershell.exe",
            "-NoLogo",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(codex_bin),
            *base_args,
        ]
    if suffix in {".cmd", ".bat"}:
        return ["cmd.exe", "/d", "/s", "/c", subprocess.list2cmdline([str(codex_bin), *base_args])]
    return [str(codex_bin), *base_args]


def format_codex_failure(completed: subprocess.CompletedProcess[str]) -> str:
    sections = [f"Codex CLI failed with exit code {completed.returncode}."]
    stdout = tail_text(completed.stdout)
    stderr = tail_text(completed.stderr)
    if stdout:
        sections.append("stdout:\n" + stdout)
    if stderr:
        sections.append("stderr:\n" + stderr)
    return "\n\n".join(sections)


def tail_text(value: str, max_lines: int = 40) -> str:
    lines = [line for line in value.strip().splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-max_lines:])


def extract_review_text(raw_text: str) -> dict[str, Any]:
    candidates: list[str] = []
    stripped = raw_text.strip()
    if stripped:
        candidates.append(stripped)

    unfenced = strip_code_fence(stripped)
    if unfenced and unfenced not in candidates:
        candidates.append(unfenced)

    braced = extract_braced_json(stripped)
    if braced and braced not in candidates:
        candidates.append(braced)

    for candidate in candidates:
        try:
            review = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        validate_review(review)
        return review

    raise RuntimeError("Codex CLI returned a response that was not valid review JSON.")


def strip_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if len(lines) >= 3 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return text


def extract_braced_json(text: str) -> str:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            _, end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        return text[index : index + end]
    return ""


def extract_usage_from_jsonl(stdout: str) -> dict[str, Any] | None:
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        msg = event.get("msg")
        if isinstance(msg, str) and msg.startswith("tokens used:"):
            return {"codex_cli": msg[len("tokens used:") :].strip()}
    return None


def validate_review(review: dict[str, Any]) -> None:
    if not isinstance(review, dict):
        raise RuntimeError("Review payload must be a JSON object.")

    required = ["status", "summary", "safe_to_autofix", "issue_counts", "issues", "follow_up_tests"]
    for key in required:
        if key not in review:
            raise RuntimeError(f"Review missing required field: {key}")

    if review["status"] not in {"pass", "fail"}:
        raise RuntimeError("Review status must be `pass` or `fail`.")
    if not isinstance(review["summary"], str):
        raise RuntimeError("Review summary must be a string.")
    if not isinstance(review["safe_to_autofix"], bool):
        raise RuntimeError("Review safe_to_autofix must be a boolean.")

    counts = review["issue_counts"]
    if not isinstance(counts, dict):
        raise RuntimeError("Review issue_counts must be an object.")
    for key in ("critical", "high", "medium", "low"):
        value = counts.get(key)
        if not isinstance(value, int):
            raise RuntimeError(f"Review issue_counts.{key} must be an integer.")

    issues = review["issues"]
    if not isinstance(issues, list):
        raise RuntimeError("Review issues must be an array.")
    valid_severities = {"critical", "high", "medium", "low"}
    valid_categories = {
        "bug",
        "regression",
        "security",
        "performance",
        "maintainability",
        "test_gap",
        "other",
    }
    for issue in issues:
        if not isinstance(issue, dict):
            raise RuntimeError("Each review issue must be an object.")
        for key in ("severity", "category", "file", "line", "title", "detail", "recommendation"):
            if key not in issue:
                raise RuntimeError(f"Review issue missing required field: {key}")
        if issue["severity"] not in valid_severities:
            raise RuntimeError(f"Invalid review issue severity: {issue['severity']}")
        if issue["category"] not in valid_categories:
            raise RuntimeError(f"Invalid review issue category: {issue['category']}")
        if not isinstance(issue["file"], str):
            raise RuntimeError("Review issue file must be a string.")
        if issue["line"] is not None and not isinstance(issue["line"], int):
            raise RuntimeError("Review issue line must be an integer or null.")
        for key in ("title", "detail", "recommendation"):
            if not isinstance(issue[key], str):
                raise RuntimeError(f"Review issue {key} must be a string.")

    follow_up_tests = review["follow_up_tests"]
    if not isinstance(follow_up_tests, list):
        raise RuntimeError("Review follow_up_tests must be an array.")
    if not all(isinstance(test, str) for test in follow_up_tests):
        raise RuntimeError("Each follow_up_tests entry must be a string.")


def estimate_tokens(text: str) -> int:
    return int(math.ceil(len(text) / 4))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def print_summary(report_path: Path, review: dict[str, Any]) -> None:
    counts = review["issue_counts"]
    print("CODEX REVIEW")
    print("------------")
    print(f"Report: {report_path}")
    print(f"Status: {review['status'].upper()}")
    print(
        "Issues: "
        f"critical={counts['critical']} "
        f"high={counts['high']} "
        f"medium={counts['medium']} "
        f"low={counts['low']}"
    )
    print(f"Safe to autofix: {'yes' if review['safe_to_autofix'] else 'no'}")
    print(f"Summary: {review['summary']}")
    for issue in review["issues"]:
        line = f":{issue['line']}" if issue["line"] is not None else ""
        print(f"- [{issue['severity']}] {issue['file']}{line} {issue['title']}")
    if review["follow_up_tests"]:
        print("Follow-up tests:")
        for test in review["follow_up_tests"]:
            print(f"- {test}")


def fence_language(path: str) -> str:
    suffix = Path(path).suffix.lower()
    mapping = {
        ".js": "js",
        ".jsx": "jsx",
        ".ts": "ts",
        ".tsx": "tsx",
        ".py": "py",
        ".json": "json",
        ".md": "md",
        ".toml": "toml",
        ".html": "html",
        ".css": "css",
        ".sh": "bash",
        ".ps1": "powershell",
        ".yml": "yaml",
        ".yaml": "yaml",
    }
    return mapping.get(suffix, "")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        raise SystemExit(2)
