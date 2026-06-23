#!/usr/bin/env python3
"""Score Oracle AI-ready metadata collected by oracle_ai_ready_collect.sql.

Input: sectioned CSV output spooled by SQLcl.
Output: Markdown report with mandatory comment gate and improvement SQL.

Compatibility: Python 3.6+ and no third-party dependencies.
"""

import argparse
import csv
import datetime as dt
import io
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Set, Tuple

Row = Dict[str, str]
Key = Tuple[str, str]
ColKey = Tuple[str, str, str]

SECTION_RE = re.compile(r"^@@SECTION:([A-Za-z0-9_]+)\s*$")
END_SECTION_RE = re.compile(r"^@@END_SECTION\s*$")
ROWCOUNT_RE = re.compile(r"^\s*\d+\s+rows?\s+selected\.?\s*$", re.I)

SCAN_WEIGHTS = {
    "clean": 0.20,
    "contextual": 0.25,
    "consumable": 0.15,
    "current": 0.15,
    "correlated": 0.15,
    "compliant": 0.10,
}

RAG_WEIGHTS = {
    "clean": 0.10,
    "contextual": 0.30,
    "consumable": 0.30,
    "current": 0.10,
    "correlated": 0.10,
    "compliant": 0.10,
}

DIMENSION_INFO_JA = {
    "clean": {
        "label": "Clean",
        "meaning": "主キー、制約、統計情報があり、AI処理の前提となる構造的な信頼性を確認します。",
        "why": "キーや統計情報が不足すると、根拠行の特定、結合、品質確認が不安定になります。",
    },
    "contextual": {
        "label": "Contextual",
        "meaning": "テーブル/カラムコメントとリレーション定義により、データの意味が説明できるかを確認します。",
        "why": "AIが列名だけから意味を推測すると誤解しやすいため、コメントを必須ゲートにしています。",
    },
    "consumable": {
        "label": "Consumable",
        "meaning": "AIやRAGパイプラインが利用しやすいテキスト列、VECTOR列、安定ID、ドキュメントを確認します。",
        "why": "検索対象、根拠、embedding管理方法が曖昧だと、RAG/agentの回答品質が安定しません。",
    },
    "current": {
        "label": "Current",
        "meaning": "更新日時などの鮮度列と最近の統計情報があり、データの新しさを説明できるかを確認します。",
        "why": "古いデータや更新時点不明のデータは、AI回答の鮮度リスクになります。",
    },
    "correlated": {
        "label": "Correlated",
        "meaning": "外部キー、主キー、source/update系メタデータにより、他テーブルや元データと関連付けられるかを確認します。",
        "why": "関連が宣言されていないと、AIが表間のつながりを誤解したり、根拠追跡が弱くなります。",
    },
    "compliant": {
        "label": "Compliant",
        "meaning": "機微情報らしい列名、コメント有無、広い権限付与候補を検出し、レビュー可能性を確認します。",
        "why": "この評価は法令遵守を保証しませんが、AI利用前のセキュリティ/プライバシーレビュー対象を明確にします。",
    },
}

DIMENSION_INFO_EN = {
    "clean": {
        "label": "Clean",
        "meaning": "Checks structural reliability through primary keys, constraints, and statistics.",
        "why": "Missing keys or statistics make row grounding, joins, and quality review less stable.",
    },
    "contextual": {
        "label": "Contextual",
        "meaning": "Checks whether tables/columns are documented and relationships are declared.",
        "why": "AI systems misinterpret bare column names, so comments are treated as a mandatory gate.",
    },
    "consumable": {
        "label": "Consumable",
        "meaning": "Checks text/vector readiness, stable identifiers, and documentation for AI/RAG use.",
        "why": "Unclear retrieval targets, grounding keys, or embedding design reduce RAG/agent quality.",
    },
    "current": {
        "label": "Current",
        "meaning": "Checks freshness timestamp columns and recent statistics.",
        "why": "Stale or undated data creates freshness risk in AI answers.",
    },
    "correlated": {
        "label": "Correlated",
        "meaning": "Checks whether tables can be joined or traced through keys and source/update metadata.",
        "why": "Undeclared relationships make it harder to trace evidence and combine tables correctly.",
    },
    "compliant": {
        "label": "Compliant",
        "meaning": "Flags sensitive-looking columns and broad grants for human review.",
        "why": "This does not certify compliance; it identifies security/privacy review targets before AI use.",
    },
}

METRIC_INFO_JA = {
    "table_comment_coverage": "コメントが設定されている評価対象テーブルの割合です。100%でない場合は必須ゲートがfailです。",
    "column_comment_coverage": "コメントが設定されている評価対象カラムの割合です。100%でない場合は必須ゲートがfailです。",
    "pk_coverage": "有効な主キーがあるテーブルの割合です。AI回答の根拠行を安定して参照するために重要です。",
    "fk_coverage": "外部キーを持つ、または外部キー関係に参加するテーブルの割合です。表間の関連を安全に扱うための指標です。",
    "relationship_coverage": "主キーまたは外部キーのいずれかを持つテーブルの割合です。データモデルの説明可能性を見ます。",
    "constraint_coverage": "主キー、一意、外部キー、CHECK制約のいずれかがあるテーブルの割合です。構造的な品質管理の指標です。",
    "table_stats_coverage": "LAST_ANALYZEDが入っているテーブルの割合です。統計情報が未取得だとデータ状態の確認が弱くなります。",
    "column_stats_coverage": "LAST_ANALYZEDが入っているカラムの割合です。列分布やNULL傾向の評価に使います。",
    "recent_stats_coverage": "統計情報が最近取得されているテーブルの割合です。既定では90日以内をrecentと見なします。",
    "freshness_coverage": "UPDATED_ATやLAST_UPDATE_DATEなど、鮮度を示す列があるテーブルの割合です。",
    "source_coverage": "SOURCE_SYSTEM、BATCH_ID、CREATED_BYなど、出所や更新者を示す列があるテーブルの割合です。",
    "text_table_coverage": "RAG候補となるテキスト列を持つテーブルの割合です。検索対象テキストの有無を確認します。",
    "vector_table_coverage": "VECTOR型またはembedding候補を持つテーブルの割合です。embeddingを外部管理している場合は設計書で補足してください。",
    "sensitive_documented_coverage": "機微情報候補列のうちコメントがある列の割合です。列名ベース推定なので人間の分類が必要です。",
    "broad_data_grant_absence": "PUBLICなど広い相手へのデータアクセス権限が検出されなかった割合です。高いほどリスクが低い見立てです。",
}

METRIC_INFO_EN = {
    "table_comment_coverage": "Share of in-scope tables with comments. Less than 100% fails the mandatory gate.",
    "column_comment_coverage": "Share of in-scope columns with comments. Less than 100% fails the mandatory gate.",
    "pk_coverage": "Share of tables with enabled primary keys. Important for stable row-level grounding.",
    "fk_coverage": "Share of tables participating in foreign-key relationships. Useful for safe joins.",
    "relationship_coverage": "Share of tables with primary-key or foreign-key metadata.",
    "constraint_coverage": "Share of tables with primary, unique, foreign-key, or check constraints.",
    "table_stats_coverage": "Share of tables with LAST_ANALYZED populated.",
    "column_stats_coverage": "Share of columns with LAST_ANALYZED populated.",
    "recent_stats_coverage": "Share of tables with recent statistics; default threshold is 90 days.",
    "freshness_coverage": "Share of tables with freshness columns such as UPDATED_AT or LAST_UPDATE_DATE.",
    "source_coverage": "Share of tables with source/update metadata columns such as SOURCE_SYSTEM or BATCH_ID.",
    "text_table_coverage": "Share of tables with text columns that may be RAG retrieval targets.",
    "vector_table_coverage": "Share of tables with VECTOR or embedding-like columns.",
    "sensitive_documented_coverage": "Share of sensitive-name candidate columns that have comments; owner review is still required.",
    "broad_data_grant_absence": "Share of tables without broad data grants such as PUBLIC SELECT.",
}

DATA_ACCESS_PRIVILEGES = set(["SELECT", "READ", "INSERT", "UPDATE", "DELETE", "MERGE", "REFERENCES"])
BROAD_GRANTEES = set(["PUBLIC", "ALL_USERS", "GUEST"])


def norm_key(value):
    return re.sub(r"[^A-Z0-9_]", "", str(value or "").upper())


def clean_cell(value):
    if value is None:
        return ""
    return str(value).strip()


def present(value):
    text = clean_cell(value)
    return bool(text) and text.upper() not in set(["NULL", "(NULL)", "<NULL>"])


def ratio(numerator, denominator):
    if denominator <= 0:
        return 1.0
    return max(0.0, min(1.0, float(numerator) / float(denominator)))


def pct(value):
    return "{0:.1f}%".format(value * 100.0)


def score(value):
    return "{0:.2f}".format(value)


def qident(identifier):
    return '"' + clean_cell(identifier).replace('"', '""') + '"'


def sql_literal(value):
    return "'" + clean_cell(value).replace("'", "''") + "'"


def table_key(row):
    return (clean_cell(row.get("OWNER")).upper(), clean_cell(row.get("TABLE_NAME")).upper())


def col_key(row):
    return (
        clean_cell(row.get("OWNER")).upper(),
        clean_cell(row.get("TABLE_NAME")).upper(),
        clean_cell(row.get("COLUMN_NAME")).upper(),
    )


def strip_sqlcl_noise(line):
    line = line.rstrip("\n")
    if line.startswith("SQL> "):
        line = line[5:]
    stripped = line.strip()
    if not stripped:
        return ""
    if stripped.startswith("old   ") or stripped.startswith("new   "):
        return None
    if stripped.lower().startswith("elapsed:"):
        return None
    if ROWCOUNT_RE.match(stripped):
        return None
    if stripped == "spool off":
        return None
    return line


def read_text(path):
    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        return handle.read()


def write_text(path, text):
    with path.open("w", encoding="utf-8") as handle:
        handle.write(text)


def parse_sections(path):
    raw_sections = {}  # type: MutableMapping[str, List[str]]
    current = None  # type: Optional[str]

    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        for original in handle:
            line = original.rstrip("\n")
            marker = SECTION_RE.match(line.strip())
            if marker:
                current = marker.group(1).lower()
                raw_sections.setdefault(current, [])
                continue
            if END_SECTION_RE.match(line.strip()):
                current = None
                continue
            if line.strip().startswith("@@END_ORACLE_AI_READY_COLLECTOR"):
                current = None
                continue
            if current:
                cleaned = strip_sqlcl_noise(line)
                if cleaned is not None:
                    raw_sections[current].append(cleaned)

    parsed = {}  # type: Dict[str, List[Row]]
    for name, lines in raw_sections.items():
        csv_text = "\n".join(line for line in lines if line.strip())
        if not csv_text.strip():
            parsed[name] = []
            continue
        try:
            reader = csv.DictReader(io.StringIO(csv_text))
            rows = []  # type: List[Row]
            for row in reader:
                normalized = {norm_key(k): clean_cell(v) for k, v in row.items() if k is not None}
                if any(present(v) for v in normalized.values()):
                    rows.append(normalized)
            parsed[name] = rows
        except csv.Error as exc:
            raise ValueError("failed to parse section {0!r} as CSV: {1}".format(name, exc))
    return parsed


def parse_date(value):
    value = clean_cell(value)
    if not value:
        return None
    candidates = [
        value,
        value[:19],
        value[:10],
    ]
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%d-%b-%y",
        "%d-%b-%Y",
    ]
    for candidate in candidates:
        for fmt in formats:
            try:
                return dt.datetime.strptime(candidate, fmt)
            except Exception:
                pass
    return None


def get_profile(rows, override):
    if override:
        return override.lower()
    if rows:
        profile = clean_cell(rows[0].get("PROFILE")).lower()
        if profile in set(["scan", "rag"]):
            return profile
    return "scan"


def intersect_col_keys(rows, valid_col_keys):
    return set(k for k in (col_key(row) for row in rows) if k in valid_col_keys)


def intersect_table_keys(rows, valid_table_keys):
    return set(k for k in (table_key(row) for row in rows) if k in valid_table_keys)


def calculate(sections, profile):
    tables = sections.get("table_inventory", [])
    columns = sections.get("column_inventory", [])
    table_comments = sections.get("table_comments", [])
    column_comments = sections.get("column_comments", [])
    constraints = sections.get("constraints", [])
    rag_candidates = sections.get("rag_candidate_columns", [])
    freshness_cols = sections.get("freshness_columns", [])
    source_cols = sections.get("source_metadata_columns", [])
    sensitive_cols = sections.get("sensitive_candidate_columns", [])
    grants = sections.get("object_grants", [])

    table_keys = sorted(set(table_key(row) for row in tables if table_key(row) != ("", "")))
    table_key_set = set(table_keys)
    col_keys = sorted(set(col_key(row) for row in columns if col_key(row) != ("", "", "") and table_key(row) in table_key_set))
    col_key_set = set(col_keys)
    total_tables = len(table_keys)
    total_columns = len(col_keys)

    table_comment_map = {table_key(row): clean_cell(row.get("COMMENTS")) for row in table_comments if table_key(row) in table_key_set}
    column_comment_map = {col_key(row): clean_cell(row.get("COMMENTS")) for row in column_comments if col_key(row) in col_key_set}

    commented_tables = set(key for key in table_keys if present(table_comment_map.get(key, "")))
    commented_columns = set(key for key in col_keys if present(column_comment_map.get(key, "")))
    missing_table_comments = [key for key in table_keys if key not in commented_tables]
    missing_column_comments = [key for key in col_keys if key not in commented_columns]

    enabled_constraints = [row for row in constraints if table_key(row) in table_key_set and clean_cell(row.get("STATUS")).upper() in set(["ENABLED", ""])]
    pk_tables = set(table_key(row) for row in enabled_constraints if clean_cell(row.get("CONSTRAINT_TYPE")).upper() == "P")
    fk_tables = set(table_key(row) for row in enabled_constraints if clean_cell(row.get("CONSTRAINT_TYPE")).upper() == "R")
    rel_tables = set(table_key(row) for row in enabled_constraints if clean_cell(row.get("CONSTRAINT_TYPE")).upper() in set(["P", "R"]))
    constraint_tables = set(table_key(row) for row in enabled_constraints if clean_cell(row.get("CONSTRAINT_TYPE")).upper() in set(["P", "U", "R", "C"]))

    table_stats = set(table_key(row) for row in tables if table_key(row) in table_key_set and present(row.get("LAST_ANALYZED")))
    column_stats = set(col_key(row) for row in columns if col_key(row) in col_key_set and present(row.get("LAST_ANALYZED")))
    missing_stats = []  # type: List[Key]
    stale_stats = []  # type: List[Tuple[Key, int]]
    today = dt.datetime.now()
    recent_stats = set()  # type: Set[Key]
    for row in tables:
        key = table_key(row)
        if key not in table_key_set:
            continue
        parsed = parse_date(row.get("LAST_ANALYZED", ""))
        if parsed is None:
            missing_stats.append(key)
            continue
        age_days = (today - parsed).days
        if age_days <= 90:
            recent_stats.add(key)
        else:
            stale_stats.append((key, age_days))

    text_tables = set()
    vector_tables = set()
    for row in rag_candidates:
        key = table_key(row)
        if key not in table_key_set:
            continue
        candidate_type = clean_cell(row.get("AI_CANDIDATE_TYPE")).lower()
        data_type = clean_cell(row.get("DATA_TYPE")).upper()
        if candidate_type in set(["text", "long_text"]):
            text_tables.add(key)
        if candidate_type == "vector" or data_type == "VECTOR":
            vector_tables.add(key)

    freshness_tables = intersect_table_keys(freshness_cols, table_key_set)
    source_tables = intersect_table_keys(source_cols, table_key_set)
    sensitive_keys = intersect_col_keys(sensitive_cols, col_key_set)
    sensitive_documented = set(key for key in sensitive_keys if present(column_comment_map.get(key, "")))

    broad_grants = [row for row in grants if table_key(row) in table_key_set and clean_cell(row.get("GRANTEE")).upper() in BROAD_GRANTEES]
    broad_data_grants = [row for row in broad_grants if clean_cell(row.get("PRIVILEGE")).upper() in DATA_ACCESS_PRIVILEGES]
    broad_nondata_grants = [row for row in broad_grants if clean_cell(row.get("PRIVILEGE")).upper() not in DATA_ACCESS_PRIVILEGES]
    broad_data_grant_tables = set(table_key(row) for row in broad_data_grants)

    table_comment_coverage = ratio(len(commented_tables), total_tables)
    column_comment_coverage = ratio(len(commented_columns), total_columns)
    pk_coverage = ratio(len(pk_tables), total_tables)
    fk_coverage = ratio(len(fk_tables), total_tables)
    relationship_coverage = ratio(len(rel_tables), total_tables)
    constraint_coverage = ratio(len(constraint_tables), total_tables)
    table_stats_coverage = ratio(len(table_stats), total_tables)
    column_stats_coverage = ratio(len(column_stats), total_columns)
    recent_stats_coverage = ratio(len(recent_stats), total_tables)
    text_table_coverage = ratio(len(text_tables), total_tables)
    vector_table_coverage = ratio(len(vector_tables), total_tables)
    freshness_coverage = ratio(len(freshness_tables), total_tables)
    source_coverage = ratio(len(source_tables), total_tables)
    sensitive_documented_coverage = ratio(len(sensitive_documented), len(sensitive_keys))
    broad_data_grant_absence = 1.0 - ratio(len(broad_data_grant_tables), total_tables)
    documentation_coverage = (table_comment_coverage + column_comment_coverage) / 2.0

    clean = (pk_coverage + table_stats_coverage + column_stats_coverage + constraint_coverage) / 4.0
    contextual = (0.4 * table_comment_coverage) + (0.4 * column_comment_coverage) + (0.2 * relationship_coverage)
    if profile == "rag":
        consumable = (
            0.35 * text_table_coverage
            + 0.15 * vector_table_coverage
            + 0.35 * documentation_coverage
            + 0.15 * pk_coverage
        )
    else:
        consumable = (0.45 * documentation_coverage) + (0.35 * text_table_coverage) + (0.20 * pk_coverage)
    current = (0.60 * freshness_coverage) + (0.40 * recent_stats_coverage)
    correlated = (0.45 * fk_coverage) + (0.30 * source_coverage) + (0.25 * pk_coverage)
    manual_review = 1.0
    if sensitive_keys:
        manual_review = 0.80 if sensitive_documented_coverage == 1.0 else 0.50
    if broad_data_grants:
        manual_review = min(manual_review, 0.45)
    compliant = (0.50 * sensitive_documented_coverage) + (0.30 * broad_data_grant_absence) + (0.20 * manual_review)

    dimension_scores = {
        "clean": clean,
        "contextual": contextual,
        "consumable": consumable,
        "current": current,
        "correlated": correlated,
        "compliant": compliant,
    }
    weights = RAG_WEIGHTS if profile == "rag" else SCAN_WEIGHTS
    overall = sum(dimension_scores[name] * weights[name] for name in weights)
    mandatory_gate_pass = table_comment_coverage >= 1.0 and column_comment_coverage >= 1.0

    metrics = {
        "table_comment_coverage": table_comment_coverage,
        "column_comment_coverage": column_comment_coverage,
        "pk_coverage": pk_coverage,
        "fk_coverage": fk_coverage,
        "relationship_coverage": relationship_coverage,
        "constraint_coverage": constraint_coverage,
        "table_stats_coverage": table_stats_coverage,
        "column_stats_coverage": column_stats_coverage,
        "recent_stats_coverage": recent_stats_coverage,
        "freshness_coverage": freshness_coverage,
        "source_coverage": source_coverage,
        "text_table_coverage": text_table_coverage,
        "vector_table_coverage": vector_table_coverage,
        "sensitive_documented_coverage": sensitive_documented_coverage,
        "broad_data_grant_absence": broad_data_grant_absence,
    }

    return {
        "profile": profile,
        "tables": tables,
        "columns": columns,
        "run_context": sections.get("run_context", []),
        "total_tables": total_tables,
        "total_columns": total_columns,
        "table_keys": table_keys,
        "col_keys": col_keys,
        "missing_table_comments": missing_table_comments,
        "missing_column_comments": missing_column_comments,
        "metrics": metrics,
        "dimension_scores": dimension_scores,
        "weights": weights,
        "overall": overall,
        "mandatory_gate_pass": mandatory_gate_pass,
        "pk_missing_tables": [key for key in table_keys if key not in pk_tables],
        "freshness_missing_tables": [key for key in table_keys if key not in freshness_tables],
        "stats_missing_tables": missing_stats,
        "stale_stats": stale_stats,
        "text_missing_tables": [key for key in table_keys if key not in text_tables],
        "vector_tables": sorted(vector_tables),
        "sensitive_cols": sorted(sensitive_keys),
        "broad_grants": broad_grants,
        "broad_data_grants": broad_data_grants,
        "broad_nondata_grants": broad_nondata_grants,
    }


def metric(data, name):
    return float(data.get("metrics", {}).get(name, 0.0))


def interpretation(overall, gate, lang):
    if not gate:
        return "必須コメントゲート未達のため、要求ポリシー上は未Ready" if lang == "ja" else "not ready under the mandatory comment policy"
    if overall >= 0.85:
        return "AI Ready候補" if lang == "ja" else "strong AI-ready candidate"
    if overall >= 0.70:
        return "改善計画付きで利用可能" if lang == "ja" else "usable with remediation"
    if overall >= 0.50:
        return "PoCまたは限定パイロット向け" if lang == "ja" else "pilot only"
    return "本格利用前に改善が必要" if lang == "ja" else "not ready without remediation"


def add_sql_block(lines, title, reason, purpose, review):
    lines.append("-- " + title)
    lines.append("-- Reason: " + reason)
    lines.append("-- Purpose: " + purpose)
    lines.append("-- Review: " + review)


def make_comment_sql(data, max_sql, lang):
    lines = []  # type: List[str]
    omitted = 0
    if data["missing_table_comments"]:
        if lang == "ja":
            add_sql_block(
                lines,
                "Remediation: missing table comments",
                "テーブルコメントがないため、Contextual score と mandatory comment gate が低下します。",
                "テーブルの業務目的、粒度、更新頻度、AI利用時の注意点を明文化します。",
                "TODOコメントを業務オーナーが実際の説明に置き換えてから実行してください。",
            )
        else:
            add_sql_block(
                lines,
                "Remediation: missing table comments",
                "Missing table comments reduce the Contextual score and fail the mandatory comment gate.",
                "Document business purpose, grain, refresh cadence, owner, and AI usage guidance.",
                "Replace TODO text with owner-approved descriptions before running.",
            )
        for owner, table in data["missing_table_comments"]:
            if len([line for line in lines if line.startswith("COMMENT ")]) >= max_sql:
                omitted += 1
                continue
            comment = "TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for {0}.{1}.".format(owner, table)
            lines.append("COMMENT ON TABLE {0}.{1} IS {2};".format(qident(owner), qident(table), sql_literal(comment)))
        lines.append("")

    if data["missing_column_comments"]:
        if lang == "ja":
            add_sql_block(
                lines,
                "Remediation: missing column comments",
                "カラムコメントがないため、AIが列の意味、単位、NULLの意味、機微性を誤解する可能性があります。",
                "各カラムの意味、形式、許容値、NULLの扱い、出所、機微性を明文化します。",
                "TODOコメントを業務オーナーが実際の説明に置き換えてから実行してください。",
            )
        else:
            add_sql_block(
                lines,
                "Remediation: missing column comments",
                "Missing column comments can cause AI to misread meaning, units, null semantics, or sensitivity.",
                "Document meaning, format, allowed values, null semantics, source, and sensitivity.",
                "Replace TODO text with owner-approved descriptions before running.",
            )
        for owner, table, column in data["missing_column_comments"]:
            if len([line for line in lines if line.startswith("COMMENT ")]) >= max_sql:
                omitted += 1
                continue
            comment = "TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for {0}.{1}.{2}.".format(owner, table, column)
            lines.append("COMMENT ON COLUMN {0}.{1}.{2} IS {3};".format(qident(owner), qident(table), qident(column), sql_literal(comment)))
        lines.append("")

    return lines, omitted


def make_advisory_sql(data, max_items, lang):
    lines = []  # type: List[str]
    stats_targets = [(key, None) for key in data.get("stats_missing_tables", [])]
    stats_targets.extend(data.get("stale_stats", []))
    if stats_targets:
        if lang == "ja":
            add_sql_block(
                lines,
                "Remediation: missing or stale optimizer statistics",
                "LAST_ANALYZEDが未設定または古いため、Clean/Current score が低下します。",
                "Oracle optimizer統計を収集し、メタデータ上もデータ状態を確認しやすくします。",
                "大きい表ではメンテナンス時間、DBMS_STATS設定、サンプリング方針をDBAと確認してください。",
            )
        else:
            add_sql_block(
                lines,
                "Remediation: missing or stale optimizer statistics",
                "LAST_ANALYZED is missing or stale, reducing Clean/Current scores.",
                "Gather optimizer statistics so metadata reflects data state more clearly.",
                "For large tables, confirm maintenance windows, DBMS_STATS preferences, and sampling policy.",
            )
        for item in stats_targets[:max_items]:
            key = item[0]
            age = item[1]
            owner, table = key
            reason = "missing" if age is None else "stale_{0}_days".format(age)
            lines.append("-- Target: {0}.{1}; stats_reason={2}".format(owner, table, reason))
            lines.append("BEGIN")
            lines.append("  DBMS_STATS.GATHER_TABLE_STATS(")
            lines.append("    ownname => {0},".format(sql_literal(owner)))
            lines.append("    tabname => {0},".format(sql_literal(table)))
            lines.append("    cascade => TRUE,")
            lines.append("    method_opt => 'FOR ALL COLUMNS SIZE AUTO'")
            lines.append("  );")
            lines.append("END;")
            lines.append("/")
        lines.append("")

    pk_missing = data.get("pk_missing_tables", [])
    if pk_missing:
        if lang == "ja":
            add_sql_block(
                lines,
                "Template only: primary key candidates",
                "主キー未検出のため、Clean/Correlated/Consumable score が低下します。",
                "AI回答の根拠行を安定して参照できる業務キーを明確にします。",
                "重複データ、NULL、既存アプリ影響、制約名、索引方針を確認するまで実行しないでください。",
            )
        else:
            add_sql_block(
                lines,
                "Template only: primary key candidates",
                "Missing primary keys reduce Clean/Correlated/Consumable scores.",
                "Define stable business keys for row-level grounding.",
                "Do not run until duplicates, nulls, application impact, constraint names, and indexing are reviewed.",
            )
        for owner, table in pk_missing[:max_items]:
            lines.append("-- ALTER TABLE {0}.{1} ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);".format(qident(owner), qident(table)))
        lines.append("")

    freshness_missing = data.get("freshness_missing_tables", [])
    if freshness_missing:
        if lang == "ja":
            add_sql_block(
                lines,
                "Template only: freshness column candidates",
                "鮮度列が未検出のため、Current score が低下し、AI回答でデータの新しさを説明しづらくなります。",
                "更新日時、取込日時、有効期間などを明示し、RAG/agent回答の鮮度説明を可能にします。",
                "アプリが別の方法で鮮度を管理していないか確認し、列追加の影響をレビューしてください。",
            )
        else:
            add_sql_block(
                lines,
                "Template only: freshness column candidates",
                "No freshness column was detected, reducing Current score and recency explainability.",
                "Expose update/load/effective timestamps so AI answers can explain freshness.",
                "Confirm whether freshness is already tracked elsewhere and review application impact before adding columns.",
            )
        for owner, table in freshness_missing[:max_items]:
            lines.append("-- ALTER TABLE {0}.{1} ADD {2} TIMESTAMP(6);".format(qident(owner), qident(table), qident("UPDATED_AT")))
        lines.append("")

    broad_data_grants = data.get("broad_data_grants", [])
    if broad_data_grants:
        if lang == "ja":
            add_sql_block(
                lines,
                "Review only: broad data grants",
                "PUBLICなど広い相手へのデータアクセス権限があるため、Compliant score が低下します。",
                "AI利用前に公開範囲が意図通りかを確認し、不要な広い権限を減らします。",
                "REVOKEはアプリや利用者に影響するため、DBA/業務オーナー確認後に個別判断してください。",
            )
        else:
            add_sql_block(
                lines,
                "Review only: broad data grants",
                "Broad data grants such as PUBLIC reduce the Compliant score.",
                "Confirm exposure is intentional before AI use and reduce unnecessary broad access.",
                "REVOKE can break applications or users; review with DBA and owners before running.",
            )
        for row in broad_data_grants[:max_items]:
            owner, table = table_key(row)
            grantee = clean_cell(row.get("GRANTEE")).upper()
            privilege = clean_cell(row.get("PRIVILEGE")).upper()
            lines.append("-- Review grant: {0} on {1}.{2} to {3}".format(privilege, owner, table, grantee))
            lines.append("-- REVOKE {0} ON {1}.{2} FROM {3};".format(privilege, qident(owner), qident(table), qident(grantee)))
        lines.append("")

    return lines


def first_context(data):
    rows = data.get("run_context", [])
    if isinstance(rows, list) and rows:
        return rows[0]
    return {}


def md_escape(value):
    text = clean_cell(value)
    return text.replace("|", "\\|") if text else "-"


def format_weight(weights, name):
    return pct(float(weights.get(name, 0.0)))


def status_label(value, good_threshold, warn_threshold, lang):
    if value >= good_threshold:
        return "良好" if lang == "ja" else "good"
    if value >= warn_threshold:
        return "要確認" if lang == "ja" else "review"
    return "要改善" if lang == "ja" else "needs remediation"


def render_metric_rows(data, lang):
    info = METRIC_INFO_JA if lang == "ja" else METRIC_INFO_EN
    labels = {
        "table_comment_coverage": "Table comment coverage",
        "column_comment_coverage": "Column comment coverage",
        "pk_coverage": "PK coverage",
        "fk_coverage": "FK coverage",
        "relationship_coverage": "Relationship coverage",
        "constraint_coverage": "Constraint coverage",
        "table_stats_coverage": "Table stats coverage",
        "column_stats_coverage": "Column stats coverage",
        "recent_stats_coverage": "Recent stats coverage",
        "freshness_coverage": "Freshness coverage",
        "source_coverage": "Source metadata coverage",
        "text_table_coverage": "Text-bearing table coverage",
        "vector_table_coverage": "Vector table coverage",
        "sensitive_documented_coverage": "Sensitive candidate documentation",
        "broad_data_grant_absence": "Broad data grant absence",
    }
    preferred_order = [
        "table_comment_coverage",
        "column_comment_coverage",
        "pk_coverage",
        "fk_coverage",
        "relationship_coverage",
        "constraint_coverage",
        "table_stats_coverage",
        "column_stats_coverage",
        "recent_stats_coverage",
        "freshness_coverage",
        "source_coverage",
        "text_table_coverage",
        "vector_table_coverage",
        "sensitive_documented_coverage",
        "broad_data_grant_absence",
    ]
    rows = []
    for name in preferred_order:
        value = metric(data, name)
        if name in set(["table_comment_coverage", "column_comment_coverage"]):
            status = "pass" if value >= 1.0 else "fail"
        elif name == "broad_data_grant_absence":
            status = status_label(value, 1.0, 0.8, lang)
        elif name in set(["vector_table_coverage", "text_table_coverage"]):
            status = "参考" if lang == "ja" else "informational"
        else:
            status = status_label(value, 0.8, 0.5, lang)
        rows.append("| {0} | {1} | {2} | {3} |".format(labels[name], pct(value), status, md_escape(info.get(name, ""))))
    return rows


def render_findings(data, lang):
    lines = []  # type: List[str]
    mt = len(data["missing_table_comments"])
    mc = len(data["missing_column_comments"])
    pk = len(data["pk_missing_tables"])
    fresh = len(data["freshness_missing_tables"])
    stats_missing = len(data["stats_missing_tables"])
    stale_stats = len(data["stale_stats"])
    sensitive = len(data["sensitive_cols"])
    broad_data = len(data["broad_data_grants"])
    broad_nondata = len(data["broad_nondata_grants"])

    if lang == "ja":
        lines.append("### High priority")
        if mt or mc:
            lines.append("- Mandatory comment gate が fail です。table comment 欠落 {0} 件、column comment 欠落 {1} 件があります。".format(mt, mc))
        if pk:
            lines.append("- 主キー未検出のテーブルが {0} 件あります。RAG/agent応答の根拠行を安定して参照しづらくなります。".format(pk))
        if broad_data:
            lines.append("- PUBLICなど広いデータアクセス権限候補が {0} 件あります。AI利用前に公開範囲を確認してください。".format(broad_data))
        if not (mt or mc or pk or broad_data):
            lines.append("- High priority の自動検出事項はありません。")
        lines.append("")
        lines.append("### Medium priority")
        if stats_missing or stale_stats:
            lines.append("- 統計情報が未取得または古いテーブルが {0} 件あります。Clean/Current score の主な減点要因です。".format(stats_missing + stale_stats))
        if fresh:
            lines.append("- 鮮度を示す日時列が未検出のテーブルが {0} 件あります。データの新しさを説明しづらくなります。".format(fresh))
        if sensitive:
            lines.append("- 機微情報候補列が {0} 件あります。列名ベースの推定のため、業務オーナーによる分類が必要です。".format(sensitive))
        if metric(data, "text_table_coverage") < 1.0:
            lines.append("- テキスト候補列を持つテーブルは {0} です。RAG対象テーブルを明確化してください。".format(pct(metric(data, "text_table_coverage"))))
        if not (stats_missing or stale_stats or fresh or sensitive or metric(data, "text_table_coverage") < 1.0):
            lines.append("- Medium priority の自動検出事項はありません。")
        lines.append("")
        lines.append("### Low priority / manual review")
        if metric(data, "vector_table_coverage") == 0.0:
            lines.append("- VECTOR型カラムは未検出です。embeddingを別スキーマや外部サービスで管理している場合は設計書に明記してください。")
        else:
            lines.append("- VECTOR型カラムを持つテーブルが {0} 件あります。インデックス、更新頻度、再埋め込み方針を確認してください。".format(len(data["vector_tables"])))
        if broad_nondata:
            lines.append("- 広い非データ権限候補が {0} 件あります。テーブル公開リスクとは分けてDBAレビュー対象にしてください。".format(broad_nondata))
    else:
        lines.append("### High priority")
        if mt or mc:
            lines.append("- The mandatory comment gate failed: {0} missing table comments and {1} missing column comments.".format(mt, mc))
        if pk:
            lines.append("- {0} tables have no detected primary key, making row-level grounding harder for RAG/agents.".format(pk))
        if broad_data:
            lines.append("- {0} broad data grant candidates were found. Confirm exposure before AI use.".format(broad_data))
        if not (mt or mc or pk or broad_data):
            lines.append("- No high-priority automatic findings.")
        lines.append("")
        lines.append("### Medium priority")
        if stats_missing or stale_stats:
            lines.append("- {0} tables have missing or stale statistics, reducing Clean/Current scores.".format(stats_missing + stale_stats))
        if fresh:
            lines.append("- {0} tables have no detected freshness timestamp column, making recency hard to explain.".format(fresh))
        if sensitive:
            lines.append("- {0} sensitive-name candidate columns require owner classification.".format(sensitive))
        if metric(data, "text_table_coverage") < 1.0:
            lines.append("- Text-bearing table coverage is {0}. Clarify which tables are RAG targets.".format(pct(metric(data, "text_table_coverage"))))
        if not (stats_missing or stale_stats or fresh or sensitive or metric(data, "text_table_coverage") < 1.0):
            lines.append("- No medium-priority automatic findings.")
        lines.append("")
        lines.append("### Low priority / manual review")
        if metric(data, "vector_table_coverage") == 0.0:
            lines.append("- No VECTOR columns were detected. If embeddings are stored elsewhere, document that design.")
        else:
            lines.append("- {0} tables have VECTOR columns. Review indexing, refresh, and re-embedding policy.".format(len(data["vector_tables"])))
        if broad_nondata:
            lines.append("- {0} broad non-data grants were found. Review separately from table data exposure.".format(broad_nondata))
    return lines


def render_markdown(data, source, max_sql, max_items, lang):
    ctx = first_context(data)
    dimensions = data["dimension_scores"]
    weights = data["weights"]
    overall = float(data["overall"])
    gate = bool(data["mandatory_gate_pass"])
    profile = str(data["profile"])
    title = "Oracle Database AI Ready 評価レポート" if lang == "ja" else "Oracle Database AI Ready Assessment Report"
    gate_label = "pass" if gate else "fail"
    conclusion = interpretation(overall, gate, lang)
    dim_info = DIMENSION_INFO_JA if lang == "ja" else DIMENSION_INFO_EN

    comment_sql, omitted_sql = make_comment_sql(data, max_sql, lang)
    advisory_sql = make_advisory_sql(data, max_items, lang)
    all_sql = comment_sql
    if omitted_sql:
        all_sql.append("-- {0} additional COMMENT statements omitted from this report/output because --max-sql was reached.".format(omitted_sql))
    all_sql.extend(advisory_sql)
    sql_text = "\n".join(all_sql).strip()
    if not sql_text:
        sql_text = "-- No improvement SQL generated from the available metadata."
    sql_text = sql_text + "\n"

    if lang == "ja":
        lines = [
            "# " + title,
            "",
            "## 1. エグゼクティブサマリー",
            "- 総合スコア: **{0} / 1.00**".format(score(overall)),
            "- Profile: **{0}**".format(profile),
            "- Mandatory comment gate: **{0}**".format(gate_label),
            "- 結論: **{0}**".format(conclusion),
            "- コメント有無チェックは必須条件です。テーブルまたはカラムコメントが1件でも欠けると、数値スコアに関係なく gate は fail です。",
            "",
            "## 2. スコープと前提",
            "| 項目 | 値 |",
            "|---|---|",
            "| Schema | {0} |".format(md_escape(ctx.get("TARGET_OWNER"))),
            "| Table pattern | {0} |".format(md_escape(ctx.get("TABLE_LIKE_PATTERN"))),
            "| Profile | {0} |".format(md_escape(profile)),
            "| 評価対象テーブル数 | {0} |".format(data["total_tables"]),
            "| 評価対象カラム数 | {0} |".format(data["total_columns"]),
            "| SQLcl spool | {0} |".format(md_escape(source.name)),
            "| Scan timestamp | {0} |".format(md_escape(ctx.get("SCAN_TIMESTAMP"))),
            "| 注意事項 | ALL_* dictionary views で見えるメタデータを評価します。実データ値、業務上の正しさ、法令遵守は別途レビューが必要です。 |",
            "",
            "## 3. 評価項目の説明",
            "| Dimension | Weight | 何を評価しているか | なぜ重要か |",
            "|---|---:|---|---|",
        ]
        for name in ["clean", "contextual", "consumable", "current", "correlated", "compliant"]:
            lines.append("| {0} | {1} | {2} | {3} |".format(dim_info[name]["label"], format_weight(weights, name), md_escape(dim_info[name]["meaning"]), md_escape(dim_info[name]["why"])))
        lines.extend([
            "",
            "## 4. スコアカード",
            "| Dimension | Weight | Score | 主な根拠 |",
            "|---|---:|---:|---|",
            "| Clean | {0} | {1} | PK {2}, table stats {3}, column stats {4}, constraints {5} |".format(format_weight(weights, "clean"), score(dimensions["clean"]), pct(metric(data, "pk_coverage")), pct(metric(data, "table_stats_coverage")), pct(metric(data, "column_stats_coverage")), pct(metric(data, "constraint_coverage"))),
            "| Contextual | {0} | {1} | table comments {2}, column comments {3}, relationships {4} |".format(format_weight(weights, "contextual"), score(dimensions["contextual"]), pct(metric(data, "table_comment_coverage")), pct(metric(data, "column_comment_coverage")), pct(metric(data, "relationship_coverage"))),
            "| Consumable | {0} | {1} | text-bearing tables {2}, vector tables {3}, documentation {4}, PK {5} |".format(format_weight(weights, "consumable"), score(dimensions["consumable"]), pct(metric(data, "text_table_coverage")), pct(metric(data, "vector_table_coverage")), pct((metric(data, "table_comment_coverage") + metric(data, "column_comment_coverage")) / 2.0), pct(metric(data, "pk_coverage"))),
            "| Current | {0} | {1} | freshness columns {2}, recent stats {3} |".format(format_weight(weights, "current"), score(dimensions["current"]), pct(metric(data, "freshness_coverage")), pct(metric(data, "recent_stats_coverage"))),
            "| Correlated | {0} | {1} | FK {2}, source metadata {3}, PK {4} |".format(format_weight(weights, "correlated"), score(dimensions["correlated"]), pct(metric(data, "fk_coverage")), pct(metric(data, "source_coverage")), pct(metric(data, "pk_coverage"))),
            "| Compliant | {0} | {1} | sensitive documented {2}, broad data grant absence {3} |".format(format_weight(weights, "compliant"), score(dimensions["compliant"]), pct(metric(data, "sensitive_documented_coverage")), pct(metric(data, "broad_data_grant_absence"))),
            "",
            "## 5. メトリクス詳細",
            "| Metric | Value | Status | 説明 |",
            "|---|---:|---|---|",
        ])
        lines.extend(render_metric_rows(data, lang))
        lines.extend([
            "",
            "## 6. Mandatory comment gate",
            "| Check | Coverage | Result | Required action |",
            "|---|---:|---|---|",
            "| Table comments | {0} | {1} | Missing {2} table comments |".format(pct(metric(data, "table_comment_coverage")), "pass" if metric(data, "table_comment_coverage") >= 1.0 else "fail", len(data["missing_table_comments"])),
            "| Column comments | {0} | {1} | Missing {2} column comments |".format(pct(metric(data, "column_comment_coverage")), "pass" if metric(data, "column_comment_coverage") >= 1.0 else "fail", len(data["missing_column_comments"])),
            "",
            "## 7. 主要な発見事項",
        ])
        lines.extend(render_findings(data, lang))
        lines.extend([
            "",
            "## 8. 改善 SQL の考え方",
            "| SQLカテゴリ | 理由 | 目的 | 実行前確認 |",
            "|---|---|---|---|",
            "| COMMENT ON TABLE / COLUMN | コメント欠落は mandatory gate と Contextual score を下げます。 | 業務意味、粒度、単位、NULL意味、機微性、AI利用時の注意を明文化します。 | TODO文を実説明に置換し、業務オーナー承認後に実行します。 |",
            "| DBMS_STATS.GATHER_TABLE_STATS | LAST_ANALYZED未設定/古い統計は Clean/Current score を下げます。 | 統計情報を収集し、メタデータ上のデータ状態を明確にします。 | 大規模表ではメンテナンス時間とDBMS_STATS方針をDBA確認します。 |",
            "| PRIMARY KEY / freshness column | キーや鮮度列の不足は根拠追跡や新しさ説明を弱くします。 | 根拠行の特定とデータ鮮度説明を可能にします。 | アプリ影響があるためテンプレートのみ。実行前に設計レビューが必要です。 |",
            "| REVOKE候補 | 広いデータ権限はAI利用前の公開範囲確認が必要です。 | 不要な公開を減らし、レビュー対象を明確にします。 | 依存ユーザー/アプリ影響があるためレビュー専用です。 |",
            "",
            "```sql",
            sql_text.rstrip(),
            "```",
            "",
            "## 9. 手動レビューが必要な項目",
            "- 機微情報候補列: {0} 件。列名ベースの推定なので、業務オーナーによる確認が必要です。".format(len(data["sensitive_cols"])),
            "- 広いデータ権限候補: {0} 件。PUBLIC SELECT/READなどがあればAI利用前にDBA確認してください。".format(len(data["broad_data_grants"])),
            "- 広い非データ権限候補: {0} 件。テーブル公開リスクとは分けてDBAレビューしてください。".format(len(data["broad_nondata_grants"])),
            "- 主キー、外部キー、更新日時、データ粒度、保持期間はアプリケーション仕様と照合してください。",
            "",
            "## 10. 次のアクション",
            "1. 欠落している table / column comment を補完し、Mandatory comment gate を pass にする。",
            "2. 統計情報、主キー、鮮度列、外部キーの不足を優先度順に改善する。",
            "3. RAG用途では、検索対象テキスト、chunking方針、embedding保管場所、更新頻度を明文化する。",
        ])
    else:
        lines = [
            "# " + title,
            "",
            "## 1. Executive summary",
            "- Overall score: **{0} / 1.00**".format(score(overall)),
            "- Profile: **{0}**".format(profile),
            "- Mandatory comment gate: **{0}**".format(gate_label),
            "- Conclusion: **{0}**".format(conclusion),
            "- Comment checks are mandatory. Any missing table or column comment fails the gate regardless of numeric score.",
            "",
            "## 2. Scope and assumptions",
            "| Item | Value |",
            "|---|---|",
            "| Schema | {0} |".format(md_escape(ctx.get("TARGET_OWNER"))),
            "| Table pattern | {0} |".format(md_escape(ctx.get("TABLE_LIKE_PATTERN"))),
            "| Profile | {0} |".format(md_escape(profile)),
            "| Tables assessed | {0} |".format(data["total_tables"]),
            "| Columns assessed | {0} |".format(data["total_columns"]),
            "| SQLcl spool | {0} |".format(md_escape(source.name)),
            "| Scan timestamp | {0} |".format(md_escape(ctx.get("SCAN_TIMESTAMP"))),
            "| Caveat | Assesses metadata visible through ALL_* dictionary views; data values, business correctness, and legal compliance require separate review. |",
            "",
            "## 3. What each dimension means",
            "| Dimension | Weight | What it evaluates | Why it matters |",
            "|---|---:|---|---|",
        ]
        for name in ["clean", "contextual", "consumable", "current", "correlated", "compliant"]:
            lines.append("| {0} | {1} | {2} | {3} |".format(dim_info[name]["label"], format_weight(weights, name), md_escape(dim_info[name]["meaning"]), md_escape(dim_info[name]["why"])))
        lines.extend([
            "",
            "## 4. Scorecard",
            "| Dimension | Weight | Score | Evidence |",
            "|---|---:|---:|---|",
            "| Clean | {0} | {1} | PK {2}, table stats {3}, column stats {4}, constraints {5} |".format(format_weight(weights, "clean"), score(dimensions["clean"]), pct(metric(data, "pk_coverage")), pct(metric(data, "table_stats_coverage")), pct(metric(data, "column_stats_coverage")), pct(metric(data, "constraint_coverage"))),
            "| Contextual | {0} | {1} | table comments {2}, column comments {3}, relationships {4} |".format(format_weight(weights, "contextual"), score(dimensions["contextual"]), pct(metric(data, "table_comment_coverage")), pct(metric(data, "column_comment_coverage")), pct(metric(data, "relationship_coverage"))),
            "| Consumable | {0} | {1} | text-bearing tables {2}, vector tables {3}, documentation {4}, PK {5} |".format(format_weight(weights, "consumable"), score(dimensions["consumable"]), pct(metric(data, "text_table_coverage")), pct(metric(data, "vector_table_coverage")), pct((metric(data, "table_comment_coverage") + metric(data, "column_comment_coverage")) / 2.0), pct(metric(data, "pk_coverage"))),
            "| Current | {0} | {1} | freshness columns {2}, recent stats {3} |".format(format_weight(weights, "current"), score(dimensions["current"]), pct(metric(data, "freshness_coverage")), pct(metric(data, "recent_stats_coverage"))),
            "| Correlated | {0} | {1} | FK {2}, source metadata {3}, PK {4} |".format(format_weight(weights, "correlated"), score(dimensions["correlated"]), pct(metric(data, "fk_coverage")), pct(metric(data, "source_coverage")), pct(metric(data, "pk_coverage"))),
            "| Compliant | {0} | {1} | sensitive documented {2}, broad data grant absence {3} |".format(format_weight(weights, "compliant"), score(dimensions["compliant"]), pct(metric(data, "sensitive_documented_coverage")), pct(metric(data, "broad_data_grant_absence"))),
            "",
            "## 5. Metric details",
            "| Metric | Value | Status | Explanation |",
            "|---|---:|---|---|",
        ])
        lines.extend(render_metric_rows(data, lang))
        lines.extend([
            "",
            "## 6. Mandatory comment gate",
            "| Check | Coverage | Result | Required action |",
            "|---|---:|---|---|",
            "| Table comments | {0} | {1} | Missing {2} table comments |".format(pct(metric(data, "table_comment_coverage")), "pass" if metric(data, "table_comment_coverage") >= 1.0 else "fail", len(data["missing_table_comments"])),
            "| Column comments | {0} | {1} | Missing {2} column comments |".format(pct(metric(data, "column_comment_coverage")), "pass" if metric(data, "column_comment_coverage") >= 1.0 else "fail", len(data["missing_column_comments"])),
            "",
            "## 7. Key findings",
        ])
        lines.extend(render_findings(data, lang))
        lines.extend([
            "",
            "## 8. Improvement SQL rationale",
            "| SQL category | Reason | Purpose | Pre-run review |",
            "|---|---|---|---|",
            "| COMMENT ON TABLE / COLUMN | Missing comments reduce Contextual score and fail the mandatory gate. | Document business meaning, grain, units, null semantics, sensitivity, and AI usage notes. | Replace TODO text and get owner approval. |",
            "| DBMS_STATS.GATHER_TABLE_STATS | Missing/stale LAST_ANALYZED reduces Clean/Current scores. | Gather statistics so metadata reflects data state. | Confirm maintenance window and DBMS_STATS policy with DBA. |",
            "| PRIMARY KEY / freshness column | Missing keys/freshness weakens grounding and recency explanation. | Enable row grounding and explain data freshness. | Template only; requires design review before execution. |",
            "| REVOKE candidates | Broad data grants require exposure review before AI use. | Reduce unnecessary exposure and clarify review targets. | Review-only due to dependency impact. |",
            "",
            "```sql",
            sql_text.rstrip(),
            "```",
            "",
            "## 9. Manual review items",
            "- Sensitive-name candidate columns: {0}. Name-based heuristic only; owner classification is required.".format(len(data["sensitive_cols"])),
            "- Broad data grant candidates: {0}. Confirm PUBLIC SELECT/READ/etc. before AI use.".format(len(data["broad_data_grants"])),
            "- Broad non-data grant candidates: {0}. Review separately from table data exposure.".format(len(data["broad_nondata_grants"])),
            "- Validate primary keys, foreign keys, freshness columns, data grain, and retention against application design.",
            "",
            "## 10. Next actions",
            "1. Fill missing table and column comments until the mandatory gate passes.",
            "2. Remediate statistics, keys, freshness columns, and relationships by priority.",
            "3. For RAG, document retrieval text, chunking policy, embedding storage, and refresh cadence.",
        ])

    return "\n".join(lines).rstrip() + "\n", sql_text


def main(argv=None):
    parser = argparse.ArgumentParser(description="Score Oracle AI-ready metadata from SQLcl spool output.")
    parser.add_argument("scan_file", help="SQLcl spool output generated by oracle_ai_ready_collect.sql")
    parser.add_argument("--profile", choices=("scan", "rag"), help="override profile detected from run_context")
    parser.add_argument("--language", choices=("ja", "en"), default="ja", help="report language")
    parser.add_argument("--max-sql", type=int, default=200, help="maximum generated COMMENT statements to include")
    parser.add_argument("--max-items", type=int, default=50, help="maximum advisory SQL items per category")
    parser.add_argument("--output", "-o", help="write Markdown report to this file")
    parser.add_argument("--sql-output", help="write improvement SQL to this file")
    args = parser.parse_args(argv)

    path = Path(args.scan_file)
    if not path.exists():
        print("error: scan file not found: {0}".format(path), file=sys.stderr)
        return 2

    try:
        sections = parse_sections(path)
        profile = get_profile(sections.get("run_context", []), args.profile)
        data = calculate(sections, profile)
        markdown, sql_text = render_markdown(data, source=path, max_sql=max(0, args.max_sql), max_items=max(0, args.max_items), lang=args.language)
    except Exception as exc:
        print("error: {0}".format(exc), file=sys.stderr)
        return 1

    if args.output:
        write_text(Path(args.output), markdown)
    else:
        sys.stdout.write(markdown)

    if args.sql_output:
        write_text(Path(args.sql_output), sql_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
