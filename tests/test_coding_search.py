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

    def test_static_audit_reports_unsafe_calls_without_executing_them(self):
        (self.project / "unsafe.py").write_text("value = eval('1 + 1')\n", encoding="utf-8")
        result = coding.audit_python_project("demo")
        self.assertIn("[HIGH]", result)
        self.assertIn("eval()", result)

    def test_static_audit_masks_possible_secret_values(self):
        (self.project / "config.py").write_text('API_TOKEN = "super-secret-value-12345"\n', encoding="utf-8")
        result = coding.audit_python_project("demo")
        self.assertIn("Possible hard-coded credential", result)
        self.assertNotIn("super-secret-value-12345", result)

    def test_static_audit_detects_prefixed_secret_names(self):
        (self.project / "config.py").write_text('STRIPE_SECRET_KEY = "sk_live_123456789012345"\n', encoding="utf-8")
        result = coding.audit_python_project("demo")
        self.assertIn("Possible hard-coded credential", result)
        self.assertNotIn("sk_live_123456789012345", result)

    def test_static_audit_rejects_unsafe_yaml_loader(self):
        (self.project / "unsafe_yaml.py").write_text(
            "import yaml\nyaml.load(data, Loader=yaml.Loader)\n", encoding="utf-8"
        )
        result = coding.audit_python_project("demo")
        self.assertIn("recognized safe Loader", result)

    def test_static_audit_accepts_safe_yaml_loader(self):
        (self.project / "safe_yaml.py").write_text(
            "import yaml\nyaml.load(data, Loader=yaml.SafeLoader)\n", encoding="utf-8"
        )
        result = coding.audit_python_project("demo")
        self.assertNotIn("recognized safe Loader", result)

    def test_static_audit_reports_syntax_errors(self):
        (self.project / "broken.py").write_text("def broken(:\n", encoding="utf-8")
        result = coding.audit_python_project("demo")
        self.assertIn("Python syntax error", result)

    def test_rejects_empty_query(self):
        with self.assertRaises(ValueError):
            coding.search_project("demo", "   ")


if __name__ == "__main__":
    unittest.main()
