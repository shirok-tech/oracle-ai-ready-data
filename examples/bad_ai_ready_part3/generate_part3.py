#!/usr/bin/env python3
"""Generate a local, reviewable Annotation/Domain comparison; never connect to a DB."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "select_ai_setup", ROOT / "scripts" / "generate_select_ai_setup.py"
)
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)

PROFILES = (
    ("AIRD_P_D_OFF", "AIRD_T02", False),
    ("AIRD_P_D_ON", "AIRD_T02", True),
    ("AIRD_P_M_OFF", "AIRD_T03", False),
    ("AIRD_P_M_ON", "AIRD_T03", True),
)
QUESTION = "有効な注文について、C02の合計を教えてください。"
SETTINGS = """SET DEFINE OFF
SET ENCODING UTF-8
SET TIMING OFF
SET AUTOTRACE OFF
SET SQLCASE MIXED
SET SQLBLANKLINES ON
SET VERIFY OFF
SET ECHO OFF
SET FEEDBACK OFF
SET HEADING ON
SET SERVEROUTPUT ON
SET NULL '(NULL)'
SET SQLFORMAT DEFAULT
SET PAGESIZE 100
SET LINESIZE 220
SET LONG 1000000
SET LONGCHUNKSIZE 1000000
SET TRIMSPOOL ON
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
WHENEVER OSERROR EXIT FAILURE ROLLBACK
"""


def assert_session(user: str) -> str:
    return f"""BEGIN
  IF SYS_CONTEXT('USERENV', 'SESSION_USER') <> '{user}'
     OR SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') <> '{user}' THEN
    RAISE_APPLICATION_ERROR(-20001, 'Use session user and current schema {user}.');
  END IF;
END;
/
"""


def create_lab(owner: str, ai_user: str) -> str:
    return SETTINGS + assert_session(owner) + f"""
-- Review before execution. DDL commits implicitly; no existing objects are removed.
DECLARE
  l_count PLS_INTEGER;
BEGIN
  SELECT COUNT(*) INTO l_count FROM user_objects
   WHERE object_name IN ('AIRD_D01', 'AIRD_T02', 'AIRD_T03');
  IF l_count > 0 THEN
    RAISE_APPLICATION_ERROR(-20002, 'Lab names already exist. Stop and inspect.');
  END IF;
END;
/
CREATE DOMAIN AIRD_D01 AS VARCHAR2(2 CHAR)
  ANNOTATIONS (
    DESCRIPTION 'MAP_PROOF_V1: Order status code. 有効な注文 means active orders.',
    ALIASES 'Order status, 注文状態, 注文ステータス',
    "VALUES" 'Q7 = active (有効な注文); X9 = cancelled (取消済みの注文)'
  );
CREATE TABLE AIRD_T02 (
  C01 VARCHAR2(10 CHAR),
  C02 NUMBER(12,2),
  C03 VARCHAR2(2 CHAR) ANNOTATIONS (
    DESCRIPTION 'MAP_PROOF_V1: Order status code. 有効な注文 means active orders.',
    ALIASES 'Order status, 注文状態, 注文ステータス',
    "VALUES" 'Q7 = active (有効な注文); X9 = cancelled (取消済みの注文)'
  )
);
CREATE TABLE AIRD_T03 (
  C01 VARCHAR2(10 CHAR),
  C02 NUMBER(12,2),
  C03 VARCHAR2(2 CHAR) DOMAIN AIRD_D01
);
INSERT ALL
  INTO AIRD_T02 VALUES ('O001', 1200, 'Q7')
  INTO AIRD_T02 VALUES ('O002',  800, 'Q7')
  INTO AIRD_T02 VALUES ('O003',  500, 'X9')
  INTO AIRD_T03 VALUES ('O001', 1200, 'Q7')
  INTO AIRD_T03 VALUES ('O002',  800, 'Q7')
  INTO AIRD_T03 VALUES ('O003',  500, 'X9')
SELECT 1 FROM dual;
COMMIT;
GRANT SELECT ON AIRD_T02 TO {ai_user};
GRANT SELECT ON AIRD_T03 TO {ai_user};
EXIT SUCCESS
"""


def dictionary_sql(owner: str) -> str:
    return SETTINGS + assert_session(owner) + """
-- This lab requires Annotation/Domain dictionaries; the general collector is optional.
SET SQLFORMAT CSV
SPOOL logs/02_dictionary.csv CREATE
SELECT SYS_CONTEXT('USERENV', 'SESSION_USER') AS session_user,
       SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') AS current_schema FROM dual;
SELECT product, version_full FROM product_component_version
 WHERE product LIKE 'Oracle%Database%';
SELECT object_name, object_type, column_name, annotation_name,
       annotation_value, domain_owner, domain_name
  FROM user_annotations_usage
 WHERE object_name IN ('AIRD_T02', 'AIRD_T03', 'AIRD_D01')
 ORDER BY object_name, column_name, annotation_name;
SELECT table_name, column_name, domain_owner, domain_name
  FROM user_tab_columns
 WHERE table_name IN ('AIRD_T02', 'AIRD_T03')
 ORDER BY table_name, column_id;
SPOOL OFF
SET SQLFORMAT DEFAULT
SPOOL logs/02_reference.log CREATE
SELECT 'AIRD_T02' AS table_name, SUM(C02) AS all_amount,
       SUM(CASE WHEN C03 = 'Q7' THEN C02 END) AS active_amount FROM AIRD_T02
UNION ALL
SELECT 'AIRD_T03', SUM(C02),
       SUM(CASE WHEN C03 = 'Q7' THEN C02 END) FROM AIRD_T03;
SPOOL OFF
EXIT SUCCESS
"""


def create_profiles(owner: str, ai_user: str, credential: str, model: str) -> str:
    names = ", ".join(setup.sql_literal(item[0]) for item in PROFILES)
    sql = SETTINGS + assert_session(ai_user) + f"""
-- The credential must already belong to this session user. No secrets are accepted.
DECLARE
  l_count PLS_INTEGER;
BEGIN
  SELECT COUNT(*) INTO l_count FROM user_credentials
   WHERE credential_name = '{credential}';
  IF l_count <> 1 THEN
    RAISE_APPLICATION_ERROR(-20003, 'Existing credential {credential} is not owned by this user.');
  END IF;
  SELECT COUNT(*) INTO l_count FROM user_cloud_ai_profiles
   WHERE profile_name IN ({names});
  IF l_count > 0 THEN
    RAISE_APPLICATION_ERROR(-20004, 'Experiment profiles exist. Stop and inspect.');
  END IF;
END;
/
"""
    for name, table, annotations in PROFILES:
        attrs = setup.make_profile_attributes(
            {
                "provider": "openai",
                "credential_name": credential,
                "model": model,
                "object_list": [{"owner": owner, "name": table}],
                "comments": False,
                "constraints": False,
                "annotations": annotations,
                "provider_attributes": {"conversation": False},
            },
            owner,
            include_objects=True,
        )
        sql += setup.profile_block(name, "Part 3 metadata comparison", attrs, False)
    return sql + "EXIT SUCCESS\n"


def trial_header(ai_user: str, name: str, run: str) -> str:
    return SETTINGS + assert_session(ai_user) + f"""
-- Start a fresh SQLcl session for each profile/trial; do not create conversations.
BEGIN
  DBMS_CLOUD_AI.SET_PROFILE(profile_name => '{name}');
END;
/
PROMPT Profile {name}; trial {run}
"""


def profile_evidence(name: str, run: str, suffix: str = "") -> str:
    return f"""
SET SQLFORMAT CSV
SPOOL logs/{name}_{run}{suffix}_attributes.csv CREATE
SELECT '{run}' AS trial_id, SYS_CONTEXT('USERENV', 'SESSION_USER') AS session_user,
       profile_name, attribute_name, attribute_value
  FROM user_cloud_ai_profile_attributes
 WHERE profile_name = '{name}'
   AND LOWER(attribute_name) IN (
     'provider', 'credential_name', 'model', 'object_list', 'object_list_mode',
     'enforce_object_list', 'annotations', 'comments', 'constraints', 'conversation',
     'temperature', 'seed', 'max_tokens')
 ORDER BY attribute_name;
SPOOL OFF
SET SQLFORMAT DEFAULT
"""


def probe_sql(ai_user: str, name: str, run: str) -> str:
    stem = f"{name}_{run}"
    return trial_header(ai_user, name, run) + profile_evidence(name, run) + f"""
SET HEADING OFF
SET PAGESIZE 0
SET LINESIZE 32767
SPOOL logs/{stem}_showprompt.txt CREATE
SELECT AI SHOWPROMPT {QUESTION};
SPOOL OFF
SPOOL logs/{stem}_showsql.txt CREATE
SELECT AI SHOWSQL {QUESTION};
SPOOL OFF
EXIT SUCCESS
"""


def reviewed_sql(ai_user: str, name: str, run: str) -> str:
    stem = f"{name}_{run}"
    return SETTINGS + assert_session(ai_user) + f"""
-- Execute only after reviewing and saving the unchanged generated SQL body.
-- This script does not call the AI provider. Never replace this step with RUNSQL.
SPOOL logs/{stem}_reviewed_result.log CREATE
PROMPT Saved SHOWSQL execution; profile {name}; trial {run}
SET ECHO ON
@reviews/{stem}.sql
SET ECHO OFF
SPOOL OFF
EXIT SUCCESS
"""


def runsql_sql(ai_user: str, name: str, run: str, enabled: bool) -> str:
    if not enabled:
        return SETTINGS + """
PROMPT RUNSQL is disabled. It is a separate generation, not saved SHOWSQL execution.
-- Regenerate a NEW output directory with --enable-runsql to opt in.
EXIT SUCCESS
"""
    return trial_header(ai_user, name, run) + profile_evidence(name, run, "_runsql") + f"""
-- Explicit opt-in: this invokes the provider and executes a NEW generated query.
SPOOL logs/{name}_{run}_runsql.log CREATE
PROMPT Separate RUNSQL generation; profile {name}; trial {run}
SELECT AI RUNSQL {QUESTION};
SPOOL OFF
EXIT SUCCESS
"""


def build(outdir: Path, owner: str, ai_user: str, credential: str,
          model: str, trials: int = 3, enable_runsql: bool = False) -> None:
    owner = setup.validate_identifier(owner, "owner")
    ai_user = setup.validate_identifier(ai_user, "select-ai-user")
    credential = setup.validate_identifier(credential, "credential-name")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", model):
        raise ValueError("model must be an explicit model identifier, not SQL or a credential")
    if isinstance(trials, bool) or not isinstance(trials, int) or not 1 <= trials <= 99:
        raise ValueError("trials must be between 1 and 99")
    files = {
        "01_create_lab.sql": create_lab(owner, ai_user),
        "02_dictionary_reference.sql": dictionary_sql(owner),
        "03_create_profiles.sql": create_profiles(owner, ai_user, credential, model),
        "99_cleanup_template.sql": """-- Manual cleanup only, after preserving all evidence.
-- Run profile removal as the Select AI user; uncomment only reviewed statements.
""" + setup.rollback_sql(PROFILES[0][0], None, None)
        + "".join(
            f"-- EXEC DBMS_CLOUD_AI.DROP_PROFILE(profile_name => '{name}', force => TRUE);\n"
            for name, _, _ in PROFILES[1:]
        ) + f"""-- Connect as {owner} for the following lab objects ONLY.
-- DROP TABLE AIRD_T02 PURGE;
-- DROP TABLE AIRD_T03 PURGE;
-- DROP DOMAIN AIRD_D01;
-- Do not drop a user, or any Part 2 objects.
""",
    }
    for name, _, _ in PROFILES:
        for index in range(1, trials + 1):
            run = f"r{index:02d}"
            stem = f"{name}_{run}"
            files[f"04_{stem}_probe.sql"] = probe_sql(ai_user, name, run)
            files[f"05_{stem}_reviewed.sql"] = reviewed_sql(ai_user, name, run)
            files[f"06_{stem}_runsql.sql"] = runsql_sql(ai_user, name, run, enable_runsql)
            files[f"reviews/{stem}.sql"] = """-- Replace this WHOLE file with the reviewed SHOWSQL body, unchanged.
-- Remove only prose/fences; add a terminator. Reject unsafe or non-SQL responses.
BEGIN
  RAISE_APPLICATION_ERROR(-20080, 'No reviewed SQL has been saved for this trial.');
END;
/
"""
    manifest = {
        "provenance": "Generated locally; no DB connection or LLM call performed",
        "owner": owner, "select_ai_user": ai_user, "credential_name": credential,
        "provider": "openai", "model": model, "trials": trials,
        "runsql_enabled": enable_runsql, "prompt": QUESTION,
        "profiles": [
            {"profile": name, "table": table, "annotations": annotations,
             "comments": False, "constraints": False}
            for name, table, annotations in PROFILES
        ],
    }
    files["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    # Refuse reuse even when empty: protect existing SQL and trial logs from overwrite.
    outdir.mkdir(parents=True, exist_ok=False)
    (outdir / "logs").mkdir()
    (outdir / "reviews").mkdir()
    for name, content in files.items():
        (outdir / name).write_text(content, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--select-ai-user", required=True)
    parser.add_argument("--credential-name", required=True)
    parser.add_argument("--model", required=True, help="Explicit verified OpenAI model; no default")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--enable-runsql", action="store_true", help="Opt in to separate generation/execution")
    args = parser.parse_args(argv)
    try:
        build(args.output_dir, args.owner, args.select_ai_user, args.credential_name,
              args.model, args.trials, args.enable_runsql)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(f"Generated {args.output_dir}; no database or provider was contacted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
