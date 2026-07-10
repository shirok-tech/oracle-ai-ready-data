#!/usr/bin/env python3
"""Score Oracle schema metadata collected by oracle_ai_ready_collect.sql."""

from __future__ import annotations

import argparse
import csv
import io
import sys
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Mapping, Sequence, Set, Tuple


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
        elif current is not None and line.strip():
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


def key(row: Mapping[str, str]) -> Tuple[str, str]:
    return row.get("OWNER", ""), row.get("TABLE_NAME", "")


def pct(numerator: int, denominator: int) -> float:
    return 1.0 if denominator == 0 else numerator / denominator


def quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def evaluate(sections: Mapping[str, List[str]], profile: str) -> Dict[str, object]:
    table_rows = rows(sections.get("table_inventory", []))
    column_rows = rows(sections.get("column_inventory", []))
    table_comments = rows(sections.get("table_comments", []))
    column_comments = rows(sections.get("column_comments", []))
    constraint_rows = rows(sections.get("constraints", []))
    rag_rows = rows(sections.get("rag_candidate_columns", []))
    freshness_rows = rows(sections.get("freshness_columns", []))
    source_rows = rows(sections.get("source_metadata_columns", []))
    sensitive_rows = rows(sections.get("sensitive_candidate_columns", []))
    grant_rows = rows(sections.get("object_grants", []))
    context = rows(sections.get("run_context", []))

    tables: Set[Tuple[str, str]] = {key(row) for row in table_rows if row.get("TABLE_NAME")}
    columns: Set[Tuple[str, str, str]] = {
        (row.get("OWNER", ""), row.get("TABLE_NAME", ""), row.get("COLUMN_NAME", ""))
        for row in column_rows
        if row.get("COLUMN_NAME")
    }
    commented_tables = {key(row) for row in table_comments if row.get("COMMENTS")}
    commented_columns = {
        (row.get("OWNER", ""), row.get("TABLE_NAME", ""), row.get("COLUMN_NAME", ""))
        for row in column_comments
        if row.get("COMMENTS")
    }
    pk_tables = {key(row) for row in constraint_rows if row.get("CONSTRAINT_TYPE") == "P" and row.get("STATUS", "ENABLED") == "ENABLED"}
    fk_tables = {key(row) for row in constraint_rows if row.get("CONSTRAINT_TYPE") == "R" and row.get("STATUS", "ENABLED") == "ENABLED"}
    constrained_tables = {key(row) for row in constraint_rows if row.get("CONSTRAINT_TYPE") in {"P", "U", "R", "C"}}
    analyzed_tables = {key(row) for row in table_rows if row.get("LAST_ANALYZED")}
    analyzed_columns = {
        (row.get("OWNER", ""), row.get("TABLE_NAME", ""), row.get("COLUMN_NAME", ""))
        for row in column_rows
        if row.get("LAST_ANALYZED")
    }
    text_tables = {key(row) for row in rag_rows if row.get("AI_CANDIDATE_TYPE") in {"text", "long_text"}}
    vector_tables = {key(row) for row in rag_rows if row.get("AI_CANDIDATE_TYPE") == "vector"}
    freshness_tables = {key(row) for row in freshness_rows}
    source_tables = {key(row) for row in source_rows}
    sensitive_columns = {
        (row.get("OWNER", ""), row.get("TABLE_NAME", ""), row.get("COLUMN_NAME", ""))
        for row in sensitive_rows
    }
    sensitive_documented = sensitive_columns & commented_columns
    broad_grants = [
        row
        for row in grant_rows
        if row.get("GRANTEE", "").upper() in {"PUBLIC", "ANONYMOUS"}
        or row.get("GRANTEE", "").upper().endswith("_ROLE")
    ]

    metrics = {
        "table_comment_coverage": pct(len(commented_tables & tables), len(tables)),
        "column_comment_coverage": pct(len(commented_columns & columns), len(columns)),
        "pk_coverage": pct(len(pk_tables & tables), len(tables)),
        "fk_coverage": pct(len(fk_tables & tables), len(tables)),
        "relationship_coverage": pct(len((pk_tables | fk_tables) & tables), len(tables)),
        "constraint_coverage": pct(len(constrained_tables & tables), len(tables)),
        "table_stats_coverage": pct(len(analyzed_tables & tables), len(tables)),
        "column_stats_coverage": pct(len(analyzed_columns & columns), len(columns)),
        "freshness_coverage": pct(len(freshness_tables & tables), len(tables)),
        "source_metadata_coverage": pct(len(source_tables & tables), len(tables)),
        "text_table_coverage": pct(len(text_tables & tables), len(tables)),
        "vector_table_coverage": pct(len(vector_tables & tables), len(tables)),
        "sensitive_documentation": pct(len(sensitive_documented), len(sensitive_columns)),
        "broad_grant_absence": 1.0 if not broad_grants else 0.0,
    }

    if profile == "rag":
        weights = {
            "table_comment_coverage": 0.12,
            "column_comment_coverage": 0.12,
            "pk_coverage": 0.08,
            "relationship_coverage": 0.08,
            "constraint_coverage": 0.05,
            "table_stats_coverage": 0.05,
            "column_stats_coverage": 0.05,
            "freshness_coverage": 0.08,
            "source_metadata_coverage": 0.08,
            "text_table_coverage": 0.12,
            "vector_table_coverage": 0.08,
            "sensitive_documentation": 0.05,
            "broad_grant_absence": 0.04,
        }
    else:
        weights = {
            "table_comment_coverage": 0.15,
            "column_comment_coverage": 0.15,
            "pk_coverage": 0.10,
            "relationship_coverage": 0.10,
            "constraint_coverage": 0.08,
            "table_stats_coverage": 0.08,
            "column_stats_coverage": 0.06,
            "freshness_coverage": 0.08,
            "source_metadata_coverage": 0.05,
            "text_table_coverage": 0.03,
            "vector_table_coverage": 0.02,
            "sensitive_documentation": 0.05,
            "broad_grant_absence": 0.05,
        }
    score = sum(metrics[name] * weight for name, weight in weights.items())
    comment_gate = metrics["table_comment_coverage"] == 1.0 and metrics["column_comment_coverage"] == 1.0
    return {
        "context": context[0] if context else {},
        "tables": tables,
        "columns": columns,
        "commented_tables": commented_tables,
        "commented_columns": commented_columns,
        "metrics": metrics,
        "score": score,
        "comment_gate": comment_gate,
        "broad_grants": broad_grants,
    }


def render(result: Mapping[str, object], profile: str, language: str) -> str:
    metrics = result["metrics"]
    assert isinstance(metrics, dict)
    score = float(result["score"])
    gate = bool(result["comment_gate"])
    if language == "ja":
        title = "Oracle AI Ready Data 評価"
        gate_text = "pass" if gate else "fail"
        conclusion = "PoC候補" if gate and score >= 0.6 else "改善後に再評価"
        headings = ("概要", "メトリクス", "優先アクション")
    else:
        title = "Oracle AI Ready Data Assessment"
        gate_text = "pass" if gate else "fail"
        conclusion = "PoC candidate" if gate and score >= 0.6 else "Improve and reassess"
        headings = ("Summary", "Metrics", "Priority actions")
    lines = [
        f"# {title}",
        "",
        f"## {headings[0]}",
        "",
        f"- Profile: `{profile}`",
        f"- Score: **{score:.2f} / 1.00**",
        f"- Mandatory comment gate: **{gate_text}**",
        f"- Conclusion: **{conclusion}**",
        f"- Tables: {len(result['tables'])}",
        f"- Columns: {len(result['columns'])}",
        "",
        f"## {headings[1]}",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for name, value in metrics.items():
        lines.append(f"| {name} | {float(value) * 100:.1f}% |")
    actions: List[str] = []
    if not gate:
        actions.append("Add complete table and column comments before relying on NL2SQL metadata enrichment.")
    if float(metrics["relationship_coverage"]) < 1.0:
        actions.append("Review missing PK/FK relationships and expose safe semantic views when physical constraints cannot be added.")
    if float(metrics["table_stats_coverage"]) < 1.0:
        actions.append("Review optimizer statistics collection with the DBA/application owner.")
    if profile == "rag" and float(metrics["text_table_coverage"]) == 0.0:
        actions.append("Do not treat relational HR tables as a document corpus; define document sources, chunking, embeddings, and a managed vector index separately.")
    if not actions:
        actions.append("Proceed to Select AI profile creation and runtime smoke tests.")
    lines.extend(["", f"## {headings[2]}", ""])
    lines.extend(f"- {action}" for action in actions)
    lines.append("")
    return "\n".join(lines)


def improvement_sql(result: Mapping[str, object]) -> str:
    tables = result["tables"]
    columns = result["columns"]
    commented_tables = result["commented_tables"]
    commented_columns = result["commented_columns"]
    lines = [
        "-- Review-before-run metadata improvement SQL.",
        "-- Replace TODO text with accurate business definitions.",
        "",
    ]
    for owner, table in sorted(tables - commented_tables):
        lines.append(
            f"COMMENT ON TABLE {quote_ident(owner)}.{quote_ident(table)} IS "
            "'TODO: business meaning, row grain, freshness, and intended AI use.';"
        )
    for owner, table, column in sorted(columns - commented_columns):
        lines.append(
            f"COMMENT ON COLUMN {quote_ident(owner)}.{quote_ident(table)}.{quote_ident(column)} IS "
            "'TODO: meaning, units, null semantics, allowed values, and sensitivity.';"
        )
    if len(lines) == 3:
        lines.append("-- No missing table or column comments were detected.")
    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spool", type=Path)
    parser.add_argument("--profile", choices=["scan", "rag"], default="scan")
    parser.add_argument("--language", choices=["en", "ja"], default="en")
    parser.add_argument("--output", type=Path, default=Path("oracle_ai_ready_report.md"))
    parser.add_argument("--sql-output", type=Path, default=Path("oracle_ai_ready_improvement.sql"))
    args = parser.parse_args(argv)
    try:
        result = evaluate(parse_sections(read_text(args.spool)), args.profile)
        args.output.write_text(render(result, args.profile, args.language), encoding="utf-8")
        args.sql_output.write_text(improvement_sql(result), encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(args.output)
    print(args.sql_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
