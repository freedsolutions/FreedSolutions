#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from fnmatch import fnmatch
from typing import Any
from urllib import error, request

API_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5.2-codex"
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
"""


def main() -> int:
    args = parse_args()
    repo_root = Path(run_git(["rev-parse", "--show-toplevel"]).strip())
    os.chdir(repo_root)

    config = load_config(repo_root / args.config)
    base_ref = resolve_base_ref()
    status_entries = parse_git_status()
    changed_entries = filter_changed_entries(status_entries, config)

    if not changed_entries:
        report = {
            "generated_at": now_iso(),
            "mode": args.mode,
            "focus": args.focus,
            "model": args.model,
            "repo_root": str(repo_root),
            "base_ref": base_ref,
            "manifest": {
                "changed_files": [],
                "context_files": [],
                "diff_chars": 0,
                "prompt_chars": 0,
                "estimated_tokens": 0,
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

    diff_text = get_tracked_diff(base_ref)
    changed_file_blobs = collect_changed_file_blobs(repo_root, changed_entries)
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
    }

    report: dict[str, Any] = {
        "generated_at": now_iso(),
        "mode": args.mode,
        "focus": args.focus,
        "model": args.model,
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

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Missing OPENAI_API_KEY.", file=sys.stderr)
        return 2

    response_json = call_openai(api_key, args.model, prompt_text, repo_root.name)
    review = extract_review(response_json)
    report["review"] = review
    report["usage"] = response_json.get("usage", {})
    report["response_id"] = response_json.get("id")
    write_json(repo_root / args.output, report)
    print_summary(repo_root / args.output, review)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a Codex-backed git worktree review.")
    parser.add_argument("--mode", choices=["review", "apply"], default="review")
    parser.add_argument("--focus", default="", help="Optional review focus hint.")
    parser.add_argument("--model", default=os.environ.get("CODEX_REVIEW_MODEL", DEFAULT_MODEL))
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
    parser.add_argument("--dry-run", action="store_true", help="Build the payload without calling the API.")
    return parser.parse_args()


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
) -> list[dict[str, str]]:
    filtered: list[dict[str, str]] = []
    for entry in entries:
        status = entry["status"]
        if status == "!!":
            continue
        if is_excluded(entry["path"], config):
            continue
        filtered.append(entry)
    return filtered


def get_tracked_diff(base_ref: str) -> str:
    completed = subprocess.run(
        ["git", "diff", "--no-color", "--find-renames=50%", base_ref],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def collect_changed_file_blobs(
    repo_root: Path,
    changed_entries: list[dict[str, str]],
) -> list[dict[str, Any]]:
    blobs: list[dict[str, Any]] = []
    for entry in changed_entries:
        rel_path = entry["path"]
        path = repo_root / rel_path
        exists = path.exists() and path.is_file()
        included_full_content = False
        skipped_reason = ""
        content = ""
        if exists:
            maybe_text = read_text_if_reasonable(path)
            if maybe_text is None:
                skipped_reason = "binary_or_unreadable"
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
        if blob["included_full_content"]:
            lines.append(f"```{blob['language']}")
            lines.append(blob["content"])
            lines.append("```")
        else:
            lines.append(f"[CONTENT NOT INCLUDED: {blob['skipped_reason']}]")
        lines.append("")
    return "\n".join(lines)


def call_openai(api_key: str, model: str, prompt_text: str, repo_name: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "reasoning": {"effort": "medium"},
        "prompt_cache_key": f"codex-review:{repo_name}:v1",
        "text": {
            "format": {
                "type": "json_schema",
                "name": "codex_review_report",
                "strict": True,
                "schema": REVIEW_SCHEMA,
            }
        },
        "input": [
            {
                "role": "developer",
                "content": [{"type": "input_text", "text": DEVELOPER_PROMPT}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt_text}],
            },
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error {exc.code}: {details}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc}") from exc


def extract_review(response_json: dict[str, Any]) -> dict[str, Any]:
    if "error" in response_json:
        raise RuntimeError(json.dumps(response_json["error"], indent=2))
    text = response_json.get("output_text")
    if not text:
        parts: list[str] = []
        for item in response_json.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    parts.append(content.get("text", ""))
                if content.get("type") == "refusal":
                    raise RuntimeError(f"Model refusal: {content.get('refusal', '')}")
        text = "\n".join(part for part in parts if part)
    if not text:
        raise RuntimeError("No output_text found in the OpenAI response.")
    review = json.loads(text)
    validate_review(review)
    return review


def validate_review(review: dict[str, Any]) -> None:
    required = ["status", "summary", "safe_to_autofix", "issue_counts", "issues", "follow_up_tests"]
    for key in required:
        if key not in review:
            raise RuntimeError(f"Review missing required field: {key}")


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
