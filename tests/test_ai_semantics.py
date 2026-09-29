"""Offline semantics regression tests.

Only observed_minimal.json is transcribed from user-provided observations.
All other records below are synthetic boundary cases. No test connects to a
database or invokes an external model.
"""

import contextlib
import copy
import html
import importlib.util
import io
import json
import re
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
OBSERVED = FIXTURES / "ai_semantics" / "observed_minimal.json"


def import_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, str(ROOT / "scripts" / filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = import_script("score_semantics_regression", "score_oracle_ai_ready_scan.py")
generator = import_script("setup_semantics_regression", "generate_select_ai_setup.py")


def inventory(tables=(("OWNER_A", "ORDERS"),)):
    """Synthetic three-column inventory, deliberately without COMMENTs."""
    return {
        "table_inventory": [{"OWNER": owner, "TABLE_NAME": table} for owner, table in tables],
        "column_inventory": [
            {"OWNER": owner, "TABLE_NAME": table, "COLUMN_NAME": column, "DATA_TYPE": "VARCHAR2"}
            for owner, table in tables for column in ("C01", "C02", "C03")
        ],
    }


def synthetic_payload(tables=(("OWNER_A", "ORDERS"),), records=(), states=None):
    """Explicitly synthetic collector payload for boundary-condition tests."""
    rows = [{"type": "context", "session_user": "READER", "current_schema": "READER",
             "target_owner": tables[0][0] if tables else "OWNER_A", "table_like_pattern": "%"}]
    for owner, table in tables:
        rows.append({"type": "table", "owner": owner, "table_name": table})
        rows.extend({"type": "column", "owner": owner, "table_name": table, "column_name": column}
                    for column in ("C01", "C02", "C03"))
    rows.extend(copy.deepcopy(records))
    states = states or {}
    rows.extend({"type": "status", "component": component,
                 "state": states.get(component, "collected"), "diagnostic": "synthetic diagnostic"}
                for component in ("scope", "annotations", "domains"))
    return {"format": "oracle-ai-semantics-v1", "records": rows}


def annotation(column="C03", owner="OWNER_A", table="ORDERS", name="DESCRIPTION", value="Order status", **extra):
    row = {"type": "annotation", "owner": owner, "object_name": table,
           "object_type": "TABLE", "column_name": column, "annotation_name": name,
           "annotation_value": value, "domain_owner": None, "domain_name": None}
    row.update(extra)
    return row


def domain(owner="OWNER_A", table="ORDERS", column="C03"):
    return {"type": "domain", "owner": owner, "table_name": table, "column_name": column,
            "domain_owner": owner, "domain_name": "ORDER_STATUS", "domain_column_name": None}


def assessed(sections=None, payload=None, profile="scan"):
    sections = inventory() if sections is None else sections
    data = mod.calculate(sections, profile)
    mod.enrich_analysis(sections, data, semantics=payload)
    return data


def plain_html(value):
    return html.unescape(re.sub(r"<[^>]*>", " ", value))


class AiSemanticsAggregationTests(unittest.TestCase):
    def test_old_input_is_not_collected_and_never_zero_percent(self):
        data = assessed()
        sem = data["ai_semantics"]
        for component in ("scope", "annotations", "domains"):
            self.assertEqual(sem[component + "_state"], "not_collected")
        for key in ("coverage", "total_columns", "annotated_columns", "direct_columns",
                    "inherited_columns", "domain_linked_columns", "table_annotations"):
            self.assertIsNone(sem[key], key)

    def test_observed_direct_and_domain_counts_use_distinct_columns(self):
        payload = mod.load_semantics(OBSERVED)
        for table, direct, inherited, linked in (("AIRD_T02", 1, 0, 0), ("AIRD_T03", 0, 1, 1)):
            with self.subTest(table=table):
                data = assessed(inventory((("BAD_AI_READY", table),)), payload)
                sem = data["ai_semantics"]
                self.assertEqual(sem["total_columns"], 3)
                self.assertEqual(sem["annotated_columns"], 1)
                self.assertEqual(sem["direct_columns"], direct)
                self.assertEqual(sem["inherited_columns"], inherited)
                self.assertEqual(sem["domain_linked_columns"], linked)
                self.assertEqual(sem["table_annotations"], 0)
                self.assertAlmostEqual(sem["coverage"], 1.0 / 3)
                self.assertEqual(len(sem["annotations"]), 3)
                self.assertEqual(sem["context"]["session_user"], "ADB_USER")
                self.assertEqual(sem["context"]["target_owner"], "BAD_AI_READY")

    def test_duplicate_records_do_not_inflate_column_coverage(self):
        item = annotation()
        payload = synthetic_payload(records=[item, item, annotation(name="ALIASES"), annotation(name="VALUES")])
        payload["records"].append({"type": "column", "owner": "OWNER_A", "table_name": "ORDERS", "column_name": "C03"})
        sem = assessed(payload=payload)["ai_semantics"]
        self.assertEqual(sem["total_columns"], 3)
        self.assertEqual(sem["annotated_columns"], 1)
        self.assertEqual(sem["direct_columns"], 1)
        self.assertAlmostEqual(sem["coverage"], 1.0 / 3)

    def test_table_annotation_is_separate_from_column_coverage(self):
        sem = assessed(payload=synthetic_payload(records=[annotation(column=None)]))["ai_semantics"]
        self.assertEqual(sem["table_annotations"], 1)
        self.assertEqual(sem["annotated_columns"], 0)
        self.assertEqual(sem["direct_columns"], 0)
        self.assertEqual(sem["coverage"], 0.0)

    def test_direct_and_inherited_on_one_column_are_counted_once_overall(self):
        rows = [annotation(), annotation(name="VALUES", domain_owner="OWNER_A", domain_name="ORDER_STATUS"), domain()]
        sem = assessed(payload=synthetic_payload(records=rows))["ai_semantics"]
        self.assertEqual(sem["annotated_columns"], 1)
        self.assertEqual(sem["direct_columns"], 1)
        self.assertEqual(sem["inherited_columns"], 1)
        self.assertEqual(sem["domain_linked_columns"], 1)
        self.assertAlmostEqual(sem["coverage"], 1.0 / 3)

    def test_domain_association_alone_does_not_imply_annotation(self):
        sem = assessed(payload=synthetic_payload(records=[domain()]))["ai_semantics"]
        self.assertEqual(sem["domain_linked_columns"], 1)
        self.assertEqual(sem["annotated_columns"], 0)
        self.assertEqual(sem["inherited_columns"], 0)
        self.assertEqual(sem["coverage"], 0.0)

    def test_domain_definition_is_never_a_table_or_column_annotation(self):
        row = annotation(table="ORDERS", object_type="DOMAIN")
        sem = assessed(payload=synthetic_payload(records=[row]))["ai_semantics"]
        self.assertEqual(sem["annotated_columns"], 0)
        self.assertEqual(sem["table_annotations"], 0)
        self.assertEqual(sem["annotations"], [])

    def test_empty_scope_has_no_percentage(self):
        sem = assessed(inventory(()), synthetic_payload(()))["ai_semantics"]
        self.assertEqual(sem["total_columns"], 0)
        self.assertEqual(sem["annotated_columns"], 0)
        self.assertIsNone(sem["coverage"])

    def test_successful_empty_collection_differs_from_not_collected(self):
        empty = assessed(payload=synthetic_payload())["ai_semantics"]
        missing = assessed()["ai_semantics"]
        self.assertEqual(empty["annotations_state"], "collected")
        self.assertEqual(empty["annotated_columns"], 0)
        self.assertEqual(empty["coverage"], 0.0)
        self.assertNotEqual(empty["annotations_state"], missing["annotations_state"])
        self.assertIsNone(missing["coverage"])

    def test_unavailable_annotation_states_preserve_diagnostics_and_unknown_counts(self):
        for state in ("not_collected", "unsupported", "permission_denied", "unavailable", "error"):
            with self.subTest(state=state):
                sem = assessed(payload=synthetic_payload(states={"annotations": state}))["ai_semantics"]
                self.assertEqual(sem["annotations_state"], state)
                self.assertIsNone(sem["coverage"])
                self.assertIsNone(sem["annotated_columns"])
                self.assertIsNone(sem["direct_columns"])
                self.assertIsNone(sem["inherited_columns"])
                self.assertIsNone(sem["table_annotations"])
                self.assertIn("synthetic diagnostic", str(sem["statuses"]["annotations"]))

    def test_domains_and_scope_failures_do_not_become_zero(self):
        sem = assessed(payload=synthetic_payload(states={"domains": "permission_denied"}))["ai_semantics"]
        self.assertEqual(sem["domains_state"], "permission_denied")
        self.assertIsNone(sem["domain_linked_columns"])
        sem = assessed(payload=synthetic_payload(records=[annotation()], states={"scope": "unavailable"}))["ai_semantics"]
        self.assertEqual(sem["scope_state"], "unavailable")
        self.assertIsNone(sem["total_columns"])
        self.assertIsNone(sem["coverage"])

    def test_partial_rows_after_scope_failure_are_not_reported_as_out_of_scope(self):
        for state in ("not_collected", "unavailable", "error"):
            with self.subTest(state=state):
                sem = assessed(payload=synthetic_payload(
                    records=[annotation(), domain()], states={"scope": state}
                ))["ai_semantics"]
                self.assertEqual(sem["excluded_records"], 0)
                self.assertEqual(sem["annotations"], [])
                self.assertEqual(sem["domains"], [])
                self.assertIsNone(sem["annotated_columns"])
                self.assertIsNone(sem["domain_linked_columns"])

    def test_incomplete_domain_association_matches_collector_contract(self):
        # The collector emits a row when either dictionary provenance field exists.
        for missing in ("domain_owner", "domain_name"):
            with self.subTest(missing=missing):
                row = domain()
                row[missing] = None
                data = assessed(payload=synthetic_payload(records=[row]))
                sem = data["ai_semantics"]
                self.assertEqual(sem["domain_linked_columns"], 1)
                self.assertEqual(sem["annotated_columns"], 0)
                self.assertEqual(len(sem["domains"]), 1)
                markdown = "\n".join(mod.render_ai_semantics_markdown(data, "en"))
                report_html = mod.render_ai_semantics_html(data, "en")
                self.assertIn("?", markdown)
                self.assertIn("?", report_html)

    def test_domain_record_without_any_association_is_invalid(self):
        row = domain()
        row["domain_owner"] = None
        row["domain_name"] = None
        with self.assertRaises(ValueError):
            assessed(payload=synthetic_payload(records=[row]))

    def test_subset_uses_only_successfully_collected_inventory(self):
        tables = (("OWNER_A", "ORDERS"), ("OWNER_A", "OTHER_TABLE"))
        payload = synthetic_payload(records=[annotation()])
        sem = assessed(inventory(tables), payload)["ai_semantics"]
        self.assertEqual(sem["total_columns"], 3)
        self.assertAlmostEqual(sem["coverage"], 1.0 / 3)

    def test_same_name_other_owner_and_out_of_scope_objects_are_excluded(self):
        rows = [annotation(), annotation(owner="OWNER_B"), annotation(table="UNSCOPED"), annotation(column="UNSCOPED")]
        data = assessed(inventory((("OWNER_A", "ORDERS"), ("OWNER_B", "ORDERS"))), synthetic_payload(records=rows))
        sem = data["ai_semantics"]
        self.assertEqual(sem["total_columns"], 3)
        self.assertEqual(sem["annotated_columns"], 1)
        self.assertEqual(len(sem["annotations"]), 1)
        self.assertGreaterEqual(sem["excluded_records"], 3)

    def test_two_scoped_owners_are_counted_independently(self):
        tables = (("OWNER_A", "ORDERS"), ("OWNER_B", "ORDERS"))
        rows = [annotation(), annotation(owner="OWNER_B")]
        sem = assessed(inventory(tables), synthetic_payload(tables, rows))["ai_semantics"]
        self.assertEqual(sem["total_columns"], 6)
        self.assertEqual(sem["annotated_columns"], 2)
        self.assertEqual(sem["direct_columns"], 2)

    def test_unknown_origin_is_not_assumed_direct(self):
        row = annotation(origin="UNKNOWN")
        del row["domain_owner"]
        del row["domain_name"]
        sem = assessed(payload=synthetic_payload(records=[row]))["ai_semantics"]
        self.assertEqual(sem["annotated_columns"], 1)
        self.assertEqual(sem["direct_columns"], 0)
        self.assertEqual(sem["inherited_columns"], 0)
        self.assertEqual(sem["unknown_origin_columns"], 1)

    def test_contradictory_provenance_is_not_assumed_direct(self):
        row = annotation(origin="DIRECT", domain_owner="OWNER_A", domain_name="ORDER_STATUS")
        sem = assessed(payload=synthetic_payload(records=[row, domain()]))["ai_semantics"]
        self.assertEqual(sem["direct_columns"], 0)
        self.assertEqual(sem["inherited_columns"], 0)
        self.assertEqual(sem["unknown_origin_columns"], 1)

    def test_valueless_and_unfamiliar_annotations_are_valid(self):
        for value in (None, ""):
            with self.subTest(value=value):
                sem = assessed(payload=synthetic_payload(records=[annotation(name="BUSINESS_MARKER", value=value)]))["ai_semantics"]
                self.assertEqual(sem["annotated_columns"], 1)
                self.assertEqual(sem["annotations_state"], "collected")

    def test_metadata_does_not_claim_runtime_verification(self):
        sem = assessed(payload=mod.load_semantics(OBSERVED))["ai_semantics"]
        evidence = sem["runtime_evidence"]
        self.assertTrue(evidence)
        for item in evidence.values():
            state = item.get("state") if isinstance(item, dict) else item
            self.assertIn(state, ("unverified", "not_verified", "not_checked"))


class AiSemanticsInputAndReportTests(unittest.TestCase):
    def test_json_round_trip_preserves_special_text_without_interpretation(self):
        value = '日本語, "quoted", O\'Brien\n次行 | <script>alert("x")</script> & [open](javascript:alert(1))'
        payload = synthetic_payload(records=[annotation(value=value)])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "special.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            loaded = mod.load_semantics(path)
        row = next(row for row in loaded["records"] if row["type"] == "annotation")
        self.assertEqual(row["annotation_value"], value)
        data = assessed(payload=loaded)
        for language in ("ja", "en"):
            markdown, sql = mod.render_markdown(data, Path("synthetic.out"), 0, 0, language)
            report_html = mod.render_html(data, Path("synthetic.out"), sql, language)
            self.assertIn("日本語", markdown)
            self.assertIn("日本語", report_html)
            self.assertIn("&lt;script&gt;", report_html)
            self.assertNotIn("<script>", report_html)
            self.assertNotIn("<script>", markdown)
            self.assertNotIn("[open](javascript:", markdown)
            self.assertNotIn("<script", sql)
            self.assertNotIn("<iframe", report_html)

    def test_loader_rejects_malformed_or_unrecognized_contract(self):
        bad_inputs = ["not json", "[]", "{}", json.dumps({"format": "other", "records": []}),
                      json.dumps({"format": "oracle-ai-semantics-v1", "records": {}}),
                      json.dumps({"format": "oracle-ai-semantics-v1", "records": [123]}),
                      json.dumps({"format": "oracle-ai-semantics-v1", "records": [{"type": "status", "component": "annotations", "state": "invented"}]})]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.json"
            for text in bad_inputs:
                with self.subTest(text=text):
                    path.write_text(text, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        mod.load_semantics(path)

    def test_markdown_and_html_show_same_coverage_and_collection_states(self):
        for state in ("collected", "not_collected", "unsupported", "permission_denied", "unavailable", "error"):
            data = assessed(payload=synthetic_payload(records=[annotation()], states={"annotations": state}))
            for language in ("ja", "en"):
                with self.subTest(state=state, language=language):
                    markdown, sql = mod.render_markdown(data, Path("synthetic.out"), 0, 0, language)
                    report_html = mod.render_html(data, Path("synthetic.out"), sql, language)
                    self.assertIn("AI Semantics Readiness", markdown)
                    self.assertIn("AI Semantics Readiness", report_html)
                    if state == "collected":
                        self.assertIn("33.33%", markdown)
                        self.assertIn("33.33%", plain_html(report_html))
                    else:
                        self.assertIn("N/A", markdown)
                        self.assertIn("N/A", report_html)
                    # Machine-readable state labels must survive both renderers.
                    self.assertIn(state, html.unescape(markdown))
                    self.assertIn(state, plain_html(report_html))

    def test_score_comment_gate_and_improvement_sql_unchanged_for_scan_and_rag(self):
        for name, expected, gate in (("bad_ai_ready_before.out", "0.22", False), ("bad_ai_ready_after.out", "0.97", True)):
            sections = mod.parse_sections(FIXTURES / name)
            for profile in ("scan", "rag"):
                with self.subTest(fixture=name, profile=profile):
                    without = assessed(sections, profile=profile)
                    row = annotation(owner="BAD_AI_READY", table="RAW_CUSTOMERS", column="COUNTRY_CODE")
                    payload = synthetic_payload((("BAD_AI_READY", "RAW_CUSTOMERS"),), [row])
                    payload["records"] = [record for record in payload["records"] if record["type"] != "column"]
                    payload["records"].extend(
                        {"type": "column", "owner": item["OWNER"], "table_name": item["TABLE_NAME"], "column_name": item["COLUMN_NAME"]}
                        for item in sections["column_inventory"] if item["TABLE_NAME"] == "RAW_CUSTOMERS"
                    )
                    with_semantics = assessed(sections, payload, profile)
                    self.assertEqual(with_semantics["ai_semantics"]["annotated_columns"], 1)
                    self.assertGreater(with_semantics["ai_semantics"]["coverage"], 0)
                    for key in ("overall", "metrics", "weights", "dimension_scores", "mandatory_gate_pass", "comment_quality"):
                        self.assertEqual(with_semantics[key], without[key], key)
                    self.assertEqual(without["mandatory_gate_pass"], gate)
                    if profile == "scan":
                        self.assertEqual(mod.score(without["overall"]), expected)
                    before_sql = mod.build_sql_text(without, 200, 50, "ja")
                    after_sql = mod.build_sql_text(with_semantics, 200, 50, "ja")
                    self.assertEqual(before_sql, after_sql)

    def test_cli_supports_optional_semantics_for_both_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for profile in ("scan", "rag"):
                with self.subTest(profile=profile):
                    markdown, report_html, sql = (base / (profile + suffix) for suffix in (".md", ".html", ".sql"))
                    rc = mod.main([str(FIXTURES / "bad_ai_ready_after.out"), "--profile", profile,
                                   "--semantics-input", str(OBSERVED), "--output", str(markdown),
                                   "--html-output", str(report_html), "--sql-output", str(sql)])
                    self.assertEqual(rc, 0)
                    self.assertIn("AI Semantics Readiness", markdown.read_text(encoding="utf-8"))
                    self.assertIn("AI Semantics Readiness", report_html.read_text(encoding="utf-8"))
                    self.assertTrue(sql.is_file())

    def test_cli_bad_semantics_returns_error_without_report_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            invalid = base / "invalid.json"
            invalid.write_text("not json", encoding="utf-8")
            target = base / "report.md"
            with contextlib.redirect_stderr(io.StringIO()) as errors:
                rc = mod.main([str(FIXTURES / "bad_ai_ready_after.out"), "--semantics-input", str(invalid), "--output", str(target)])
            self.assertNotEqual(rc, 0)
            self.assertFalse(target.exists())
            self.assertIn("error", errors.getvalue().lower())


class SelectAiSetupRegressionTests(unittest.TestCase):
    def test_existing_rag_generator_keeps_profiles_and_disabled_runsql(self):
        config = generator.load_json(ROOT / "examples" / "select_ai_rag_config.json")
        attrs = generator.make_profile_attributes(config["nl2sql_profile"], "HR", include_objects=True)
        self.assertTrue(attrs["annotations"])
        self.assertNotIn("domains", attrs)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                generator.build(config, output, replace=False)
            rag_profile = (output / "03_create_rag_profile.sql").read_text(encoding="utf-8")
            vector_index = (output / "04_create_vector_index.sql").read_text(encoding="utf-8")
            attachment = (output / "05_attach_vector_index.sql").read_text(encoding="utf-8")
            smoke = (output / "06_smoke_test.sql").read_text(encoding="utf-8")
            self.assertIn("HR_RAG", rag_profile)
            self.assertIn("embedding_model", rag_profile)
            self.assertIn("CREATE_VECTOR_INDEX", vector_index)
            self.assertIn("HR_DOCS_VECIDX", attachment)
            self.assertIn("SELECT AI SHOWPROMPT", smoke)
            self.assertIn("SELECT AI SHOWSQL", smoke)
            self.assertIn("action       => 'narrate'", smoke)
            self.assertFalse(any(line.lstrip().startswith("SELECT AI RUNSQL") for line in smoke.splitlines()))


if __name__ == "__main__":
    unittest.main()
