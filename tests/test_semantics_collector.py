"""Offline safety and packaging checks; these do not validate Oracle execution."""

import contextlib
import importlib.util
import io
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("semantics_collector", SCRIPTS / "generate_semantics_collector.py")
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class SemanticsCollectorTests(unittest.TestCase):
    def test_owner_uses_existing_identifier_policy(self):
        self.assertIn("c_owner constant varchar2(128) := 'TEAM_$1';", collector.generate("team_$1"))
        for owner in ["", "1TEAM", '"TEAM"', "TEAM;DROP TABLE X", "TEAM' OR '1'='1", "TEAM&cmd", "TEAM\n/", "A" * 126]:
            with self.subTest(owner=owner), self.assertRaises(ValueError):
                collector.generate(owner)

    def test_like_wildcards_and_escapes(self):
        for pattern in ["%", "emp_%", r"EMP\_%", r"EMP\%", r"EMP\\%", "A_$#9"]:
            with self.subTest(pattern=pattern):
                self.assertEqual(collector.validate_table_pattern(pattern), pattern.upper())
        for pattern in ["", "A" * 257, "' OR 1=1 --", "A&B", "A\n/", "A B", '"A"', "A;", "A\\", r"A\Q"]:
            with self.subTest(pattern=pattern), self.assertRaises(ValueError):
                collector.generate("HR", pattern)

    def test_spool_is_a_filename_not_a_sqlcl_command(self):
        for name in ["evidence_hr_r01.json", "Scan-2.json"]:
            self.assertIn("spool " + name + " create", collector.generate("HR", spool_file=name))
        for name in ["../scan.json", "/tmp/scan.json", "scan.json replace", "x\nhost touch marker", '"scan.json"', "&target", ".", "A" * 201]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                collector.generate("HR", spool_file=name)

    def test_spool_filename_cannot_invoke_reserved_client_commands(self):
        for name in ("off", "OFF", "Out"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                collector.generate("HR", spool_file=name)

    def test_template_markers_in_valid_input_are_preserved_as_literal_data(self):
        sql = collector.generate("A__TABLE_LIKE____SPOOL_FILE__", "__OWNER____SPOOL_FILE__", "evidence.json")
        self.assertIn("c_owner constant varchar2(128) := 'A__TABLE_LIKE____SPOOL_FILE__';", sql)
        self.assertIn("c_table_like constant varchar2(256) := '__OWNER____SPOOL_FILE__';", sql)
        self.assertIn("spool evidence.json create", sql)

    def test_collector_normalizes_json_output_and_preserves_pending_transactions(self):
        sql = collector.generate("HR")
        prologue = sql.split("\nspool ", 1)[0].lower()
        for command in ("set encoding utf-8", "set timing off", "set autotrace off",
                        "set autocommit off", "set errorlogging off",
                        "set sqlblanklines on", "set tab off"):
            self.assertIn(command, prologue)

    def test_collector_does_not_emit_sqlcase_compatibility_command(self):
        # The user's SQLcl 25.4 run reports this compatibility setting as obsolete.
        # JSON generation must keep its own literal case without issuing it.
        sql = collector.generate("HR")
        self.assertNotRegex(sql, r"(?im)^\s*set\s+sqlc(?:ase|as|a)?(?:\s|$)")
        self.assertIn('"format":"oracle-ai-semantics-v1","records":[', sql)
        self.assertIn("status_record('annotations', v_state", sql)
        self.assertIn("then 'DOMAIN_INHERITED'", sql)

    def test_scope_values_are_bound_and_no_sqlcl_substitution_remains(self):
        sql = collector.generate("HR", r"EMP\_%")
        self.assertIn("set define off", sql)
        self.assertIn("dbms_sql.bind_variable(v_cursor, ':target_owner', c_owner)", sql)
        self.assertIn("dbms_sql.bind_variable(v_cursor, ':table_like', c_table_like)", sql)
        self.assertNotRegex(sql, r"__OWNER__|__TABLE_LIKE__|__SPOOL_FILE__|&&?\w+")
        self.assertEqual(sql.count("where t.owner = :target_owner and t.table_name like :table_like escape"), 4)
        self.assertIn("t.owner = a.annotation_owner and t.table_name = a.object_name", sql)
        self.assertIn("a.object_type = 'TABLE'", sql)

    def test_new_dictionary_columns_are_only_in_dynamic_queries(self):
        sql = collector.generate("HR")
        # Every dictionary data query is a q-quoted SELECT passed to DBMS_SQL.
        queries = re.findall(r"q'~(.*?)~'", sql, re.S)
        self.assertEqual(len(queries), 4)
        self.assertTrue(all(query.strip().lower().startswith("select ") for query in queries))
        self.assertIn("capability('ALL_ANNOTATIONS_USAGE'", sql)
        self.assertIn("capability('ALL_TAB_COLUMNS'", sql)
        self.assertIn("if v_visible and sqlcode = -904", sql)
        self.assertIn("if p_code = -942 then return 'unavailable'", sql)
        self.assertIn("if p_code = -1031 then return 'permission_denied'", sql)

    def test_read_only_and_json_transport_contract(self):
        sql = collector.generate("HR")
        executable = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
        self.assertNotRegex(executable.lower(), r"\b(?:insert|update|delete|merge|commit|rollback|grant|revoke)\b|\bcreate\s+(?:table|domain|procedure)\b|dbms_cloud_ai")
        self.assertIn('"format":"oracle-ai-semantics-v1","records":[', sql)
        self.assertIn("for i in 0..31 loop", sql)
        self.assertIn("'\\u' || lpad(to_char(i, 'FMXX'), 4, '0')", sql)
        self.assertIn("if lengthb(v_value) > 32000", sql)
        self.assertIn("if p_value is null then return 'null'", sql)
        self.assertIn("status_record('scope', 'collected'", sql)
        self.assertIn("status_record('annotations', v_state", sql)
        self.assertIn("status_record('domains', v_state", sql)
        self.assertNotIn("@@SECTION", sql)

    def test_cli_generates_a_reviewable_file_without_a_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "collect.sql"
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "generate_semantics_collector.py"), "--owner", "app", "--table-like", "ORD%", "--output", str(output)],
                cwd=tmp, capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("c_owner constant varchar2(128) := 'APP';", output.read_text(encoding="utf-8"))
            self.assertEqual(list(Path(tmp).iterdir()), [output])

    def test_invalid_cli_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "collect.sql"
            with contextlib.redirect_stderr(io.StringIO()):
                rc = collector.main(["--owner", "HR'", "--output", str(output)])
            self.assertEqual(rc, 2)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
