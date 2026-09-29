import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "part3_examples", ROOT / "examples" / "bad_ai_ready_part3" / "generate_part3.py"
)
part3 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(part3)


class Part3ExamplesTests(unittest.TestCase):
    def build(self, path, **overrides):
        args = dict(owner="lab_owner", ai_user="ai_reader", credential="existing_cred",
                    model="explicit-model", trials=3)
        args.update(overrides)
        part3.build(path, **args)

    def test_pairs_keep_provider_and_all_other_attributes_identical(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run"
            self.build(path)
            sql = (path / "03_create_profiles.sql").read_text()
            payloads = [json.loads(value) for value in re.findall(
                r"attributes\s*=>\s*q'~(.*?)~'", sql, re.DOTALL
            )]
            self.assertEqual(len(payloads), 4)
            for off, on in (payloads[:2], payloads[2:]):
                self.assertFalse(off.pop("annotations"))
                self.assertTrue(on.pop("annotations"))
                self.assertEqual(off, on)
                self.assertFalse(on["comments"])
                self.assertFalse(on["constraints"])
                self.assertFalse(on["conversation"])
                self.assertTrue(on["enforce_object_list"])
                self.assertEqual(on["model"], "explicit-model")
                self.assertEqual(on["credential_name"], "EXISTING_CRED")
                self.assertEqual(on["object_list"][0]["owner"], "LAB_OWNER")
            self.assertIn("FROM user_credentials", sql)
            self.assertIn("Experiment profiles exist. Stop and inspect.", sql)
            self.assertNotIn("DROP_PROFILE", sql)

    def test_default_run_sql_is_disabled_and_saved_sql_is_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run"
            self.build(path)
            probes = sorted(path.glob("04_*_probe.sql"))
            runs = sorted(path.glob("06_*_runsql.sql"))
            reviewed = sorted(path.glob("05_*_reviewed.sql"))
            self.assertEqual((len(probes), len(runs), len(reviewed)), (12, 12, 12))
            for item in runs:
                self.assertNotIn("SELECT AI RUNSQL", item.read_text())
            for item in reviewed:
                text = item.read_text()
                self.assertIn("@reviews/", text)
                self.assertNotIn("SELECT AI", text)
                self.assertIn("SET DEFINE OFF", text)
            for item in path.glob("reviews/*.sql"):
                self.assertIn("RAISE_APPLICATION_ERROR", item.read_text())
            for item in probes:
                text = item.read_text()
                self.assertIn("SET PAGESIZE 0", text)
                self.assertIn("SET NULL '(NULL)'", text)
                self.assertIn("_showprompt.txt CREATE", text)
                self.assertIn("_showsql.txt CREATE", text)
                self.assertIn("_attributes.csv CREATE", text)
                self.assertNotIn(" REPLACE", text)

    def test_runsql_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run"
            self.build(path, trials=1, enable_runsql=True)
            files = list(path.glob("06_*_runsql.sql"))
            self.assertEqual(len(files), 4)
            for item in files:
                text = item.read_text()
                self.assertIn("SELECT AI RUNSQL", text)
                self.assertIn("Separate RUNSQL generation", text)
                self.assertIn("SET NULL '(NULL)'", text)
                self.assertIn("_runsql_attributes.csv CREATE", text)
            self.assertTrue(json.loads((path / "manifest.json").read_text())["runsql_enabled"])

    def test_generation_preserves_part2_and_cannot_overwrite_existing_output(self):
        part2 = ROOT / "examples" / "bad_ai_ready_part2"
        before = {p: p.read_bytes() for p in part2.rglob("*") if p.is_file()}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run"
            self.build(path)
            sentinel = path / "logs" / "user_evidence.txt"
            sentinel.write_text("retain")
            with self.assertRaises(FileExistsError):
                self.build(path)
            self.assertEqual(sentinel.read_text(), "retain")
            lab = (path / "01_create_lab.sql").read_text()
            self.assertNotIn("DROP", lab)
            self.assertNotIn("RAW_CUSTOMERS", lab)
            cleanup = (path / "99_cleanup_template.sql").read_text()
            self.assertTrue(all(not line.strip() or line.startswith("--")
                                for line in cleanup.splitlines()))
        self.assertEqual(before, {p: p.read_bytes() for p in part2.rglob("*") if p.is_file()})

    def test_invalid_input_is_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            for index, kwargs in enumerate((
                {"owner": "LAB'; DROP USER X;--"},
                {"ai_user": "AI_READER\nHOST whoami"},
                {"credential": "cred/password"},
                {"model": "model'\nHOST whoami"},
                {"model": ""}, {"trials": 0}, {"trials": 100}, {"trials": True},
            )):
                path = Path(temp) / str(index)
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    self.build(path, **kwargs)
                self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
