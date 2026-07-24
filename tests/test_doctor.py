import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from xhs_doctor import CheckResult, build_diagnostics, print_text_report


class DoctorTests(unittest.TestCase):
    def test_diagnostics_payload_has_expected_shape(self):
        checks = [
            CheckResult("python", "ok", "Python ok"),
            CheckResult("auth", "warn", "Local auth exists", "Run login"),
        ]
        with patch("xhs_doctor.check_python", return_value=checks[0]), \
            patch("xhs_doctor.check_node", return_value=CheckResult("node", "ok", "node ok")), \
            patch("xhs_doctor.check_npm", return_value=CheckResult("npm", "ok", "npm ok")), \
            patch("xhs_doctor.check_python_modules", return_value=CheckResult("python-deps", "ok", "deps ok")), \
            patch("xhs_doctor.check_node_modules", return_value=CheckResult("node-deps", "ok", "node deps ok")), \
            patch("xhs_doctor.check_runtime_manifest", return_value=CheckResult("runtime", "ok", "runtime ok")), \
            patch("xhs_doctor.check_browser", return_value=CheckResult("browser", "ok", "browser ok")), \
            patch("xhs_doctor.check_auth", return_value=checks[1]), \
            patch("xhs_doctor.check_token_platform", return_value=CheckResult("token-platform", "warn", "missing env")), \
            patch("xhs_doctor.check_runs_dir", return_value=CheckResult("runs-dir", "ok", "runs ok")):
            payload = build_diagnostics()
        self.assertEqual(payload["overall"], "warn")
        self.assertEqual(payload["counts"]["fail"], 0)
        self.assertEqual(len(payload["checks"]), 10)

    def test_text_report_does_not_print_cookie_values(self):
        payload = {
            "overall": "warn",
            "skill_dir": "/tmp/xhs-tool",
            "platform": "test",
            "checks": [
                {
                    "name": "auth",
                    "status": "warn",
                    "message": "Local XHS cookies have the required names.",
                    "remediation": "Run login",
                }
            ],
        }
        stream = io.StringIO()
        with patch("sys.stdout", stream):
            print_text_report(payload)
        output = stream.getvalue()
        self.assertIn("[WARN] auth", output)
        self.assertNotIn("web_session=", output)
        self.assertNotIn("a1=", output)

    def test_json_payload_can_be_serialized(self):
        with patch("xhs_doctor.check_python", return_value=CheckResult("python", "ok", "Python ok")), \
            patch("xhs_doctor.check_node", return_value=CheckResult("node", "ok", "node ok")), \
            patch("xhs_doctor.check_npm", return_value=CheckResult("npm", "ok", "npm ok")), \
            patch("xhs_doctor.check_python_modules", return_value=CheckResult("python-deps", "ok", "deps ok")), \
            patch("xhs_doctor.check_node_modules", return_value=CheckResult("node-deps", "ok", "node deps ok")), \
            patch("xhs_doctor.check_runtime_manifest", return_value=CheckResult("runtime", "ok", "runtime ok")), \
            patch("xhs_doctor.check_browser", return_value=CheckResult("browser", "ok", "browser ok")), \
            patch("xhs_doctor.check_auth", return_value=CheckResult("auth", "ok", "auth ok")), \
            patch("xhs_doctor.check_token_platform", return_value=CheckResult("token-platform", "ok", "token ok")), \
            patch("xhs_doctor.check_runs_dir", return_value=CheckResult("runs-dir", "ok", "runs ok")):
            payload = build_diagnostics()
        encoded = json.dumps(payload, ensure_ascii=False)
        self.assertIn('"overall": "ok"', encoded)


if __name__ == "__main__":
    unittest.main()
