from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from jarvis import coding


class ProjectSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous_workspace = os.environ.get("JARVIS_WORKSPACE")
        os.environ["JARVIS_WORKSPACE"] = self.temp.name
        self.project = Path(self.temp.name) / "demo"
        self.project.mkdir()

    def tearDown(self):
        if self.previous_workspace is None:
            os.environ.pop("JARVIS_WORKSPACE", None)
        else:
            os.environ["JARVIS_WORKSPACE"] = self.previous_workspace
        self.temp.cleanup()

    def test_finds_case_insensitive_symbol_with_line_number(self):
        (self.project / "src").mkdir()
        (self.project / "src" / "main.py").write_text("def Target_Symbol():\n    return 7\n", encoding="utf-8")
        result = coding.search_project("demo", "target_symbol")
        self.assertIn("src/main.py:1", result)
        self.assertIn("def Target_Symbol()", result)

    def test_does_not_search_secret_environment_files(self):
        (self.project / ".env").write_text("API_SECRET=do-not-show", encoding="utf-8")
        result = coding.search_project("demo", "do-not-show")
        self.assertIn("No matches found", result)
        self.assertNotIn("API_SECRET", result)

    def test_rejects_empty_query(self):
        with self.assertRaises(ValueError):
            coding.search_project("demo", "   ")


if __name__ == "__main__":
    unittest.main()
