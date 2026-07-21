import io
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import collect_notes
import xhs_api_tool
import xhs_auth
from xhs_security import sanitize_raw_data, write_private_text


class SecurityTests(unittest.TestCase):
    def test_call_uses_stdin_instead_of_process_arguments(self):
        response = {"namespace": "pc", "method": "get_user_self_info2", "result": [True, "ok", {}]}
        completed = subprocess.CompletedProcess([], 0, stdout=json.dumps(response), stderr="")
        with patch.object(collect_notes.subprocess, "run", return_value=completed) as run:
            collect_notes.call_xhs(Path("tool.py"), "pc", "get_user_self_info2", {"cookies_str": "secret"}, retries=0)
        command = run.call_args.args[0]
        self.assertNotIn("secret", " ".join(command))
        self.assertIn("--params-stdin", command)
        self.assertIn("secret", run.call_args.kwargs["input"])

    def test_inline_secret_payload_is_rejected(self):
        with self.assertRaises(ValueError):
            xhs_api_tool._read_json_arg('{"cookies_str":"secret"}', None)
        with self.assertRaises(ValueError):
            xhs_api_tool._read_json_arg('{"xsec_token":"secret"}', None)
        with patch.object(sys, "stdin", io.StringIO('{"cookies_str":"secret"}')):
            self.assertEqual(xhs_api_tool._read_json_arg(None, None, True)["cookies_str"], "secret")

    def test_params_file_requires_private_mode(self):
        if sys.platform == "win32":
            self.skipTest("POSIX mode check")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "params.json"
            path.write_text('{"query":"safe"}')
            path.chmod(0o644)
            with self.assertRaises(PermissionError):
                xhs_api_tool._read_json_arg(None, str(path))
            path.chmod(0o600)
            self.assertEqual(xhs_api_tool._read_json_arg(None, str(path))["query"], "safe")

    def test_research_api_allowlist_excludes_mutating_methods(self):
        self.assertNotIn("creator", xhs_api_tool.ALLOWED_METHODS)
        self.assertNotIn("post_note", xhs_api_tool.ALLOWED_METHODS["pc"])
        self.assertNotIn("get_note_no_water_video", xhs_api_tool.ALLOWED_METHODS["pc"])
        self.assertNotIn("get_user_all_notes", xhs_api_tool.ALLOWED_METHODS["pc"])

    def test_low_level_count_and_proxy_limits_are_enforced(self):
        with self.assertRaises(ValueError):
            xhs_api_tool._validate_method_payload("search_some_note", {"require_num": 51})
        with self.assertRaises(PermissionError):
            xhs_api_tool._validate_method_payload("search_some_note", {"require_num": 1, "proxies": {"https": "proxy"}})

    def test_cookie_names_alone_are_not_reported_as_verified(self):
        status = xhs_auth.auth_status_from_cookie("a1=a; web_session=s; webId=w")
        self.assertTrue(status["structural_usable"])
        self.assertFalse(status["usable"])
        self.assertFalse(status["verified"])

    def test_raw_sanitization_and_private_file_mode(self):
        sanitized = sanitize_raw_data({"cookies_str": "secret", "url": "https://x.test?n=1&xsec_token=abc", "title": "safe"})
        self.assertEqual(sanitized["cookies_str"], "[redacted]")
        self.assertNotIn("abc", sanitized["url"])
        with tempfile.TemporaryDirectory() as directory:
            path = write_private_text(Path(directory) / "report.md", "safe")
            mode = stat.S_IMODE(path.stat().st_mode)
            self.assertEqual(mode, 0o600)


if __name__ == "__main__":
    unittest.main()
