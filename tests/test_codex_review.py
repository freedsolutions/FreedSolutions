import importlib.util
import json
from pathlib import Path
import shutil
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "codex_review.py"
SPEC = importlib.util.spec_from_file_location("codex_review", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load module spec from {MODULE_PATH}")
codex_review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(codex_review)


VALID_REVIEW = {
    "status": "pass",
    "summary": "Looks good.",
    "safe_to_autofix": False,
    "issue_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
    "issues": [],
    "follow_up_tests": [],
}


class CodexReviewTests(unittest.TestCase):
    def test_extract_review_text_accepts_raw_json(self) -> None:
        review = codex_review.extract_review_text(json.dumps(VALID_REVIEW))
        self.assertEqual(review["status"], "pass")

    def test_extract_review_text_accepts_fenced_json(self) -> None:
        review = codex_review.extract_review_text(f"```json\n{json.dumps(VALID_REVIEW)}\n```")
        self.assertEqual(review["summary"], "Looks good.")

    def test_extract_review_text_accepts_wrapped_json(self) -> None:
        wrapped = f"Review result follows:\n{json.dumps(VALID_REVIEW)}\nDone."
        review = codex_review.extract_review_text(wrapped)
        self.assertEqual(review["issue_counts"]["medium"], 0)

    def test_build_codex_command_wraps_cmd_shim(self) -> None:
        command = codex_review.build_codex_command(
            Path(r"C:\tools\codex.cmd"),
            "",
            Path(r"C:\tmp\last-message.txt"),
        )
        self.assertEqual(command[:4], ["cmd.exe", "/d", "/s", "/c"])
        self.assertIn("codex.cmd", command[4])
        self.assertIn("exec", command[4])

    def test_build_codex_command_wraps_powershell_shim(self) -> None:
        command = codex_review.build_codex_command(
            Path(r"C:\tools\codex.ps1"),
            "gpt-5",
            Path(r"C:\tmp\last-message.txt"),
        )
        self.assertEqual(
            command[:6],
            ["powershell.exe", "-NoLogo", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File"],
        )
        self.assertIn("--model", command)
        self.assertIn("gpt-5", command)

    def test_extract_usage_from_jsonl_parses_token_message(self) -> None:
        stdout = json.dumps({"msg": "tokens used: 5784"}) + "\n"
        self.assertEqual(codex_review.extract_usage_from_jsonl(stdout), {"codex_cli": "5784"})

    def test_resolve_auth_file_errors_when_missing(self) -> None:
        missing = Path(__file__).resolve().parents[1] / ".claude" / "tmp" / "missing-auth.json"
        with self.assertRaises(RuntimeError) as ctx:
            codex_review.resolve_auth_file(str(missing))
        self.assertIn("Run `codex login` first", str(ctx.exception))

    def test_resolve_codex_bin_errors_when_missing(self) -> None:
        with mock.patch.object(codex_review.shutil, "which", return_value=None):
            with mock.patch.object(codex_review, "windows_codex_binary", return_value=None):
                with self.assertRaises(RuntimeError) as ctx:
                    codex_review.resolve_codex_bin("")
        self.assertIn("Could not find the Codex CLI", str(ctx.exception))

    def test_collect_changed_file_blobs_truncates_large_files(self) -> None:
        fixture_root = Path(__file__).resolve().parents[1] / ".claude" / "tmp" / "test-codex-review-fixture"
        if fixture_root.exists():
            shutil.rmtree(fixture_root)
        fixture_root.mkdir(parents=True, exist_ok=True)
        large_file = fixture_root / "large.txt"
        large_file.write_text("A" * 32, encoding="utf-8")

        blobs = codex_review.collect_changed_file_blobs(
            fixture_root,
            [{"status": "??", "path": "large.txt"}],
            {"max_changed_file_chars": 8},
        )
        self.assertTrue(blobs[0]["truncated"])
        self.assertFalse(blobs[0]["included_full_content"])
        self.assertEqual(blobs[0]["skipped_reason"], "truncated_for_budget")

    def test_build_prompt_includes_truncated_changed_file_content(self) -> None:
        prompt = codex_review.build_prompt(
            "review",
            "focus",
            "HEAD",
            [{"status": "??", "path": "large.txt"}],
            [],
            "",
            [
                {
                    "path": "large.txt",
                    "status": "??",
                    "exists": True,
                    "included_full_content": False,
                    "truncated": True,
                    "skipped_reason": "truncated_for_budget",
                    "language": "txt",
                    "content": "ABC\n[TRUNCATED FOR CHANGED FILE BUDGET]",
                }
            ],
        )
        self.assertIn("[CONTENT TRUNCATED FOR BUDGET]", prompt)
        self.assertIn("ABC", prompt)
        self.assertIn("REQUIRED OUTPUT", prompt)


if __name__ == "__main__":
    unittest.main()
