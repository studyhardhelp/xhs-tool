import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import collect_notes
import xhs_workflow


class CollectionTests(unittest.TestCase):
    def test_comment_collection_stops_at_limit(self):
        page = {
            "namespace": "pc",
            "method": "get_note_out_comment",
            "result": [True, "ok", {"data": {"comments": [
                {"id": "1", "content": "root", "sub_comments": [
                    {"id": "2", "content": "sub1"},
                    {"id": "3", "content": "sub2"},
                ]},
                {"id": "4", "content": "second", "sub_comments": []},
            ], "has_more": True, "cursor": "next"}}],
        }
        with patch.object(collect_notes, "call_xhs", return_value=page) as call:
            _, comments = collect_notes.fetch_comments(
                Path("tool.py"), "https://www.xiaohongshu.com/explore/note?xsec_token=t", "cookie", limit=3
            )
        self.assertEqual(len(comments), 3)
        self.assertEqual(call.call_count, 1)

    def test_note_failure_is_recorded_and_collection_continues(self):
        good = {"namespace": "pc", "method": "get_note_info", "result": [True, "ok", {"id": "2", "title": "ok"}]}
        with patch.object(collect_notes, "call_xhs", side_effect=[RuntimeError("failed"), good]):
            _, _, notes, errors = collect_notes.fetch_note_details(
                Path("tool.py"), [{"id": "1"}, {"id": "2", "xsec_token": "secret"}], "cookie", "pc_search", 2
            )
        self.assertEqual(len(notes), 1)
        self.assertEqual(errors[0]["note_id"], "1")
        self.assertNotIn("xsec_token", notes[0]["url"])

    def test_limits_are_enforced(self):
        with self.assertRaises(ValueError):
            collect_notes.fetch_comments(Path("tool.py"), "https://x/note/1", "cookie", limit=101)

    def test_workflow_respects_max_queries(self):
        search = {"namespace": "pc", "method": "search_some_note", "result": [True, "ok", []]}
        with patch.object(xhs_workflow, "resolve_tool", return_value=Path("tool.py")), \
             patch.object(xhs_workflow, "call_xhs", return_value=search) as call, \
             patch.object(xhs_workflow, "fetch_note_details", return_value=([], [], [], [])):
            queries, _, _, _ = xhs_workflow.collect_workflow_notes(
                "product-review", "防晒", 2, 10, 2, False, 10, None, "cookie"
            )
        self.assertEqual(len(queries), 2)
        self.assertEqual(call.call_count, 2)

    def test_user_note_collection_is_limited(self):
        response = {"namespace": "pc", "method": "get_user_note_info", "result": [True, "ok", {"data": {
            "notes": [{"id": str(index)} for index in range(30)], "has_more": True, "cursor": "next"
        }}]}
        with patch.object(collect_notes, "call_xhs", return_value=response) as call:
            pages, refs = collect_notes.fetch_user_note_refs(
                Path("tool.py"), "https://www.xiaohongshu.com/user/profile/u?xsec_token=t", "cookie", 10
            )
        self.assertEqual(len(pages), 1)
        self.assertEqual(len(refs), 10)
        self.assertEqual(call.call_count, 1)


if __name__ == "__main__":
    unittest.main()
