#!/usr/bin/env python3
"""Score post-setup Select AI and RAG verification output from SQLcl."""

from __future__ import annotations

import argparse
import csv
import io
import sys
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Mapping, Sequence


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_sections(text: str) -> Mapping[str, List[str]]:
    sections: DefaultDict[str, List[str]] = defaultdict(list)
    current: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip("\r\n")
        if line.startswith("@@SECTION:"):
            current = line.split(":", 1)[1].strip()
            sections[current] = []
            continue
        if line.startswith("@@END_SECTION"):
            current = None
            continue
        if current is not None and line.strip():
            sections[current].append(line)
    return sections


def csv_rows(lines: List[str]) -> List[Dict[str, str]]:
    if not lines:
        return []
    cleaned = [line for line in lines if not line.startswith("PL/SQL procedure")]
    if not cleaned:
        return []
    reader = csv.DictReader(io.StringIO("\n".join(cleaned)))
    return [
        {str(k).strip().upper(): (v or "").strip() for k, v in row.items() if k is not None}
        for row in reader
    ]


def truthy(value: str) -> bool:
    return value.strip().lower() in {"true", "yes", "y", "1", "enabled"}


def attr_map(rows: List[Dict[str, str]], key_name: str) -> Dict[str, Dict[str, str]]:
    result: Dict[str, Dict[str, str]] = defaultdict(dict)
    for row in rows:
        object_name = row.get(key_name, "").upper()
        attr = row.get("ATTRIBUTE_NAME", "").lower()
        if object_name and attr:
            result[object_name][attr] = row.get("ATTRIBUTE_VALUE", "")
    return dict(result)


def add_check(checks: List[Dict[str, str]], area: str, name: str, status: str, evidence: str, action: str = "") -> None:
    checks.append(
        {
            "area": area,
            "check": name,
            "status": status,
            "evidence": evidence or "-",
            "action": action or "-",
        }
    )


def profile_status(rows: List[Dict[str, str]], name: str) -> str:
    for row in rows:
        if row.get("PROFILE_NAME", "").upper() == name.upper():
            return row.get("STATUS", "")
    return ""


def score(
    sections: Mapping[str, List[str]],
    nl_profile: str,
    rag_profile: str | None,
    vector_index: str | None,
) -> List[Dict[str, str]]:
    profiles = csv_rows(sections.get("profiles", []))
    profile_attrs = attr_map(csv_rows(sections.get("profile_attributes", [])), "PROFILE_NAME")
    vector_rows = csv_rows(sections.get("vector_index", []))
    vector_attrs = attr_map(csv_rows(sections.get("vector_index_attributes", [])), "INDEX_NAME")
    checks: List[Dict[str, str]] = []

    nl = nl_profile.upper()
    nl_status = profile_status(profiles, nl)
    add_check(
        checks,
        "NL2SQL",
        "Profile exists and is enabled",
        "pass" if nl_status.upper() == "ENABLED" else "fail",
        nl_status or "not found",
        "Create or enable the NL2SQL profile" if nl_status.upper() != "ENABLED" else "",
    )
    attrs = profile_attrs.get(nl, {})
    for attr in ("provider", "credential_name"):
        add_check(
            checks,
            "NL2SQL",
            f"Profile attribute: {attr}",
            "pass" if attrs.get(attr) else "fail",
            attrs.get(attr, "missing"),
            f"Set {attr} on the NL2SQL profile" if not attrs.get(attr) else "",
        )
    for attr in ("comments", "annotations", "constraints"):
        add_check(
            checks,
            "NL2SQL metadata",
            f"{attr}=true",
            "pass" if truthy(attrs.get(attr, "")) else "warn",
            attrs.get(attr, "missing"),
            f"Set {attr}=true and verify SHOWPROMPT contains the expected metadata"
            if not truthy(attrs.get(attr, ""))
            else "",
        )
    object_scope = attrs.get("object_list") or attrs.get("object_list_mode")
    add_check(
        checks,
        "NL2SQL safety",
        "Object scope configured",
        "pass" if object_scope else "warn",
        object_scope or "missing",
        "" if object_scope else "Set object_list or use object_list_mode=automated",
    )
    add_check(
        checks,
        "NL2SQL safety",
        "enforce_object_list=true",
        "pass" if truthy(attrs.get("enforce_object_list", "")) else "warn",
        attrs.get("enforce_object_list", "missing"),
        "" if truthy(attrs.get("enforce_object_list", "")) else "Enable enforce_object_list for a bounded SQL generation scope",
    )
    model_evidence = attrs.get("model") or attrs.get("oci_endpoint_id") or attrs.get("azure_deployment_name")
    add_check(
        checks,
        "NL2SQL provider",
        "Model or deployment configured",
        "pass" if model_evidence else "warn",
        model_evidence or "not visible",
        "" if model_evidence else "Confirm provider-specific model/deployment requirements",
    )

    if rag_profile:
        rag = rag_profile.upper()
        rag_status = profile_status(profiles, rag)
        add_check(
            checks,
            "RAG",
            "RAG profile exists and is enabled",
            "pass" if rag_status.upper() == "ENABLED" else "fail",
            rag_status or "not found",
            "Create or enable the RAG profile" if rag_status.upper() != "ENABLED" else "",
        )
        rattrs = profile_attrs.get(rag, {})
        for attr in ("provider", "credential_name", "embedding_model", "vector_index_name"):
            add_check(
                checks,
                "RAG",
                f"Profile attribute: {attr}",
                "pass" if rattrs.get(attr) else "fail",
                rattrs.get(attr, "missing"),
                f"Set {attr} on the RAG profile" if not rattrs.get(attr) else "",
            )

    if vector_index:
        idx = vector_index.upper()
        idx_status = ""
        for row in vector_rows:
            if row.get("INDEX_NAME", "").upper() == idx:
                idx_status = row.get("STATUS", "")
                break
        add_check(
            checks,
            "RAG index",
            "Vector index exists and is enabled",
            "pass" if idx_status.upper() == "ENABLED" else "fail",
            idx_status or "not found",
            "Create or enable the vector index" if idx_status.upper() != "ENABLED" else "",
        )
        iattrs = vector_attrs.get(idx, {})
        for attr in ("location", "profile_name", "object_storage_credential_name", "vector_db_provider"):
            add_check(
                checks,
                "RAG index",
                f"Vector index attribute: {attr}",
                "pass" if iattrs.get(attr) else "fail",
                iattrs.get(attr, "missing"),
                f"Set {attr} on the vector index" if not iattrs.get(attr) else "",
            )
        add_check(
            checks,
            "RAG citations",
            "enable_sources=true",
            "pass" if truthy(iattrs.get("enable_sources", "true")) else "warn",
            iattrs.get("enable_sources", "default true / not visible"),
            "" if truthy(iattrs.get("enable_sources", "true")) else "Set enable_sources=true when source attribution is required",
        )
    return checks


def render(checks: List[Dict[str, str]], nl: str, rag: str | None, idx: str | None) -> str:
    counts = {status: sum(1 for item in checks if item["status"] == status) for status in ("pass", "warn", "fail")}
    overall = "fail" if counts["fail"] else ("warn" if counts["warn"] else "pass")
    lines = [
        "# Select AI Setup Verification",
        "",
        f"- Overall: **{overall}**",
        f"- NL2SQL profile: `{nl}`",
        f"- RAG profile: `{rag or 'not requested'}`",
        f"- Vector index: `{idx or 'not requested'}`",
        f"- Checks: pass {counts['pass']}, warn {counts['warn']}, fail {counts['fail']}",
        "",
        "## Check results",
        "",
        "| Area | Check | Status | Evidence | Next action |",
        "|---|---|---:|---|---|",
    ]
    for item in checks:
        values = [item[k].replace("|", "\\|").replace("\n", " ") for k in ("area", "check", "status", "evidence", "action")]
        lines.append("| " + " | ".join(values) + " |")
    lines.extend(
        [
            "",
            "## Runtime validation still required",
            "",
            "This report verifies stored configuration evidence. It does not prove provider connectivity, SQL correctness, document ingestion, retrieval quality, or citations. Run the generated `06_smoke_test.sql`, inspect `SHOWPROMPT` and `SHOWSQL`, and validate grounded RAG answers against known source documents.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spool", type=Path)
    parser.add_argument("--nl2sql-profile", required=True)
    parser.add_argument("--rag-profile")
    parser.add_argument("--vector-index")
    parser.add_argument("--output", type=Path, default=Path("select_ai_setup_verification.md"))
    args = parser.parse_args(argv)
    try:
        sections = parse_sections(read_text(args.spool))
        checks = score(sections, args.nl2sql_profile, args.rag_profile, args.vector_index)
        report = render(checks, args.nl2sql_profile, args.rag_profile, args.vector_index)
        args.output.write_text(report, encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
