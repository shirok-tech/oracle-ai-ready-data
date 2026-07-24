#!/usr/bin/env python3
"""Assess Oracle Select AI, RAG, Vector Search, and Agent feature readiness."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Mapping, Sequence, Set


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_sections(text: str) -> Mapping[str, List[str]]:
    sections: DefaultDict[str, List[str]] = defaultdict(list)
    current = None
    for raw in text.splitlines():
        line = raw.rstrip("\r\n")
        if line.startswith("@@SECTION:"):
            current = line.split(":", 1)[1].strip()
            sections[current] = []
        elif line.startswith("@@END_SECTION"):
            current = None
        elif current is not None and line.strip() and not line.startswith("PL/SQL procedure"):
            sections[current].append(line)
    return sections


def rows(lines: List[str]) -> List[Dict[str, str]]:
    if not lines:
        return []
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    return [
        {str(k).strip().upper(): (v or "").strip() for k, v in row.items() if k is not None}
        for row in reader
    ]


def package_names(sections: Mapping[str, List[str]]) -> Set[str]:
    names: Set[str] = set()
    for section in ("package_objects", "package_synonyms"):
        for row in rows(sections.get(section, [])):
            name = row.get("OBJECT_NAME") or row.get("SYNONYM_NAME") or row.get("TABLE_NAME")
            if name:
                names.add(name.upper())
    return names


def procedure_names(sections: Mapping[str, List[str]], package: str) -> Set[str]:
    return {
        row.get("PROCEDURE_NAME", "").upper()
        for row in rows(sections.get("package_subprograms", []))
        if row.get("OBJECT_NAME", "").upper() == package.upper()
        and row.get("PROCEDURE_NAME", "") not in {"", "(package)"}
    }


def ok_rows(section_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [row for row in section_rows if row.get("PROBE_STATUS", "OK").upper() == "OK"]


def attr_map(section_rows: List[Dict[str, str]], object_key: str) -> Dict[str, Dict[str, str]]:
    result: Dict[str, Dict[str, str]] = defaultdict(dict)
    for row in ok_rows(section_rows):
        object_name = row.get(object_key, "").upper()
        attr = row.get("ATTRIBUTE_NAME", "").lower()
        if object_name and attr:
            result[object_name][attr] = row.get("ATTRIBUTE_VALUE", "")
    return dict(result)


def evaluate(sections: Mapping[str, List[str]]) -> Dict[str, object]:
    packages = package_names(sections)
    cloud_ai_procs = procedure_names(sections, "DBMS_CLOUD_AI")
    agent_procs = procedure_names(sections, "DBMS_CLOUD_AI_AGENT")
    profiles = [row for row in ok_rows(rows(sections.get("ai_profiles", []))) if row.get("PROFILE_NAME")]
    profile_attrs = attr_map(rows(sections.get("ai_profile_attributes", [])), "PROFILE_NAME")
    cloud_indexes = [row for row in ok_rows(rows(sections.get("cloud_vector_indexes", []))) if row.get("INDEX_NAME")]
    vector_attrs = attr_map(rows(sections.get("cloud_vector_index_attributes", [])), "INDEX_NAME")
    credentials = [row for row in ok_rows(rows(sections.get("user_credentials", []))) if row.get("CREDENTIAL_NAME")]
    vector_columns = rows(sections.get("target_vector_columns", []))
    native_indexes = rows(sections.get("native_vector_indexes", []))
    context = rows(sections.get("run_context", []))

    cloud_ai = "DBMS_CLOUD_AI" in packages
    cloud_agent = "DBMS_CLOUD_AI_AGENT" in packages
    native_vector = bool({"DBMS_VECTOR", "DBMS_VECTOR_CHAIN"} & packages) or bool(vector_columns) or bool(native_indexes)
    has_profile = bool(profiles)
    has_credential = bool(credentials)
    has_vector_index = bool(cloud_indexes)
    has_rag_profile = any(
        attrs.get("embedding_model") and attrs.get("vector_index_name")
        for attrs in profile_attrs.values()
    )

    def status(available: bool, configured: bool, prerequisites: bool = True) -> str:
        if not available:
            return "not detected"
        if not prerequisites:
            return "blocked by prerequisite"
        return "ready-looking" if configured else "available; setup required"

    features = [
        ("Select AI / NL2SQL", status(cloud_ai and "CREATE_PROFILE" in cloud_ai_procs, has_profile and has_credential)),
        ("Select AI RAG", status(cloud_ai and "CREATE_VECTOR_INDEX" in cloud_ai_procs, has_rag_profile and has_vector_index, has_profile and has_credential)),
        ("Oracle AI Vector Search", status(native_vector or "CREATE_VECTOR_INDEX" in cloud_ai_procs, bool(vector_columns or native_indexes or cloud_indexes))),
        ("Select AI Agent - SQL tool", status(cloud_agent and "CREATE_AGENT" in agent_procs, False, has_profile)),
        ("Select AI Agent - RAG tool", status(cloud_agent and "CREATE_AGENT" in agent_procs, False, has_rag_profile and has_vector_index)),
        ("Synthetic Data Generation", status(cloud_ai and "GENERATE_SYNTHETIC_DATA" in cloud_ai_procs, has_profile)),
        ("NL2SQL Feedback", status(cloud_ai and "FEEDBACK" in cloud_ai_procs, has_profile)),
        ("Auto Object Selection", status(cloud_ai and "CREATE_PROFILE" in cloud_ai_procs, any(attrs.get("object_list_mode", "").lower() == "automated" for attrs in profile_attrs.values()))),
    ]
    points = {"ready-looking": 1.0, "available; setup required": 0.6, "blocked by prerequisite": 0.35, "not detected": 0.0}
    weights = [0.25, 0.20, 0.15, 0.15, 0.10, 0.08, 0.04, 0.03]
    score_value = sum(points[state] * weight for (_, state), weight in zip(features, weights))
    return {
        "context": context[0] if context else {},
        "packages": sorted(packages),
        "cloud_ai_procs": sorted(cloud_ai_procs),
        "agent_procs": sorted(agent_procs),
        "profiles": profiles,
        "profile_attrs": profile_attrs,
        "cloud_indexes": cloud_indexes,
        "vector_attrs": vector_attrs,
        "credentials": credentials,
        "features": features,
        "score": score_value,
        "cloud_ai": cloud_ai,
        "create_profile": "CREATE_PROFILE" in cloud_ai_procs,
        "create_vector_index": "CREATE_VECTOR_INDEX" in cloud_ai_procs,
    }


def render(result: Mapping[str, object], language: str) -> str:
    features = result["features"]
    assert isinstance(features, list)
    if language == "ja":
        title = "Oracle AI Feature Readiness"
        summary = "機能の存在と、実際に利用できる設定状態を分けて判定します。"
    else:
        title = "Oracle AI Feature Readiness"
        summary = "Feature presence and usable configuration are evaluated separately."
    lines = [
        f"# {title}",
        "",
        summary,
        "",
        f"- Score: **{float(result['score']):.2f} / 1.00**",
        f"- Visible packages: {', '.join(result['packages']) or 'none'}",
        f"- AI profiles: {len(result['profiles'])}",
        f"- Cloud vector indexes: {len(result['cloud_indexes'])}",
        f"- Visible credential objects: {len(result['credentials'])}",
        "",
        "## Feature status",
        "",
        "| Feature | Status |",
        "|---|---|",
    ]
    for name, state in features:
        lines.append(f"| {name} | {state} |")
    lines.extend(["", "## Existing profile metadata", ""])
    profile_attrs = result["profile_attrs"]
    assert isinstance(profile_attrs, dict)
    if not profile_attrs:
        lines.append("No AI profile attributes were detected.")
    else:
        lines.extend(["| Profile | Metadata enrichment | RAG linkage |", "|---|---|---|"])
        for name, attrs in sorted(profile_attrs.items()):
            enrichment = ", ".join(
                f"{key}={attrs.get(key, 'missing')}" for key in ("comments", "annotations", "constraints")
            )
            rag = ", ".join(
                f"{key}={attrs.get(key, 'missing')}" for key in ("embedding_model", "vector_index_name")
            )
            lines.append(f"| {name} | {enrichment} | {rag} |")
    lines.extend(
        [
            "",
            "## Recommended next step",
            "",
            "Review the generated JSON configuration, then run `scripts/generate_select_ai_setup.py` to create preflight, profile, vector-index, smoke-test, verification, and rollback SQL files. Runtime smoke tests are required before calling the environment ready.",
            "",
        ]
    )
    return "\n".join(lines)


def setup_template(result: Mapping[str, object]) -> str:
    context = result.get("context", {})
    owner = "TARGET_SCHEMA"
    if isinstance(context, dict):
        owner = context.get("TARGET_OWNER", owner) or owner
    lines = [
        "-- Compatibility setup template generated from feature readiness evidence.",
        "-- Prefer scripts/generate_select_ai_setup.py with a reviewed JSON config.",
        "-- No secret values belong in this file; reference Oracle credential objects by name.",
        "",
    ]
    if not result.get("cloud_ai") or not result.get("create_profile"):
        lines.append("-- DBMS_CLOUD_AI.CREATE_PROFILE was not visible. Check service support and privileges first.")
        return "\n".join(lines) + "\n"
    lines.extend(
        [
            "BEGIN",
            "  DBMS_CLOUD_AI.CREATE_PROFILE(",
            "    profile_name => 'REPLACE_NL2SQL_PROFILE',",
            "    status       => 'enabled',",
            "    description  => 'Reviewed NL2SQL profile',",
            "    attributes   => JSON_OBJECT(",
            "      'provider' VALUE 'REPLACE_PROVIDER',",
            "      'credential_name' VALUE 'REPLACE_CREDENTIAL_OBJECT',",
            "      'model' VALUE 'REPLACE_SUPPORTED_MODEL',",
            f"      'object_list' VALUE JSON_ARRAY(JSON_OBJECT('owner' VALUE '{owner}')),",
            "      'comments' VALUE true,",
            "      'annotations' VALUE true,",
            "      'constraints' VALUE true,",
            "      'enforce_object_list' VALUE true",
            "    )",
            "  );",
            "END;",
            "/",
            "",
        ]
    )
    if result.get("create_vector_index"):
        lines.extend(
            [
                "-- RAG requires a real document source and a separate reviewed profile.",
                "-- In CREATE_VECTOR_INDEX, enable_sources belongs to vector-index attributes,",
                "-- not to DBMS_CLOUD_AI.SET_ATTRIBUTE on the AI profile.",
                "-- Generate the complete RAG SQL with generate_select_ai_setup.py.",
                "",
            ]
        )
    return "\n".join(lines)


def write_config_skeleton(result: Mapping[str, object], path: Path) -> None:
    context = result.get("context", {})
    owner = "TARGET_SCHEMA"
    if isinstance(context, dict):
        owner = context.get("TARGET_OWNER", owner) or owner
    config = {
        "schema_owner": owner,
        "nl2sql_profile": {
            "name": f"{owner}_NL2SQL",
            "provider": "oci",
            "credential_name": "REPLACE_CREDENTIAL_OBJECT",
            "model": "REPLACE_SUPPORTED_CHAT_MODEL",
            "region": "REPLACE_REGION",
            "object_list": [{"owner": owner}],
            "comments": True,
            "annotations": True,
            "constraints": True,
            "enforce_object_list": True,
            "additional_instructions": "Use documented business definitions and generate read-only SQL.",
        },
        "rag": {
            "enabled": False,
            "profile_name": f"{owner}_RAG",
            "provider": "oci",
            "credential_name": "REPLACE_CREDENTIAL_OBJECT",
            "model": "REPLACE_SUPPORTED_CHAT_MODEL",
            "embedding_model": "REPLACE_SUPPORTED_EMBEDDING_MODEL",
            "index_name": f"{owner}_DOCS_VECIDX",
            "location": "REPLACE_DIRECTORY_OR_OBJECT_STORAGE_URI",
            "object_storage_credential_name": "REPLACE_OBJECT_STORAGE_CREDENTIAL",
            "enable_sources": True,
        },
        "smoke_tests": {
            "nl2sql_prompt": "How many rows are in each relevant table?",
            "rag_prompt": "Summarize the indexed documents and include sources.",
            "run_sql": False,
        },
    }
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spool", type=Path)
    parser.add_argument("--language", choices=["en", "ja"], default="en")
    parser.add_argument("--output", type=Path, default=Path("oracle_ai_feature_readiness.md"))
    parser.add_argument("--sql-output", type=Path, default=Path("oracle_ai_feature_setup.sql"))
    parser.add_argument("--config-output", type=Path)
    parser.add_argument("--setup-config", type=Path)
    parser.add_argument("--setup-dir", type=Path)
    parser.add_argument("--replace-existing", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = evaluate(parse_sections(read_text(args.spool)))
        args.output.write_text(render(result, args.language), encoding="utf-8")
        args.sql_output.write_text(setup_template(result), encoding="utf-8")
        if args.config_output:
            write_config_skeleton(result, args.config_output)
        if bool(args.setup_config) != bool(args.setup_dir):
            raise ValueError("--setup-config and --setup-dir must be supplied together")
        if args.setup_config and args.setup_dir:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from generate_select_ai_setup import build, load_json

            build(load_json(args.setup_config), args.setup_dir, args.replace_existing)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(args.output)
    print(args.sql_output)
    if args.config_output:
        print(args.config_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
