import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

class PythonCompatibilityTests(unittest.TestCase):
    def test_supported_python_version(self):
        self.assertGreaterEqual(sys.version_info, (3, 9))

    def test_command_modules_import(self):
        __import__("collect_notes")
        __import__("xhs_auth")
        __import__("xhs_content_chat")
        __import__("xhs_doctor")
        __import__("xhs_report_lib")
        __import__("xhs_workflow")


if __name__ == "__main__":
    unittest.main()
