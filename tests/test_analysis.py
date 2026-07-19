import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from xhs_report_lib import parse_publish_datetime, tokenize_chinese_and_ascii
from xhs_workflow import build_workflow_report, evidence_quality, expand_queries, infer_workflow, parse_trip_days


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.note = {
            "note_id": "1",
            "url": "https://www.xiaohongshu.com/explore/1",
            "title": "上海亲子两日游避坑路线",
            "desc": "酒店住宿方便，但是周末排队很久。美食预算每人200元。",
            "author": "作者A",
            "author_id": "a",
            "publish_time": "2026-07-01",
            "liked_count": 1200,
            "collected_count": 800,
            "comment_count": 100,
            "share_count": 20,
            "tags": ["亲子游"],
            "images": ["https://img"],
            "comments": [],
        }
        self.comment = {"content": "路线很实用，酒店价格有点贵，怎么避开排队？", "like_count": 20, "note_url": self.note["url"]}

    def test_chinese_tokenization_does_not_return_entire_sentence(self):
        tokens = tokenize_chinese_and_ascii(self.comment["content"])
        self.assertIn("路线", tokens)
        self.assertIn("酒店", tokens)
        self.assertNotIn(self.comment["content"], tokens)

    def test_travel_report_uses_requested_days_and_evidence(self):
        report = build_workflow_report("travel-plan", "上海亲子两日游", ["上海亲子两日游"], [self.note], [self.comment])
        self.assertEqual(parse_trip_days("上海亲子两日游"), 2)
        self.assertIn("## 2日行程骨架", report)
        self.assertNotIn("## 5日行程骨架", report)
        self.assertIn("路线很实用", report)

    def test_evidence_quality_reports_diversity_and_warnings(self):
        quality = evidence_quality([self.note], [self.comment])
        self.assertEqual(quality["level"], "low")
        self.assertEqual(quality["content_diversity"], 1.0)
        self.assertTrue(quality["warnings"])

    def test_unknown_topic_uses_general_research(self):
        self.assertEqual(infer_workflow("咖啡豆风味记录"), "general-research")

    def test_two_day_trip_queries_do_not_add_five_day_trip(self):
        queries = expand_queries("travel-plan", "上海亲子两日游", 8)
        self.assertFalse(any("5日游" in query for query in queries))

    def test_short_numeric_publish_value_is_not_a_timestamp(self):
        self.assertIsNone(parse_publish_datetime("2026"))


if __name__ == "__main__":
    unittest.main()
