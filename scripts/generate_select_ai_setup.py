#!/usr/bin/env python3
"""Generate reviewable Oracle Select AI NL2SQL and RAG setup SQL.

The generator never stores provider secrets. It only references existing Oracle
credential object names. All generated DDL/PLSQL must be reviewed before use.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]{0,124}$")
FORBIDDEN_KEYS = {
    "api_key",
    "apikey",
    "access_token",
    "secret",
    "secret_key",
    "password",
    "private_key",
    "bearer_token",
}


def fail(message: str) -> "NoReturn":
    raise ValueError(message)


def load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Top-level config must be a JSON object")
    return data


def require_str(obj: Mapping[str, Any], key: str, where: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        fail(f"{where}.{key} must be a non-empty string")
    return value.strip()


def optional_str(obj: Mapping[str, Any], key: str) -> str | None:
    value = obj.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        fail(f"{key} must be a non-empty string when supplied")
    return value.strip()


def validate_identifier(value: str, label: str) -> str:
    if not IDENTIFIER_RE.fullmatch(value):
        fail(
            f"{label} must be an unquoted Oracle identifier of 1-125 characters "
            "starting with a letter and containing only letters, digits, _, $, or #"
        )
    return value.upper()


def validate_no_secrets(value: Any, path: str = "config") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_KEYS:
                fail(
                    f"{path}.{key} is not allowed. Store secrets in an Oracle "
                    "credential object and reference credential_name only."
                )
            validate_no_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_no_secrets(child, f"{path}[{index}]")


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def q_literal(value: str) -> str:
    pairs = [("~", "~"), ("!", "!"), ("[", "]"), ("{", "}"), ("(", ")")]
    for left, right in pairs:
        if left not in value and right not in value:
            return f"q'{left}{value}{right}'"
    return sql_literal(value)


def json_for_sql(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def normalize_object_list(value: Any, default_owner: str) -> List[Dict[str, str]]:
    if value is None:
        return [{"owner": default_owner}]
    if not isinstance(value, list) or not value:
        fail("nl2sql_profile.object_list must be a non-empty array")
    result: List[Dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            fail(f"object_list[{index}] must be an object")
        owner = validate_identifier(require_str(item, "owner", f"object_list[{index}]"), "object owner")
        entry: Dict[str, str] = {"owner": owner}
        if item.get("name") is not None:
            entry["name"] = validate_identifier(require_str(item, "name", f"object_list[{index}]"), "object name")
        result.append(entry)
    return result


def bool_value(obj: Mapping[str, Any], key: str, default: bool) -> bool:
    value = obj.get(key, default)
    if not isinstance(value, bool):
        fail(f"{key} must be true or false")
    return value


def int_value(obj: Mapping[str, Any], key: str, default: int, minimum: int = 0) -> int:
    value = obj.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        fail(f"{key} must be an integer >= {minimum}")
    return value


def number_value(obj: Mapping[str, Any], key: str, default: float, minimum: float = 0.0) -> float:
    value = obj.get(key, default)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or float(value) < minimum:
        fail(f"{key} must be a number >= {minimum}")
    return float(value)


def merge_provider_attributes(target: Dict[str, Any], source: Mapping[str, Any], where: str) -> None:
    extra = source.get("provider_attributes", {})
    if extra is None:
        return
    if not isinstance(extra, dict):
        fail(f"{where}.provider_attributes must be an object")
    for key, value in extra.items():
        normalized = str(key).strip().lower()
        if normalized in FORBIDDEN_KEYS:
            fail(f"{where}.provider_attributes.{key} may contain a secret; it is not allowed")
        if normalized in target:
            fail(f"{where}.provider_attributes duplicates managed attribute {key}")
        target[normalized] = value


def make_profile_attributes(profile: Mapping[str, Any], owner: str, include_objects: bool) -> Dict[str, Any]:
    attrs: Dict[str, Any] = {
        "provider": require_str(profile, "provider", "profile"),
        "credential_name": validate_identifier(
            require_str(profile, "credential_name", "profile"), "credential_name"
        ),
    }
    model = optional_str(profile, "model")
    if model:
        attrs["model"] = model
    embedding_model = optional_str(profile, "embedding_model")
    if embedding_model:
        attrs["embedding_model"] = embedding_model
    region = optional_str(profile, "region")
    if region:
        attrs["region"] = region
    if include_objects:
        mode = str(profile.get("object_list_mode", "all")).lower()
        if mode not in {"all", "automated"}:
            fail("nl2sql_profile.object_list_mode must be all or automated")
        attrs["object_list_mode"] = mode
        if mode == "all" or profile.get("object_list") is not None:
            attrs["object_list"] = normalize_object_list(profile.get("object_list"), owner)
        attrs["enforce_object_list"] = bool_value(profile, "enforce_object_list", True)
        attrs["comments"] = bool_value(profile, "comments", True)
        attrs["annotations"] = bool_value(profile, "annotations", True)
        attrs["constraints"] = bool_value(profile, "constraints", True)
    role = optional_str(profile, "role")
    if role:
        attrs["role"] = role
    instructions = optional_str(profile, "additional_instructions")
    if instructions:
        attrs["additional_instructions"] = instructions
    if bool_value(profile, "enable_custom_source_uri", False):
        attrs["enable_custom_source_uri"] = True
    merge_provider_attributes(attrs, profile, "profile")
    return attrs


def profile_block(name: str, description: str, attrs: Mapping[str, Any], replace: bool) -> str:
    payload = q_literal(json_for_sql(attrs))
    name_lit = sql_literal(name)
    description_lit = q_literal(description)
    if replace:
        return f"""BEGIN
  DBMS_CLOUD_AI.DROP_PROFILE(profile_name => {name_lit}, force => TRUE);
  DBMS_CLOUD_AI.CREATE_PROFILE(
    profile_name => {name_lit},
    attributes   => {payload},
    status       => 'enabled',
    description  => {description_lit}
  );
END;
/
"""
    return f"""DECLARE
  l_count PLS_INTEGER;
BEGIN
  SELECT COUNT(*)
    INTO l_count
    FROM USER_CLOUD_AI_PROFILES
   WHERE UPPER(profile_name) = UPPER({name_lit});

  IF l_count = 0 THEN
    DBMS_CLOUD_AI.CREATE_PROFILE(
      profile_name => {name_lit},
      attributes   => {payload},
      status       => 'enabled',
      description  => {description_lit}
    );
  ELSE
    DBMS_OUTPUT.PUT_LINE('Profile {name} already exists; no changes were made.');
  END IF;
END;
/
"""


def vector_index_block(rag: Mapping[str, Any], rag_profile_name: str, replace: bool) -> str:
    index_name = validate_identifier(require_str(rag, "index_name", "rag"), "rag.index_name")
    location = require_str(rag, "location", "rag")
    credential = validate_identifier(
        require_str(rag, "object_storage_credential_name", "rag"),
        "rag.object_storage_credential_name",
    )
    attrs: Dict[str, Any] = {
        "vector_db_provider": str(rag.get("vector_db_provider", "oracle")),
        "profile_name": rag_profile_name,
        "location": location,
        "object_storage_credential_name": credential,
        "chunk_size": int_value(rag, "chunk_size", 1024, 1),
        "chunk_overlap": int_value(rag, "chunk_overlap", 128, 0),
        "refresh_rate": int_value(rag, "refresh_rate", 1440, 1),
        "match_limit": int_value(rag, "match_limit", 5, 1),
        "similarity_threshold": number_value(rag, "similarity_threshold", 0.0, 0.0),
        "enable_sources": bool_value(rag, "enable_sources", True),
    }
    vector_table_name = optional_str(rag, "vector_table_name")
    if vector_table_name:
        attrs["vector_table_name"] = validate_identifier(vector_table_name, "rag.vector_table_name")
    vector_dimension = rag.get("vector_dimension")
    if vector_dimension is not None:
        if not isinstance(vector_dimension, int) or vector_dimension <= 0:
            fail("rag.vector_dimension must be a positive integer")
        attrs["vector_dimension"] = vector_dimension
    metric = optional_str(rag, "vector_distance_metric")
    if metric:
        attrs["vector_distance_metric"] = metric.upper()
    payload = q_literal(json_for_sql(attrs))
    wait = "TRUE" if bool_value(rag, "wait_for_completion", True) else "FALSE"
    name_lit = sql_literal(index_name)
    description = q_literal(str(rag.get("description", "Select AI RAG document index")))
    if replace:
        return f"""BEGIN
  DBMS_CLOUD_AI.DROP_VECTOR_INDEX(index_name => {name_lit}, force => TRUE);
  DBMS_CLOUD_AI.CREATE_VECTOR_INDEX(
    index_name          => {name_lit},
    attributes          => {payload},
    status              => 'enabled',
    description         => {description},
    wait_for_completion => {wait}
  );
END;
/
"""
    return f"""DECLARE
  l_count PLS_INTEGER;
BEGIN
  SELECT COUNT(*)
    INTO l_count
    FROM USER_CLOUD_VECTOR_INDEXES
   WHERE UPPER(index_name) = UPPER({name_lit});

  IF l_count = 0 THEN
    DBMS_CLOUD_AI.CREATE_VECTOR_INDEX(
      index_name          => {name_lit},
      attributes          => {payload},
      status              => 'enabled',
      description         => {description},
      wait_for_completion => {wait}
    );
  ELSE
    DBMS_OUTPUT.PUT_LINE('Vector index {index_name} already exists; no changes were made.');
  END IF;
END;
/
"""


def preflight_sql(owner: str, nl_name: str, rag_name: str | None, index_name: str | None) -> str:
    rag_checks = ""
    if rag_name and index_name:
        rag_checks = f"""
PROMPT === RAG prerequisites ===
SELECT owner, object_name, object_type, status
  FROM all_objects
 WHERE object_name IN ('DBMS_CLOUD_PIPELINE')
 ORDER BY owner, object_name, object_type;

SELECT credential_name, username, comments, enabled
  FROM user_credentials
 ORDER BY credential_name;

SELECT profile_name, status, description
  FROM user_cloud_ai_profiles
 WHERE UPPER(profile_name) IN (UPPER('{rag_name}'));

SELECT index_name, status, description
  FROM user_cloud_vector_indexes
 WHERE UPPER(index_name) IN (UPPER('{index_name}'));
"""
    profile_names = [nl_name] + ([rag_name] if rag_name else [])
    profile_predicate = ", ".join(
        f"UPPER({sql_literal(name)})" for name in profile_names
    )
    return f"""-- Generated by generate_select_ai_setup.py
-- Read-only preflight. Run before any setup SQL.
SET SERVEROUTPUT ON SIZE UNLIMITED
SET LONG 200000
SET LONGCHUNKSIZE 200000
SET PAGESIZE 50000
SET LINESIZE 32767

PROMPT === Database and session ===
SELECT sys_context('USERENV','DB_NAME') AS db_name,
       sys_context('USERENV','CON_NAME') AS con_name,
       sys_context('USERENV','SESSION_USER') AS session_user,
       sys_context('USERENV','CURRENT_SCHEMA') AS current_schema
  FROM dual;

SELECT product, version, version_full, status
  FROM product_component_version
 WHERE product LIKE 'Oracle%Database%';

PROMPT === Required packages and procedures ===
SELECT owner, object_name, object_type, status
  FROM all_objects
 WHERE object_name IN ('DBMS_CLOUD_AI','DBMS_CLOUD','DBMS_CLOUD_PIPELINE')
 ORDER BY object_name, owner, object_type;

SELECT owner, object_name, procedure_name
  FROM all_procedures
 WHERE object_name = 'DBMS_CLOUD_AI'
   AND procedure_name IN ('CREATE_PROFILE','SET_PROFILE','GENERATE','CREATE_VECTOR_INDEX','DROP_VECTOR_INDEX')
 ORDER BY procedure_name, owner;

PROMPT === Existing Select AI objects ===
SELECT profile_name, status, description
  FROM user_cloud_ai_profiles
 WHERE UPPER(profile_name) IN ({profile_predicate})
 ORDER BY profile_name;

SELECT profile_name, attribute_name, attribute_value
  FROM user_cloud_ai_profile_attributes
 WHERE UPPER(profile_name) IN ({profile_predicate})
 ORDER BY profile_name, attribute_name;

PROMPT === Target schema metadata coverage ===
SELECT COUNT(*) AS table_count,
       SUM(CASE WHEN tc.comments IS NOT NULL THEN 1 ELSE 0 END) AS tables_with_comments
  FROM all_tables t
  LEFT JOIN all_tab_comments tc
    ON tc.owner = t.owner AND tc.table_name = t.table_name
 WHERE t.owner = '{owner}';

SELECT COUNT(*) AS column_count,
       SUM(CASE WHEN cc.comments IS NOT NULL THEN 1 ELSE 0 END) AS columns_with_comments
  FROM all_tab_columns c
  LEFT JOIN all_col_comments cc
    ON cc.owner = c.owner
   AND cc.table_name = c.table_name
   AND cc.column_name = c.column_name
 WHERE c.owner = '{owner}';

SELECT constraint_type, COUNT(*) AS constraint_count
  FROM all_constraints
 WHERE owner = '{owner}'
   AND constraint_type IN ('P','U','R','C')
 GROUP BY constraint_type
 ORDER BY constraint_type;
{rag_checks}
PROMPT Review all results before running setup files.
"""


def smoke_sql(nl_name: str, nl_prompt: str, run_sql: bool, rag_name: str | None, rag_prompt: str | None) -> str:
    run_line = (
        f"SELECT AI RUNSQL {nl_prompt};"
        if run_sql
        else f"-- SELECT AI RUNSQL {nl_prompt};  -- enable only after reviewing SHOWSQL output"
    )
    rag_part = ""
    if rag_name and rag_prompt:
        rag_part = f"""
PROMPT === RAG profile inspection ===
SELECT profile_name, status, description
  FROM user_cloud_ai_profiles
 WHERE UPPER(profile_name) = UPPER('{rag_name}');

SELECT profile_name, attribute_name, attribute_value
  FROM user_cloud_ai_profile_attributes
 WHERE UPPER(profile_name) = UPPER('{rag_name}')
 ORDER BY attribute_name;

PROMPT === RAG prompt construction ===
SELECT DBMS_CLOUD_AI.GENERATE(
         prompt       => {q_literal(rag_prompt)},
         profile_name => '{rag_name}',
         action       => 'showprompt') AS rag_prompt
  FROM dual;

PROMPT === RAG grounded answer ===
SELECT DBMS_CLOUD_AI.GENERATE(
         prompt       => {q_literal(rag_prompt)},
         profile_name => '{rag_name}',
         action       => 'narrate') AS rag_answer
  FROM dual;
"""
    return f"""-- Generated smoke tests. These calls invoke the configured AI provider.
SET SERVEROUTPUT ON SIZE UNLIMITED
SET LONG 1000000
SET LONGCHUNKSIZE 1000000
SET PAGESIZE 50000
SET LINESIZE 32767

PROMPT === NL2SQL profile inspection ===
SELECT profile_name, status, description
  FROM user_cloud_ai_profiles
 WHERE UPPER(profile_name) = UPPER('{nl_name}');

SELECT profile_name, attribute_name, attribute_value
  FROM user_cloud_ai_profile_attributes
 WHERE UPPER(profile_name) = UPPER('{nl_name}')
 ORDER BY attribute_name;

PROMPT === Session-based SQLcl test ===
BEGIN
  DBMS_CLOUD_AI.SET_PROFILE(profile_name => '{nl_name}');
END;
/

SELECT AI SHOWPROMPT {nl_prompt};
SELECT AI SHOWSQL {nl_prompt};
{run_line}

PROMPT === Stateless test for Database Actions, APEX, and connection pools ===
SELECT DBMS_CLOUD_AI.GENERATE(
         prompt       => {q_literal(nl_prompt)},
         profile_name => '{nl_name}',
         action       => 'showsql') AS generated_sql
  FROM dual;
{rag_part}
PROMPT Smoke tests complete. Inspect generated SQL, prompt metadata, answer grounding, and citations.
"""


def verify_sql(nl_name: str, rag_name: str | None, index_name: str | None) -> str:
    names = [nl_name] + ([rag_name] if rag_name else [])
    profile_in = ", ".join(sql_literal(name) for name in names)
    vector_part = ""
    if index_name:
        vector_part = f"""
PROMPT @@SECTION:vector_index
SELECT index_name, status, description, created, last_modified
  FROM user_cloud_vector_indexes
 WHERE UPPER(index_name) = UPPER('{index_name}');
PROMPT @@END_SECTION

PROMPT @@SECTION:vector_index_attributes
SELECT index_name, attribute_name, attribute_value, last_modified
  FROM user_cloud_vector_index_attributes
 WHERE UPPER(index_name) = UPPER('{index_name}')
 ORDER BY attribute_name;
PROMPT @@END_SECTION
"""
    return f"""-- Post-setup evidence collector for SQLcl
SET FEEDBACK OFF
SET VERIFY OFF
SET HEADING ON
SET PAGESIZE 50000
SET LINESIZE 32767
SET LONG 200000
SET LONGCHUNKSIZE 200000
SET SQLFORMAT CSV

SPOOL select_ai_setup_verification.out REPLACE
PROMPT @@SELECT_AI_SETUP_VERIFIER_VERSION:1
PROMPT @@SECTION:profiles
SELECT profile_name, status, description, created, last_modified
  FROM user_cloud_ai_profiles
 WHERE profile_name IN ({profile_in})
 ORDER BY profile_name;
PROMPT @@END_SECTION

PROMPT @@SECTION:profile_attributes
SELECT profile_name, attribute_name, attribute_value, last_modified
  FROM user_cloud_ai_profile_attributes
 WHERE profile_name IN ({profile_in})
 ORDER BY profile_name, attribute_name;
PROMPT @@END_SECTION
{vector_part}
PROMPT @@END_SELECT_AI_SETUP_VERIFIER
SPOOL OFF
"""


def rollback_sql(nl_name: str, rag_name: str | None, index_name: str | None) -> str:
    lines = [
        "-- Destructive rollback template. Review and uncomment only when appropriate.",
        "-- BEGIN",
    ]
    if index_name:
        lines.append(
            f"--   DBMS_CLOUD_AI.DROP_VECTOR_INDEX(index_name => '{index_name}', force => TRUE);"
        )
    if rag_name:
        lines.append(f"--   DBMS_CLOUD_AI.DROP_PROFILE(profile_name => '{rag_name}', force => TRUE);")
    lines.append(f"--   DBMS_CLOUD_AI.DROP_PROFILE(profile_name => '{nl_name}', force => TRUE);")
    lines.extend(["-- END;", "-- /", ""])
    return "\n".join(lines)


def write_file(outdir: Path, name: str, text: str) -> None:
    path = outdir / name
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    print(path)


def build(config: Mapping[str, Any], outdir: Path, replace: bool) -> None:
    validate_no_secrets(config)
    owner = validate_identifier(require_str(config, "schema_owner", "config"), "schema_owner")

    nl = config.get("nl2sql_profile")
    if not isinstance(nl, dict):
        fail("config.nl2sql_profile must be an object")
    nl_name = validate_identifier(require_str(nl, "name", "nl2sql_profile"), "nl2sql profile name")
    nl_attrs = make_profile_attributes(nl, owner, include_objects=True)

    rag = config.get("rag", {})
    if rag is None:
        rag = {}
    if not isinstance(rag, dict):
        fail("config.rag must be an object")
    rag_enabled = bool_value(rag, "enabled", False)
    rag_name: str | None = None
    index_name: str | None = None
    rag_profile_sql = ""
    vector_sql = ""
    attach_sql = "-- RAG is disabled in the configuration.\n"
    if rag_enabled:
        rag_name = validate_identifier(require_str(rag, "profile_name", "rag"), "RAG profile name")
        index_name = validate_identifier(require_str(rag, "index_name", "rag"), "RAG index name")
        rag_attrs = make_profile_attributes(rag, owner, include_objects=False)
        if "embedding_model" not in rag_attrs:
            fail("rag.embedding_model is required for Select AI RAG")
        rag_profile_sql = profile_block(
            rag_name,
            str(rag.get("profile_description", "Select AI RAG profile")),
            rag_attrs,
            replace,
        )
        vector_sql = vector_index_block(rag, rag_name, replace)
        attach_sql = f"""BEGIN
  DBMS_CLOUD_AI.SET_ATTRIBUTE(
    profile_name    => '{rag_name}',
    attribute_name  => 'vector_index_name',
    attribute_value => '{index_name}'
  );
END;
/
"""

    smoke = config.get("smoke_tests", {})
    if not isinstance(smoke, dict):
        fail("config.smoke_tests must be an object")
    nl_prompt = str(smoke.get("nl2sql_prompt", "How many rows are in each table?"))
    rag_prompt = str(smoke.get("rag_prompt", "Summarize the indexed documents with sources."))
    run_sql = bool_value(smoke, "run_sql", False)

    outdir.mkdir(parents=True, exist_ok=True)
    write_file(outdir, "01_preflight.sql", preflight_sql(owner, nl_name, rag_name, index_name))
    write_file(
        outdir,
        "02_create_nl2sql_profile.sql",
        "SET SERVEROUTPUT ON SIZE UNLIMITED\n" + profile_block(
            nl_name,
            str(nl.get("description", "Select AI NL2SQL profile")),
            nl_attrs,
            replace,
        ),
    )
    write_file(
        outdir,
        "03_create_rag_profile.sql",
        "SET SERVEROUTPUT ON SIZE UNLIMITED\n" + (rag_profile_sql or "-- RAG is disabled.\n"),
    )
    write_file(
        outdir,
        "04_create_vector_index.sql",
        "SET SERVEROUTPUT ON SIZE UNLIMITED\n" + (vector_sql or "-- RAG is disabled.\n"),
    )
    write_file(outdir, "05_attach_vector_index.sql", attach_sql)
    write_file(outdir, "06_smoke_test.sql", smoke_sql(nl_name, nl_prompt, run_sql, rag_name, rag_prompt if rag_enabled else None))
    write_file(outdir, "07_collect_verification.sql", verify_sql(nl_name, rag_name, index_name))
    write_file(outdir, "99_rollback_template.sql", rollback_sql(nl_name, rag_name, index_name))
    write_file(
        outdir,
        "README.txt",
        "Run in order after review:\n"
        "  01_preflight.sql\n"
        "  02_create_nl2sql_profile.sql\n"
        "  03_create_rag_profile.sql (when enabled)\n"
        "  04_create_vector_index.sql (when enabled)\n"
        "  05_attach_vector_index.sql (when enabled)\n"
        "  06_smoke_test.sql\n"
        "  07_collect_verification.sql\n\n"
        "Do not run 99_rollback_template.sql without deliberate review.\n"
        "Credential objects must already exist. No secret values are generated.\n",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="JSON configuration file")
    parser.add_argument("--output-dir", type=Path, default=Path("generated_select_ai_setup"))
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Generate DROP/CREATE blocks instead of safe create-if-absent blocks",
    )
    args = parser.parse_args(argv)
    try:
        build(load_json(args.config), args.output_dir, args.replace_existing)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
