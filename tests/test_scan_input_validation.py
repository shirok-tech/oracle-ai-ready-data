"""Synthetic, offline regression cases for sectioned SQLcl CSV input.

These inputs are parser boundary cases, not captured Oracle execution results.
No database or external model is used.
"""

import contextlib
import csv
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "score_oracle_ai_ready_scan.py"
spec = importlib.util.spec_from_file_location("scan_input_validation", str(SCRIPT))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def section(name, header=None, rows=()):
    output = io.StringIO()
    output.write("@@SECTION:{0}\n".format(name))
    writer = csv.writer(output, lineterminator="\n")
    if header is not None:
        writer.writerow(header)
    writer.writerows(rows)
    output.write("@@END_SECTION\n")
    return output.getvalue()


CONTEXT = section("run_context", ("TARGET_OWNER", "PROFILE"), [("HR", "scan")])
TABLES = section("table_inventory", ("OWNER", "TABLE_NAME"), [("HR", "ORDERS")])
COLUMNS = section("column_inventory", ("OWNER", "TABLE_NAME", "COLUMN_NAME"), [("HR", "ORDERS", "ORDER_ID")])
VALID = CONTEXT + TABLES + COLUMNS


class ScanInputValidationTests(unittest.TestCase):
    maxDiff = 2000

    def parse_text(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scan.out"
            path.write_text(text, encoding="utf-8")
            return mod.parse_sections(path)

    def assert_invalid(self, text):
        with self.assertRaises(ValueError):
            self.parse_text(text)

    def test_minimal_legacy_headers_do_not_need_version_or_global_footer(self):
        parsed = self.parse_text(VALID)
        self.assertEqual(parsed["table_inventory"], [{"OWNER": "HR", "TABLE_NAME": "ORDERS"}])
        self.assertEqual(parsed["column_inventory"][0]["COLUMN_NAME"], "ORDER_ID")

    def test_header_only_blank_and_no_rows_selected_are_valid_empty_scopes(self):
        for style in ("header", "blank", "no_rows"):
            with self.subTest(style=style):
                if style == "header":
                    tables = section("table_inventory", ("OWNER", "TABLE_NAME"))
                    columns = section("column_inventory", ("OWNER", "TABLE_NAME", "COLUMN_NAME"))
                else:
                    body = "" if style == "blank" else "no rows selected.\n"
                    tables = "@@SECTION:table_inventory\n" + body + "@@END_SECTION\n"
                    columns = "@@SECTION:column_inventory\n" + body + "@@END_SECTION\n"
                parsed = self.parse_text(CONTEXT + tables + columns)
                self.assertEqual(parsed["table_inventory"], [])
                self.assertEqual(parsed["column_inventory"], [])

    def test_all_required_sections_must_be_present(self):
        for text in ("", "irrelevant text\n", CONTEXT, TABLES + COLUMNS,
                     CONTEXT + TABLES, CONTEXT + COLUMNS):
            with self.subTest(text=text[:80]):
                self.assert_invalid(text)

    def test_run_context_requires_one_owner_and_valid_profile(self):
        bad_contexts = (
            section("run_context", ("TARGET_OWNER", "PROFILE")),
            section("run_context", ("TARGET_OWNER", "PROFILE"), [("HR", "scan"), ("HR", "rag")]),
            section("run_context", ("TARGET_OWNER", "PROFILE"), [("", "scan")]),
            section("run_context", ("TARGET_OWNER", "PROFILE"), [("HR", "")]),
            section("run_context", ("TARGET_OWNER", "PROFILE"), [("HR", "unknown")]),
            section("run_context", ("PROFILE",), [("scan",)]),
            section("run_context", ("TARGET_OWNER",), [("HR",)]),
        )
        for context in bad_contexts:
            with self.subTest(context=context):
                self.assert_invalid(context + TABLES + COLUMNS)
        for profile in ("scan", "rag"):
            context = section("run_context", ("TARGET_OWNER", "PROFILE"), [("HR", profile)])
            self.assertEqual(self.parse_text(context + TABLES + COLUMNS)["run_context"][0]["PROFILE"], profile)

    def test_missing_inventory_identity_headers_are_rejected(self):
        bad_pairs = (
            (section("table_inventory", ("TABLE_NAME",), [("ORDERS",)]), COLUMNS),
            (section("table_inventory", ("OWNER",), [("HR",)]), COLUMNS),
            (TABLES, section("column_inventory", ("OWNER", "TABLE_NAME"), [("HR", "ORDERS")])),
            (TABLES, section("column_inventory", ("TABLE_NAME", "COLUMN_NAME"), [("ORDERS", "ORDER_ID")])),
        )
        for tables, columns in bad_pairs:
            with self.subTest(tables=tables, columns=columns):
                self.assert_invalid(CONTEXT + tables + columns)

    def test_duplicate_section_and_duplicate_csv_header_are_rejected(self):
        self.assert_invalid(VALID + TABLES)
        duplicate_header = section("table_inventory", ("OWNER", "TABLE_NAME", "OWNER"), [("HR", "ORDERS", "OTHER")])
        self.assert_invalid(CONTEXT + duplicate_header + COLUMNS)
        repeated_header_row = section("table_inventory", ("OWNER", "TABLE_NAME"), [("OWNER", "TABLE_NAME"), ("HR", "ORDERS")])
        self.assert_invalid(CONTEXT + repeated_header_row + COLUMNS)

    def test_every_section_must_close_before_next_section_or_eof(self):
        self.assert_invalid(CONTEXT + TABLES.replace("@@END_SECTION\n", "") + COLUMNS)
        self.assert_invalid(VALID[:-len("@@END_SECTION\n")])
        self.assert_invalid(CONTEXT + TABLES.replace("@@END_SECTION\n", "@@END_ORACLE_AI_READY_COLLECTOR\n") + COLUMNS)

    def test_short_long_and_blank_identity_rows_are_rejected(self):
        for row in (("HR",), ("HR", "ORDERS", "unexpected"), ("", "ORDERS"), ("HR", ""), ("", "")):
            with self.subTest(table_row=row):
                self.assert_invalid(CONTEXT + section("table_inventory", ("OWNER", "TABLE_NAME"), [row]) + COLUMNS)
        for row in (("HR", "ORDERS"), ("HR", "ORDERS", "ORDER_ID", "unexpected"), ("HR", "ORDERS", ""), ("", "", "")):
            with self.subTest(column_row=row):
                self.assert_invalid(CONTEXT + TABLES + section("column_inventory", ("OWNER", "TABLE_NAME", "COLUMN_NAME"), [row]))

    def test_columns_must_belong_to_inventory_tables_and_each_table_needs_columns(self):
        no_columns = section("column_inventory", ("OWNER", "TABLE_NAME", "COLUMN_NAME"))
        self.assert_invalid(CONTEXT + TABLES + no_columns)
        other_owner = section("column_inventory", ("OWNER", "TABLE_NAME", "COLUMN_NAME"), [("OTHER", "ORDERS", "ORDER_ID")])
        self.assert_invalid(CONTEXT + TABLES + other_owner)
        other_table = section("column_inventory", ("OWNER", "TABLE_NAME", "COLUMN_NAME"), [("HR", "MISSING", "ORDER_ID")])
        self.assert_invalid(CONTEXT + TABLES + other_table)
        extra_table = section("table_inventory", ("OWNER", "TABLE_NAME"), [("HR", "ORDERS"), ("HR", "NO_COLUMNS")])
        self.assert_invalid(CONTEXT + extra_table + COLUMNS)

    def test_echoed_prompt_and_sql_are_rejected_instead_of_becoming_empty_data(self):
        echoed = VALID.replace("@@SECTION:", "SQL> prompt @@SECTION:").replace("@@END_SECTION", "SQL> prompt @@END_SECTION")
        self.assert_invalid(echoed)
        # ECHO ON includes real markers as well as echoed source statements.
        contamination = ("SQL> select owner, table_name from all_tables;\n",
                         "SQL> prompt @@SECTION:table_inventory\n",
                         "SQL> prompt @@END_SECTION\n")
        for noise in contamination:
            with self.subTest(noise=noise):
                self.assert_invalid(CONTEXT + TABLES.replace("OWNER,TABLE_NAME\n", noise + "OWNER,TABLE_NAME\n") + COLUMNS)

    def test_query_errors_inside_sections_are_rejected(self):
        for error in ("ORA-00942: table or view does not exist", "SP2-0734: unknown command beginning select", "Error starting at line : 1 in command -"):
            with self.subTest(error=error):
                invalid_tables = "@@SECTION:table_inventory\n" + error + "\n@@END_SECTION\n"
                self.assert_invalid(CONTEXT + invalid_tables + COLUMNS)

    def test_bare_quotes_in_unquoted_cells_cannot_hide_echoed_commands(self):
        malformed = ('@@SECTION:table_comments\nOWNER,TABLE_NAME,COMMENTS\n'
                     'HR,ORDERS,open"\nSQL> owner,table_name,comments\n'
                     'HR,ORDERS,close"\n@@END_SECTION\n')
        self.assert_invalid(VALID + malformed)

    def test_quoted_multiline_values_preserve_prompts_markers_blank_lines_and_noise(self):
        value = ('Business description\nSQL> select metadata as text;\n'
                 '@@SECTION:fake_section\n@@END_SECTION\n'
                 '@@END_ORACLE_AI_READY_COLLECTOR\n\nno rows selected.\n'
                 'old   1: prior text\nnew   1: current text\nElapsed: 00:00:01\n'
                 'spool off\n日本語, "quoted" ending')
        comments = section("table_comments", ("OWNER", "TABLE_NAME", "COMMENTS"), [("HR", "ORDERS", value)])
        parsed = self.parse_text(VALID + comments)
        self.assertEqual(parsed["table_comments"][0]["COMMENTS"], value)
        self.assertNotIn("fake_section", parsed)

    def test_csv_comments_with_same_line_prompts_are_data(self):
        values = ("SQL> legitimate documentation", "@@SECTION:legitimate", "no rows selected.", 'A "quoted", comma')
        for value in values:
            with self.subTest(value=value):
                comments = section("table_comments", ("OWNER", "TABLE_NAME", "COMMENTS"), [("HR", "ORDERS", value)])
                self.assertEqual(self.parse_text(VALID + comments)["table_comments"][0]["COMMENTS"], value)

    def test_unterminated_quoted_csv_is_rejected(self):
        malformed = '@@SECTION:table_comments\nOWNER,TABLE_NAME,COMMENTS\nHR,ORDERS,"unfinished\n@@END_SECTION\n'
        self.assert_invalid(VALID + malformed)

    def test_invalid_cli_does_not_print_a_report_or_overwrite_existing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "invalid.out"
            source.write_text("SQL> prompt @@SECTION:table_inventory\nSQL> select * from all_tables;\n", encoding="utf-8")
            outputs = [base / "report.md", base / "report.html", base / "improvement.sql"]
            for path in outputs:
                path.write_text("existing user content\n", encoding="utf-8")
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                rc = mod.main([str(source), "--output", str(outputs[0]), "--html-output", str(outputs[1]), "--sql-output", str(outputs[2])])
            self.assertEqual(rc, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("error", stderr.getvalue().lower())
            for path in outputs:
                self.assertEqual(path.read_text(encoding="utf-8"), "existing user content\n")
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                rc = mod.main([str(source)])
            self.assertEqual(rc, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("error", stderr.getvalue().lower())

    def test_valid_empty_scope_cli_preserves_legacy_scan_and_rag_results(self):
        # Captured from the pre-fix scorer: legitimate empty scope remains
        # 0 tables / 0 columns, overall 0.97, COMMENT gate pass in both profiles.
        # Input validation must not silently redefine that existing policy.
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "empty.out"
            for profile in ("scan", "rag"):
                with self.subTest(profile=profile):
                    source.write_text(
                        section("run_context", ("TARGET_OWNER", "PROFILE"), [("HR", profile)])
                        + section("table_inventory", ("OWNER", "TABLE_NAME"))
                        + section("column_inventory", ("OWNER", "TABLE_NAME", "COLUMN_NAME")),
                        encoding="utf-8",
                    )
                    data = mod.calculate(mod.parse_sections(source), profile)
                    self.assertEqual(data["total_tables"], 0)
                    self.assertEqual(data["total_columns"], 0)
                    self.assertEqual(data["overall"], 0.97)
                    self.assertTrue(data["mandatory_gate_pass"])
                    stdout, stderr = io.StringIO(), io.StringIO()
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        rc = mod.main([str(source), "--language", "en"])
                    self.assertEqual(rc, 0)
                    self.assertEqual(stderr.getvalue(), "")
                    self.assertIn("| Tables assessed | 0 |", stdout.getvalue())
                    self.assertIn("| Columns assessed | 0 |", stdout.getvalue())
                    self.assertIn("Overall score: **0.97 / 1.00**", stdout.getvalue())
                    self.assertIn("Mandatory comment gate: **pass**", stdout.getvalue())

    def test_collector_turns_echo_off_before_spooling(self):
        collector = (ROOT / "scripts" / "oracle_ai_ready_collect.sql").read_text(encoding="utf-8")
        commands = [line.strip().lower() for line in collector.splitlines() if line.strip() and not line.lstrip().startswith("--")]
        echo_index = commands.index("set echo off")
        spool_index = next(index for index, command in enumerate(commands) if command.startswith("spool "))
        self.assertLess(echo_index, spool_index)


if __name__ == "__main__":
    unittest.main()
