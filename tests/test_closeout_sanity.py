import os
import shutil
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "ops" / "notion-workspace" / "scripts" / "test-closeout-sanity.ps1"
FIXTURE_ROOT = REPO_ROOT / "ops" / "notion-workspace" / ".tmp" / "test-closeout-sanity-fixture"
POWERSHELL_BIN = shutil.which("powershell.exe") or shutil.which("powershell")
HAS_CLOSEOUT_SANITY_DEPS = os.name == "nt" and POWERSHELL_BIN is not None and shutil.which("git") is not None


@unittest.skipUnless(HAS_CLOSEOUT_SANITY_DEPS, "requires Windows PowerShell and git")
class CloseoutSanityTests(unittest.TestCase):
    def setUp(self) -> None:
        if FIXTURE_ROOT.exists():
            shutil.rmtree(FIXTURE_ROOT)
        FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if FIXTURE_ROOT.exists():
            shutil.rmtree(FIXTURE_ROOT)

    def run_script(self, fixture_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                POWERSHELL_BIN,
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPT_PATH),
                "-Paths",
                str(fixture_path),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_clean_file_passes_when_scanned_explicitly(self) -> None:
        clean_file = FIXTURE_ROOT / "clean.md"
        clean_file.write_text("# Clean\nThis file is fine.\n", encoding="utf-8")

        completed = self.run_script(clean_file)

        self.assertEqual(completed.returncode, 0)
        self.assertIn("Closeout sanity OK", completed.stdout)
        self.assertNotIn("ops/notion-workspace/freed-solutions-execution-checklist.md", completed.stderr)

    def test_mojibake_file_fails_when_scanned_explicitly(self) -> None:
        bad_file = FIXTURE_ROOT / "bad.md"
        bad_file.write_text("# Bad\nThis line has mojibake: \u00e2\u20ac\u2014\n", encoding="utf-8")

        completed = self.run_script(bad_file)

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Likely mojibake found", completed.stderr)
        self.assertIn("bad.md", completed.stderr)


if __name__ == "__main__":
    unittest.main()
