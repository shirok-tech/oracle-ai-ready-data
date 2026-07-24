import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "score_oracle_ai_ready_scan.py"
BEFORE = ROOT / "tests" / "fixtures" / "bad_ai_ready_before.out"
AFTER = ROOT / "tests" / "fixtures" / "bad_ai_ready_after.out"

spec = importlib.util.spec_from_file_location("score_ai_ready", str(SCRIPT))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def load_data(path):
    sections = mod.parse_sections(path)
    profile = mod.get_profile(sections.get("run_context", []), None)
    data = mod.calculate(sections, profile)
    mod.enrich_analysis(sections, data)
    return sections, data


class ScoreRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before_sections, cls.before = load_data(BEFORE)
        cls.after_sections, cls.after = load_data(AFTER)

    def test_existing_scores_are_unchanged(self):
        self.assertEqual(mod.score(self.before["overall"]), "0.22")
        self.assertEqual(mod.score(self.after["overall"]), "0.97")
        self.assertFalse(self.before["mandatory_gate_pass"])
        self.assertTrue(self.after["mandatory_gate_pass"])

    def test_comment_quality_before_and_after(self):
        before_quality = self.before["comment_quality"]
        after_quality = self.after["comment_quality"]
        self.assertEqual(before_quality["table_quality_coverage"], 0.0)
        self.assertEqual(before_quality["column_quality_coverage"], 0.0)
        self.assertEqual(after_quality["table_quality_coverage"], 1.0)
        self.assertEqual(after_quality["column_quality_coverage"], 1.0)
        self.assertEqual(after_quality["placeholder_count"], 0)
        self.assertEqual(after_quality["issues"], [])

    def test_semantic_type_candidates_are_precise(self):
        names = {
            "{0}.{1}".format(item["table_name"], item["column_name"])
            for item in self.after["semantic_type_warnings"]
        }
        expected = {
            "CUSTOMER_FEATURES.CHURN_SCORE_TXT",
            "CUSTOMER_FEATURES.LIFETIME_VALUE_TXT",
            "RAW_CUSTOMERS.BIRTHDATE_TXT",
            "RAW_CUSTOMERS.LAST_PURCHASE_AMT",
            "RAW_CUSTOMERS.SIGNUP_WHEN_TXT",
            "RAW_ORDERS.AMOUNT_TXT",
            "RAW_ORDERS.ORDER_TIME_TXT",
            "RAW_ORDER_LINES.DISCOUNT_TXT",
            "RAW_ORDER_LINES.QUANTITY_TXT",
            "RAW_ORDER_LINES.UNIT_PRICE_TXT",
            "SUPPORT_TICKETS.SEVERITY_TXT",
        }
        self.assertEqual(names, expected)
        self.assertNotIn("RAW_CUSTOMERS.COUNTRY_CODE", names)
        self.assertNotIn("RAW_ORDERS.CURRENCY_CODE", names)
        self.assertNotIn("RAW_ORDERS.ORDER_PAYLOAD", names)

    def test_next_actions_are_dynamic(self):
        before_actions = "\n".join(mod.build_next_actions(self.before, "ja"))
        after_actions = "\n".join(mod.build_next_actions(self.after, "ja"))
        self.assertIn("欠落しているテーブルコメント8件", before_actions)
        self.assertIn("主キー未定義8表", before_actions)
        self.assertNotIn("欠落しているテーブルコメント", after_actions)
        self.assertNotIn("主キー未定義", after_actions)
        self.assertNotIn("統計", after_actions)
        self.assertNotIn("鮮度列未定義", after_actions)
        self.assertIn("数値・日付候補11列", after_actions)
        self.assertIn("機微情報候補10列", after_actions)

    def test_html_is_self_contained_and_escaped(self):
        data = dict(self.after)
        quality = dict(self.after["comment_quality"])
        issue = {
            "object_type": "column",
            "owner": "BAD_AI_READY",
            "table_name": "RAW_CUSTOMERS",
            "column_name": "NOTES",
            "comment": "<script>alert('x')</script>",
            "issues": ["placeholder"],
        }
        quality["issues"] = [issue]
        data["comment_quality"] = quality
        sql_text = "-- <unsafe>"
        html = mod.render_html(data, AFTER, sql_text, "ja")
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;unsafe&gt;", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertIn("0.97", html)

    def test_cli_writes_markdown_html_and_sql(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            md = tmp_path / "report.md"
            html = tmp_path / "report.html"
            sql = tmp_path / "improvement.sql"
            rc = mod.main([
                str(AFTER),
                "--profile", "scan",
                "--language", "ja",
                "--output", str(md),
                "--html-output", str(html),
                "--sql-output", str(sql),
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(md.exists())
            self.assertTrue(html.exists())
            self.assertTrue(sql.exists())
            self.assertIn("Comment quality review: **pass**", md.read_text(encoding="utf-8"))
            self.assertIn("<!doctype html>", html.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
