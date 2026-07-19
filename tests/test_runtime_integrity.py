import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from verify_runtime import verify_runtime


class RuntimeIntegrityTests(unittest.TestCase):
    def test_vendored_runtime_matches_manifest(self):
        self.assertEqual(verify_runtime(), [])


if __name__ == "__main__":
    unittest.main()
