import os
import sys
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from manage_runs import expired_raw_files


class ManageRunsTests(unittest.TestCase):
    def test_only_expired_raw_files_are_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old_raw = root / "old" / "raw.workflow.json"
            new_raw = root / "new" / "raw.json"
            report = root / "old" / "workflow_report.md"
            old_raw.parent.mkdir()
            new_raw.parent.mkdir()
            old_raw.write_text("{}")
            new_raw.write_text("{}")
            report.write_text("report")
            old_time = time.time() - 40 * 86400
            os.utime(old_raw, (old_time, old_time))
            matched = expired_raw_files(root, 30)
            self.assertEqual(matched, [old_raw.resolve()])


if __name__ == "__main__":
    unittest.main()
