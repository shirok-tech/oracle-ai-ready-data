#!/usr/bin/env python3
"""Score Oracle AI-ready metadata collected by oracle_ai_ready_collect.sql.

Input: sectioned CSV output spooled by SQLcl.
Outputs:
- Markdown report with the mandatory comment gate
- Optional self-contained HTML report
- Review-oriented improvement SQL

Additional advisory checks:
- Dynamic next actions based on unresolved findings
- Comment quality review (placeholder, overly short, generic comments)
- Semantic type mismatch warnings for text columns that appear numeric/date-like

The additional advisory checks do not change the existing dimension or overall
scores in this version.

Compatibility: Python 3.6+ and no third-party dependencies.
"""

import argparse
import csv
import datetime as dt
import io
import json
import re
import sys
from html import escape as html_escape
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
    stripped = line.strip()
    if not stripped:
        return ""
    if stripped.startswith("old   ") or stripped.startswith("new   "):
        return None
    if stripped.lower().startswith("elapsed:"):
        return None
    if ROWCOUNT_RE.match(stripped):
        return None
    if re.fullmatch(r"no rows selected\.?", stripped, re.I):
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


def csv_quote_state(line, quoted, line_number):
    """Track true quoted fields, rejecting bare quotes in unquoted fields.

    csv.reader(strict=True) still accepts bare quotes, so quote parity alone
    could misclassify an echoed SQL line as a multiline metadata value.
    """
    field_start = not quoted
    index = 0
    while index < len(line):
        char = line[index]
        if char == '"':
            if quoted:
                if index + 1 < len(line) and line[index + 1] == '"':
                    index += 2
                    continue
                quoted = False
            elif field_start:
                quoted = True
            else:
                raise ValueError("invalid CSV quoting at line {0}".format(line_number))
            field_start = False
        elif not quoted:
            field_start = char == ","
        index += 1
    return quoted


def parse_sections(path):
    """Reject corrupt spools before an unrecognized scan can look like empty scope.

    Section markers and SQLcl noise are recognized only between CSV records;
    the same text inside a quoted multiline comment is metadata, not a command.
    """
    raw_sections = {}  # type: MutableMapping[str, List[str]]
    current = None  # type: Optional[str]
    in_quoted_record = False

    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        for line_number, original in enumerate(handle, 1):
            line = original.rstrip("\r\n")
            if not in_quoted_record:
                if re.match(r"^\s*SQL>", line, re.I):
                    raise ValueError(
                        "invalid collector input at line {0}: SQL> prompt / echoed SQL detected; "
                        "recollect with SET ECHO OFF before SPOOL".format(line_number)
                    )
                marker = SECTION_RE.match(line.strip())
                if marker:
                    if current is not None:
                        raise ValueError("unclosed collector section: {0}".format(current))
                    current = marker.group(1).lower()
                    if current in raw_sections:
                        raise ValueError("duplicate collector section: {0}".format(current))
                    raw_sections[current] = []
                    continue
                if END_SECTION_RE.match(line.strip()):
                    if current is None:
                        raise ValueError("collector section end without a section at line {0}".format(line_number))
                    current = None
                    continue
                if line.strip().startswith("@@END_ORACLE_AI_READY_COLLECTOR"):
                    if current is not None:
                        raise ValueError("unclosed collector section: {0}".format(current))
                    continue
            if current:
                cleaned = line if in_quoted_record else strip_sqlcl_noise(line)
                if cleaned is not None:
                    in_quoted_record = csv_quote_state(cleaned, in_quoted_record, line_number)
                    raw_sections[current].append(cleaned)

    if current is not None:
        raise ValueError("unclosed collector section: {0}".format(current))

    parsed = {}  # type: Dict[str, List[Row]]
    headers = {}
    for name, lines in raw_sections.items():
        csv_text = "\n".join(lines)
        if not csv_text.strip():
            parsed[name] = []
            headers[name] = []
            continue
        try:
            reader = csv.reader(io.StringIO(csv_text), strict=True)
            raw_header = next((row for row in reader if row), [])
            fields = [norm_key(key) for key in raw_header]
            if not fields or any(not key for key in fields) or len(set(fields)) != len(fields):
                raise ValueError("invalid or duplicate CSV headers in section {0}".format(name))
            headers[name] = fields
            rows = []  # type: List[Row]
            for row in reader:
                if not row:
                    continue
                if len(row) != len(fields):
                    raise ValueError("invalid CSV row width in section {0}: expected {1}, got {2}".format(name, len(fields), len(row)))
                normalized = {key: clean_cell(value) for key, value in zip(fields, row)}
                if name in {"run_context", "table_inventory", "column_inventory"} or any(present(v) for v in normalized.values()):
                    rows.append(normalized)
            parsed[name] = rows
        except csv.Error as exc:
            raise ValueError("failed to parse section {0!r} as CSV: {1}".format(name, exc))
    validate_scan_sections(parsed, headers)
    return parsed


def validate_scan_sections(sections, headers):
    required = {
        "run_context": ("TARGET_OWNER", "PROFILE"),
        "table_inventory": ("OWNER", "TABLE_NAME"),
        "column_inventory": ("OWNER", "TABLE_NAME", "COLUMN_NAME"),
    }
    for name, fields in required.items():
        if name not in sections:
            raise ValueError("missing required collector section: {0}".format(name))
        # SQLcl may emit no header for a query returning no rows. A closed,
        # empty inventory section is valid, unlike a missing section.
        if headers[name] or name == "run_context":
            missing = set(fields) - set(headers[name])
            if missing:
                raise ValueError("invalid CSV headers in {0}; missing: {1}".format(name, ", ".join(sorted(missing))))
        for row in sections[name]:
            if any(not present(row.get(field)) for field in fields):
                raise ValueError("missing required values in collector section: {0}".format(name))
    context = sections["run_context"]
    if len(context) != 1 or context[0]["PROFILE"].lower() not in {"scan", "rag"}:
        raise ValueError("run_context must contain one valid row with TARGET_OWNER and PROFILE (scan or rag)")
    table_keys = {table_key(row) for row in sections["table_inventory"]}
    column_tables = {table_key(row) for row in sections["column_inventory"]}
    if table_keys != column_tables:
        raise ValueError("inconsistent table_inventory and column_inventory: every table needs columns and every column needs a table")


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



COMMENT_PLACEHOLDER_RE = re.compile(
    r"(?:\\bTODO\\b|\\bTBD\\b|\\bFIXME\\b|\\bUNKNOWN\\b|"
    r"describe\\s+business\\s+purpose|define\\s+meaning|"
    r"要記載|未記載|説明を記載|内容を記載)",
    re.I,
)
GENERIC_COMMENT_RE = re.compile(
    r"^(?:this\\s+is\\s+)?(?:table|column|field|value|data)(?:\\s+description)?[.。]?$|"
    r"^(?:テーブル|カラム|列|項目|データ|値)(?:の説明|です|情報)?[.。]?$",
    re.I,
)
TEXT_DATA_TYPES = set(["CHAR", "NCHAR", "VARCHAR2", "NVARCHAR2", "CLOB", "NCLOB", "LONG"])
NUMERIC_NAME_SIGNALS = set([
    "AMOUNT", "AMT", "PRICE", "COST", "TOTAL", "QUANTITY", "QTY", "COUNT",
    "SCORE", "RATE", "RATIO", "PERCENT", "PCT", "VALUE", "SEVERITY", "DISCOUNT",
])
DATE_NAME_SIGNALS = set(["DATE", "TIME", "TIMESTAMP", "DATETIME", "WHEN"])
NUMERIC_COMMENT_SIGNALS = [
    "金額", "数量", "単価", "割引率", "スコア", "割合", "百分率", "件数", "重大度",
    "numeric", "number", "amount", "quantity", "price", "score", "rate", "ratio", "percent",
]
DATE_COMMENT_SIGNALS = [
    "日付", "日時", "時刻", "更新日時", "登録日時", "yyyy-mm-dd", "timestamp", "date", "datetime",
]


def normalized_text_length(value):
    text = clean_cell(value)
    text = re.sub(r"[\\s\\-_.。,，;；:：/\\\\()（）\\[\\]【】{}「」『』'\"`]+", "", text)
    return len(text)


def normalize_comment(value):
    text = clean_cell(value).lower()
    return re.sub(r"[\\s\\W_]+", "", text, flags=re.UNICODE)


def is_generic_comment(value):
    text = clean_cell(value)
    if not text:
        return False
    return bool(GENERIC_COMMENT_RE.match(text))


def assess_comment(value, object_type, object_name):
    text = clean_cell(value)
    issues = []
    if not present(text):
        return ["missing"]
    if COMMENT_PLACEHOLDER_RE.search(text):
        issues.append("placeholder")
    minimum = 20 if object_type == "table" else 8
    if normalized_text_length(text) < minimum:
        issues.append("too_short")
    if is_generic_comment(text):
        issues.append("generic")
    normalized = normalize_comment(text)
    normalized_name = normalize_comment(object_name)
    if normalized_name and normalized in set([normalized_name, normalized_name + "table", normalized_name + "column"]):
        issues.append("name_only")
    return sorted(set(issues))


def analyze_comment_quality(sections, data):
    table_keys = data.get("table_keys", [])
    col_keys = data.get("col_keys", [])
    table_comments = sections.get("table_comments", [])
    column_comments = sections.get("column_comments", [])
    table_map = {table_key(row): clean_cell(row.get("COMMENTS")) for row in table_comments}
    column_map = {col_key(row): clean_cell(row.get("COMMENTS")) for row in column_comments}

    table_results = []
    column_results = []
    for owner, table in table_keys:
        comment = table_map.get((owner, table), "")
        table_results.append({
            "object_type": "table",
            "owner": owner,
            "table_name": table,
            "column_name": "",
            "comment": comment,
            "issues": assess_comment(comment, "table", table),
        })
    for owner, table, column in col_keys:
        comment = column_map.get((owner, table, column), "")
        column_results.append({
            "object_type": "column",
            "owner": owner,
            "table_name": table,
            "column_name": column,
            "comment": comment,
            "issues": assess_comment(comment, "column", column),
        })

    # Flag exact duplicate comments only when the duplicated text is short/generic.
    groups = {}
    for item in table_results + column_results:
        comment = clean_cell(item.get("comment"))
        if not present(comment):
            continue
        groups.setdefault(normalize_comment(comment), []).append(item)
    repeated_groups = []
    for normalized, items in groups.items():
        if len(items) < 3:
            continue
        sample = clean_cell(items[0].get("comment"))
        if normalized_text_length(sample) <= 20 or is_generic_comment(sample):
            repeated_groups.append({
                "comment": sample,
                "count": len(items),
                "objects": [format_object_name(item) for item in items],
            })
            for item in items:
                item["issues"] = sorted(set(item["issues"] + ["repeated_generic"]))

    table_good = [item for item in table_results if not item["issues"]]
    column_good = [item for item in column_results if not item["issues"]]
    all_issues = [item for item in table_results + column_results if item["issues"]]
    return {
        "table_results": table_results,
        "column_results": column_results,
        "issues": all_issues,
        "repeated_groups": repeated_groups,
        "table_quality_coverage": ratio(len(table_good), len(table_results)),
        "column_quality_coverage": ratio(len(column_good), len(column_results)),
        "placeholder_count": sum(1 for item in all_issues if "placeholder" in item["issues"]),
        "short_count": sum(1 for item in all_issues if "too_short" in item["issues"]),
        "generic_count": sum(1 for item in all_issues if "generic" in item["issues"] or "name_only" in item["issues"]),
    }


def format_object_name(item):
    if item.get("column_name"):
        return "{0}.{1}.{2}".format(item.get("owner", ""), item.get("table_name", ""), item.get("column_name", ""))
    return "{0}.{1}".format(item.get("owner", ""), item.get("table_name", ""))


def column_name_tokens(name):
    upper = clean_cell(name).upper()
    return [token for token in re.split(r"[^A-Z0-9]+", upper) if token]



def infer_semantic_type(row, comment):
    data_type = clean_cell(row.get("DATA_TYPE")).upper()
    if data_type not in TEXT_DATA_TYPES:
        return None
    name = clean_cell(row.get("COLUMN_NAME")).upper()
    tokens = set(column_name_tokens(name))
    lower_comment = clean_cell(comment).lower()

    # Use exact underscore-delimited tokens to avoid false positives such as
    # COUNTRY -> COUNT, DISCOUNT -> COUNT, and LIFETIME -> TIME.
    date_name_hits = sorted(signal for signal in DATE_NAME_SIGNALS if signal in tokens)
    number_name_hits = sorted(signal for signal in NUMERIC_NAME_SIGNALS if signal in tokens)

    # Common compact date tokens do not always contain underscores.
    date_compound_hits = []
    for token in tokens:
        if token.endswith("DATE") and token not in set(["CANDIDATE", "VALIDATE"]):
            date_compound_hits.append(token)
    date_name_hits = sorted(set(date_name_hits + date_compound_hits))

    # Comments are supporting evidence only when they explicitly describe a
    # typed value stored as text. This avoids treating CURRENCY_CODE as a
    # number merely because its comment mentions an order amount.
    explicit_numeric_phrases = [
        "数値文字列", "小数文字列", "整数文字列", "数値として", "数値変換", "to_number",
        "numeric string", "number string", "convert to number",
    ]
    explicit_date_phrases = [
        "yyyy-mm-dd", "hh24:mi:ss", "日付を", "日時を", "時刻を", "to_date", "to_timestamp",
        "date string", "timestamp string",
    ]
    number_comment_hits = sorted(phrase for phrase in explicit_numeric_phrases if phrase in lower_comment)
    date_comment_hits = sorted(phrase for phrase in explicit_date_phrases if phrase in lower_comment)

    if date_name_hits or date_comment_hits:
        evidence = []
        if date_name_hits:
            evidence.append("name: " + ", ".join(date_name_hits[:3]))
        if date_comment_hits:
            evidence.append("comment: " + ", ".join(date_comment_hits[:3]))
        return "DATE/TIMESTAMP", evidence
    if number_name_hits or number_comment_hits:
        evidence = []
        if number_name_hits:
            evidence.append("name: " + ", ".join(number_name_hits[:3]))
        if number_comment_hits:
            evidence.append("comment: " + ", ".join(number_comment_hits[:3]))
        return "NUMBER", evidence
    return None

def analyze_semantic_types(sections, data):
    comments = {col_key(row): clean_cell(row.get("COMMENTS")) for row in sections.get("column_comments", [])}
    valid_keys = set(data.get("col_keys", []))
    warnings = []
    for row in sections.get("column_inventory", []):
        key = col_key(row)
        if key not in valid_keys:
            continue
        inferred = infer_semantic_type(row, comments.get(key, ""))
        if not inferred:
            continue
        semantic_type, evidence = inferred
        owner, table, column = key
        if semantic_type == "NUMBER":
            recommendation_ja = "NUMBER列、仮想列、または型付きAI用Viewを検討してください。"
            recommendation_en = "Consider a NUMBER column, virtual column, or typed AI-facing view."
        else:
            recommendation_ja = "DATE/TIMESTAMP列、仮想列、または型付きAI用Viewを検討してください。"
            recommendation_en = "Consider a DATE/TIMESTAMP column, virtual column, or typed AI-facing view."
        warnings.append({
            "owner": owner,
            "table_name": table,
            "column_name": column,
            "data_type": clean_cell(row.get("DATA_TYPE")).upper(),
            "inferred_type": semantic_type,
            "evidence": "; ".join(evidence),
            "comment": comments.get(key, ""),
            "recommendation_ja": recommendation_ja,
            "recommendation_en": recommendation_en,
        })
    return sorted(warnings, key=lambda item: (item["owner"], item["table_name"], item["column_name"]))


SEMANTICS_STATES = {
    "collected": ("収集成功", "Collected"),
    "not_collected": ("未収集", "Not collected"),
    "unsupported": ("非対応確認済み", "Confirmed unsupported"),
    "permission_denied": ("権限不足確認済み", "Confirmed permission denied"),
    "unavailable": ("原因未確定の利用不可", "Unavailable; cause undetermined"),
    "error": ("収集エラー", "Collection error"),
}


def load_semantics(path):
    """Read the optional collector's JSON without interpreting metadata as code."""
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate semantics JSON key: {0}".format(key))
            result[key] = value
        return result

    with Path(path).open(encoding="utf-8-sig") as handle:
        payload = json.load(handle, object_pairs_hook=unique_keys)
    validate_semantics(payload)
    return payload


def validate_semantics(payload):
    if not isinstance(payload, dict) or payload.get("format") != "oracle-ai-semantics-v1":
        raise ValueError("expected oracle-ai-semantics-v1 JSON")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("semantics records must be an array")
    statuses = set()
    context_count = 0
    required = {
        "table": ("owner", "table_name"),
        "column": ("owner", "table_name", "column_name"),
        "annotation": ("owner", "object_name", "object_type", "annotation_name"),
        "domain": ("owner", "table_name", "column_name"),
    }
    for row in records:
        if (not isinstance(row, dict) or not isinstance(row.get("type"), str)
                or row["type"] not in set(required) | {"context", "status"}):
            raise ValueError("invalid semantics record type")
        if any(value is not None and not isinstance(value, (str, int, float)) for value in row.values()):
            raise ValueError("semantics record fields must be scalar strings or numbers")
        for key in required.get(row["type"], ()):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError("missing semantics {0}.{1}".format(row["type"], key))
        if row["type"] == "domain" and not (clean_cell(row.get("domain_owner")) or clean_cell(row.get("domain_name"))):
            raise ValueError("domain association needs a domain owner or name")
        # Metadata text must remain text, including a legitimate literal 'NULL'.
        for key, value in row.items():
            if key not in {"error_code", "domain_association_id"} and value is not None and not isinstance(value, str):
                raise ValueError("semantics {0} must be text or null".format(key))
        if row["type"] == "context":
            context_count += 1
            if context_count > 1:
                raise ValueError("duplicate semantics context")
        if row["type"] == "status":
            component = row.get("component")
            if component not in {"scope", "annotations", "domains"} or component in statuses:
                raise ValueError("invalid or duplicate semantics status component")
            if row.get("state") not in SEMANTICS_STATES:
                raise ValueError("invalid semantics collection state")
            statuses.add(component)


def analyze_ai_semantics(data, payload=None):
    """Advisory only. Never feed these counts into score or COMMENT gates."""
    if payload is not None:
        validate_semantics(payload)
    records = payload.get("records", []) if payload is not None else []
    statuses = {name: {"state": "not_collected", "diagnostic": ""}
                for name in ("scope", "annotations", "domains")}
    context = {}
    for row in records:
        if row["type"] == "status":
            statuses[row["component"]] = dict(row)
        elif row["type"] == "context":
            context = dict(row)

    def key(row, table_field="table_name"):
        return (clean_cell(row.get("owner")).upper(), clean_cell(row.get(table_field)).upper())

    def column_key(row, table_field="table_name"):
        return key(row, table_field) + (clean_cell(row.get("column_name")).upper(),)

    base_tables = set(data.get("table_keys", []))
    base_columns = set(data.get("col_keys", []))
    scope_ok = statuses["scope"]["state"] == "collected"
    scope_tables = {key(row) for row in records if row["type"] == "table"} & base_tables if scope_ok else set()
    scope_columns = {column_key(row) for row in records if row["type"] == "column"
                     and key(row) in scope_tables} & base_columns if scope_ok else set()
    annotations_ok = scope_ok and statuses["annotations"]["state"] == "collected"
    domains_ok = scope_ok and statuses["domains"]["state"] == "collected"
    annotated, direct, inherited, unknown, table_annotations, linked = (set() for _ in range(6))
    annotations, domains = [], []
    excluded = 0
    seen_annotations, seen_domains = set(), set()
    for row in records:
        kind = row["type"]
        if not scope_ok:
            # Partial inventory is not evidence that its semantic rows are out of scope.
            continue
        if kind == "annotation":
            target = column_key(row, "object_name")
            is_column = bool(target[2])
            if row.get("object_type", "").upper() != "TABLE" or target[:2] not in scope_tables or (is_column and target not in scope_columns):
                excluded += 1
                continue
            if not annotations_ok:
                continue
            domain_owner = clean_cell(row.get("domain_owner"))
            domain_name = clean_cell(row.get("domain_name"))
            declared_origin = clean_cell(row.get("origin")).upper()
            if domain_owner and domain_name and declared_origin in {"", "DOMAIN_INHERITED"}:
                origin = "DOMAIN_INHERITED"
            elif (not domain_owner and not domain_name and "domain_owner" in row and "domain_name" in row
                  and declared_origin in {"", "DIRECT"}):
                origin = "DIRECT"
            else:
                origin = "UNKNOWN"
            item = dict(row, origin=origin)
            signature = (target, row.get("annotation_name"), row.get("annotation_value"), domain_owner, domain_name, origin)
            if signature in seen_annotations:
                continue
            seen_annotations.add(signature)
            annotations.append(item)
            if is_column:
                annotated.add(target)
                {"DIRECT": direct, "DOMAIN_INHERITED": inherited, "UNKNOWN": unknown}[origin].add(target)
            else:
                table_annotations.add(target[:2])
        elif kind == "domain":
            target = column_key(row)
            if target not in scope_columns:
                excluded += 1
                continue
            if not domains_ok:
                continue
            signature = (target, row.get("domain_owner"), row.get("domain_name"), row.get("domain_column_name"))
            if signature not in seen_domains:
                seen_domains.add(signature)
                linked.add(target)
                domains.append(dict(row))
    annotations.sort(key=lambda row: (key(row, "object_name"), row.get("column_name") or "", row["annotation_name"], row["origin"]))
    domains.sort(key=lambda row: column_key(row))
    return {
        "statuses": statuses, "context": context,
        "scope_state": statuses["scope"]["state"],
        "annotations_state": statuses["annotations"]["state"],
        "domains_state": statuses["domains"]["state"],
        "total_tables": len(scope_tables) if scope_ok else None,
        "total_columns": len(scope_columns) if scope_ok else None,
        "scan_total_columns": len(base_columns),
        "annotated_columns": len(annotated) if annotations_ok else None,
        "direct_columns": len(direct) if annotations_ok else None,
        "inherited_columns": len(inherited) if annotations_ok else None,
        "unknown_origin_columns": len(unknown) if annotations_ok else None,
        "domain_linked_columns": len(linked) if domains_ok else None,
        "table_annotations": len(table_annotations) if annotations_ok else None,
        "coverage": float(len(annotated)) / len(scope_columns) if annotations_ok and scope_columns else None,
        "annotations": annotations, "domains": domains, "excluded_records": excluded,
        "runtime_evidence": {name: "unverified" for name in
                             ("dictionary_registration", "profile_settings", "showprompt", "sql_review", "saved_sql_execution", "runsql_trial")},
    }


def enrich_analysis(sections, data, semantics=None):
    data["comment_quality"] = analyze_comment_quality(sections, data)
    data["semantic_type_warnings"] = analyze_semantic_types(sections, data)
    table_key_set = set(data.get("table_keys", []))
    source_tables = intersect_table_keys(sections.get("source_metadata_columns", []), table_key_set)
    data["source_missing_tables"] = [key for key in data.get("table_keys", []) if key not in source_tables]
    data["metrics"]["table_comment_quality_coverage"] = data["comment_quality"]["table_quality_coverage"]
    data["metrics"]["column_comment_quality_coverage"] = data["comment_quality"]["column_quality_coverage"]
    data["ai_semantics"] = analyze_ai_semantics(data, semantics)
    return data


def comment_quality_status(data):
    quality = data.get("comment_quality", {})
    if not data.get("mandatory_gate_pass"):
        return "fail"
    if quality.get("issues"):
        return "warning"
    return "pass"


def build_next_actions(data, lang):
    actions = []
    missing_tables = len(data.get("missing_table_comments", []))
    missing_columns = len(data.get("missing_column_comments", []))
    quality_issues = len(data.get("comment_quality", {}).get("issues", []))
    pk_missing = len(data.get("pk_missing_tables", []))
    stats_missing = len(data.get("stats_missing_tables", [])) + len(data.get("stale_stats", []))
    freshness_missing = len(data.get("freshness_missing_tables", []))
    source_missing = len(data.get("source_missing_tables", []))
    broad_data = len(data.get("broad_data_grants", []))
    sensitive = len(data.get("sensitive_cols", []))
    semantic = len(data.get("semantic_type_warnings", []))
    profile = data.get("profile", "scan")

    if lang == "ja":
        if missing_tables or missing_columns:
            actions.append("欠落しているテーブルコメント{0}件、カラムコメント{1}件を補完し、Mandatory comment gateをpassにします。".format(missing_tables, missing_columns))
        elif quality_issues:
            actions.append("品質レビュー対象のコメント{0}件について、TODO、短すぎる説明、汎用文を業務内容に置き換えます。".format(quality_issues))
        structural = []
        if pk_missing:
            structural.append("主キー未定義{0}表".format(pk_missing))
        if stats_missing:
            structural.append("未取得または古い統計{0}表".format(stats_missing))
        if freshness_missing:
            structural.append("鮮度列未定義{0}表".format(freshness_missing))
        if source_missing:
            structural.append("出所列未定義{0}表".format(source_missing))
        if structural:
            actions.append("構造・運用メタデータを改善します: {0}。".format("、".join(structural)))
        if semantic:
            actions.append("文字列型に保存された数値・日付候補{0}列を確認し、型付き列、仮想列、またはAI用Viewを検討します。".format(semantic))
        security = []
        if broad_data:
            security.append("広いデータ権限{0}件".format(broad_data))
        if sensitive:
            security.append("機微情報候補{0}列".format(sensitive))
        if security:
            actions.append("DBA・業務オーナーがセキュリティとプライバシーを確認します: {0}。".format("、".join(security)))
        if profile == "rag" and metric(data, "vector_table_coverage") == 0.0:
            actions.append("RAG用途では、VECTOR列または外部embedding保管場所、chunking、更新方式、Vector Indexを設計します。")
        if not actions:
            actions.append("自動検出された必須改善事項はありません。データモデル変更時にもコメント、制約、鮮度、出所、統計情報を維持してください。")
    else:
        if missing_tables or missing_columns:
            actions.append("Add {0} missing table comments and {1} missing column comments so the mandatory gate passes.".format(missing_tables, missing_columns))
        elif quality_issues:
            actions.append("Review {0} low-quality comments and replace placeholders, overly short text, or generic wording.".format(quality_issues))
        structural = []
        if pk_missing:
            structural.append("{0} tables without primary keys".format(pk_missing))
        if stats_missing:
            structural.append("{0} tables with missing/stale statistics".format(stats_missing))
        if freshness_missing:
            structural.append("{0} tables without freshness columns".format(freshness_missing))
        if source_missing:
            structural.append("{0} tables without source metadata".format(source_missing))
        if structural:
            actions.append("Remediate structural and operational metadata: {0}.".format(", ".join(structural)))
        if semantic:
            actions.append("Review {0} text columns that appear to contain numeric/date values and consider typed columns, virtual columns, or AI-facing views.".format(semantic))
        security = []
        if broad_data:
            security.append("{0} broad data grants".format(broad_data))
        if sensitive:
            security.append("{0} sensitive-name candidates".format(sensitive))
        if security:
            actions.append("Have DBAs and business owners review security/privacy items: {0}.".format(", ".join(security)))
        if profile == "rag" and metric(data, "vector_table_coverage") == 0.0:
            actions.append("For RAG, design VECTOR or external embedding storage, chunking, refresh, and indexing.")
        if not actions:
            actions.append("No mandatory automatic remediation remains. Preserve comments, constraints, freshness, source metadata, and statistics as the model evolves.")
    return actions

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



def render_comment_quality_markdown(data, lang):
    quality = data.get("comment_quality", {})
    lines = []
    if lang == "ja":
        lines.extend([
            "| 項目 | 値 |",
            "|---|---:|",
            "| Table comment quality coverage | {0} |".format(pct(quality.get("table_quality_coverage", 0.0))),
            "| Column comment quality coverage | {0} |".format(pct(quality.get("column_quality_coverage", 0.0))),
            "| Placeholder comments | {0} |".format(quality.get("placeholder_count", 0)),
            "| Too-short comments | {0} |".format(quality.get("short_count", 0)),
            "| Generic/name-only comments | {0} |".format(quality.get("generic_count", 0)),
            "| Repeated generic groups | {0} |".format(len(quality.get("repeated_groups", []))),
        ])
        if quality.get("issues"):
            lines.extend(["", "| Object | Issue | Current comment |", "|---|---|---|"])
            for item in quality.get("issues", []):
                lines.append("| {0} | {1} | {2} |".format(
                    md_escape(format_object_name(item)),
                    md_escape(", ".join(item.get("issues", []))),
                    md_escape(item.get("comment", "")),
                ))
        else:
            lines.extend(["", "- コメント品質の自動レビュー対象はありません。"])
    else:
        lines.extend([
            "| Item | Value |",
            "|---|---:|",
            "| Table comment quality coverage | {0} |".format(pct(quality.get("table_quality_coverage", 0.0))),
            "| Column comment quality coverage | {0} |".format(pct(quality.get("column_quality_coverage", 0.0))),
            "| Placeholder comments | {0} |".format(quality.get("placeholder_count", 0)),
            "| Too-short comments | {0} |".format(quality.get("short_count", 0)),
            "| Generic/name-only comments | {0} |".format(quality.get("generic_count", 0)),
            "| Repeated generic groups | {0} |".format(len(quality.get("repeated_groups", []))),
        ])
        if quality.get("issues"):
            lines.extend(["", "| Object | Issue | Current comment |", "|---|---|---|"])
            for item in quality.get("issues", []):
                lines.append("| {0} | {1} | {2} |".format(
                    md_escape(format_object_name(item)),
                    md_escape(", ".join(item.get("issues", []))),
                    md_escape(item.get("comment", "")),
                ))
        else:
            lines.extend(["", "- No automatic comment-quality findings."])
    return lines


def render_semantic_markdown(data, lang):
    warnings = data.get("semantic_type_warnings", [])
    if not warnings:
        return ["- Semantic type mismatch候補はありません。" if lang == "ja" else "- No semantic type mismatch candidates."]
    if lang == "ja":
        lines = [
            "文字列型ですが、列名またはコメントから数値・日付として扱われる可能性がある列です。推定結果のため、自動的な型変更は行いません。",
            "",
            "| Column | DB type | 推定される意味 | 根拠 | 推奨対応 |",
            "|---|---|---|---|---|",
        ]
        for item in warnings:
            lines.append("| {0} | {1} | {2} | {3} | {4} |".format(
                md_escape("{0}.{1}.{2}".format(item["owner"], item["table_name"], item["column_name"])),
                md_escape(item["data_type"]),
                md_escape(item["inferred_type"]),
                md_escape(item["evidence"]),
                md_escape(item["recommendation_ja"]),
            ))
    else:
        lines = [
            "These text columns appear to represent numeric or date/time values based on names/comments. This is heuristic and does not generate automatic type changes.",
            "",
            "| Column | DB type | Inferred meaning | Evidence | Recommendation |",
            "|---|---|---|---|---|",
        ]
        for item in warnings:
            lines.append("| {0} | {1} | {2} | {3} | {4} |".format(
                md_escape("{0}.{1}.{2}".format(item["owner"], item["table_name"], item["column_name"])),
                md_escape(item["data_type"]),
                md_escape(item["inferred_type"]),
                md_escape(item["evidence"]),
                md_escape(item["recommendation_en"]),
            ))
    return lines


def ai_semantics_sections(data, lang):
    """One presentation model shared by Markdown and HTML."""
    model = data.get("ai_semantics") or analyze_ai_semantics(data)
    ja = lang == "ja"
    label = lambda jp, en: jp if ja else en
    value = lambda item: "N/A" if item is None else str(item)
    status_rows = []
    for component in ("scope", "annotations", "domains"):
        record = model["statuses"][component]
        state = record["state"]
        status_rows.append([component, state + " / " + SEMANTICS_STATES[state][0 if ja else 1], record.get("diagnostic") or "—"])
    coverage = "N/A" if model["coverage"] is None else "{0:.2f}%".format(model["coverage"] * 100)
    metrics = [
        [label("収集対象の表数", "Collected scope tables"), value(model["total_tables"])],
        [label("収集対象の列数（重複排除）", "Collected scope distinct columns"), value(model["total_columns"])],
        [label("元の評価対象列数", "Original scan columns"), value(model["scan_total_columns"])],
        [label("表Annotationがある表数", "Tables with table annotations"), value(model["table_annotations"])],
        ["Annotated columns", value(model["annotated_columns"])],
        ["Direct columns", value(model["direct_columns"])],
        ["Domain-inherited columns", value(model["inherited_columns"])],
        [label("由来不明の列数", "Unknown-origin columns"), value(model["unknown_origin_columns"])],
        ["Domain-linked columns", value(model["domain_linked_columns"])],
        ["Column annotation coverage", coverage],
        [label("対象外の意味情報レコード（除外）", "Excluded out-of-scope semantic records"), str(model["excluded_records"])],
    ]
    context = [[key, value(model["context"].get(key))] for key in
               ("session_user", "current_schema", "target_owner", "table_like_pattern", "db_name", "con_name", "collected_at")]
    annotation_rows = []
    for row in model["annotations"]:
        object_name = "{0}.{1}".format(row["owner"], row["object_name"])
        if row.get("column_name"):
            object_name += "." + row["column_name"]
        category = row["annotation_name"].upper()
        if category not in {"DESCRIPTION", "ALIASES", "VALUES"}:
            category = label("その他", "Other")
        annotation_rows.append([
            object_name, "COLUMN" if row.get("column_name") else "TABLE", category,
            row["annotation_name"], row.get("annotation_value") if row.get("annotation_value") is not None else label("（値なし）", "(valueless)"),
            row["origin"], ".".join(filter(None, [row.get("domain_owner"), row.get("domain_name")])) or "—",
        ])
    domain_rows = [["{0}.{1}.{2}".format(row["owner"], row["table_name"], row["column_name"]),
                    "{0}.{1}".format(row.get("domain_owner") or "?", row.get("domain_name") or "?"),
                    row.get("domain_column_name") or "—"] for row in model["domains"]]
    evidence_rows = [
        [label("辞書登録（観測）", "Dictionary registration (observed)"),
         label("収集値を参照。業務上の正しさは未確認", "See collected metadata; business meaning unverified")
         if model["scope_state"] == "collected" and model["annotations_state"] == "collected" else label("未確認", "Unverified")],
    ]
    for jp, en in [("Profile設定", "Profile settings"), ("SHOWPROMPT確認", "SHOWPROMPT inspection"),
                   ("生成SQLレビュー", "Generated SQL review"), ("保存SQLの実行", "Saved SQL execution"),
                   ("別試行RUNSQL", "Separate RUNSQL trial")]:
        evidence_rows.append([label(jp, en), label("未確認", "Unverified")])
    return {
        "notes": [
            label("Annotation／Domainは任意のAdvisoryです。件数・coverageでスコアやCOMMENT必須ゲートは変わりません。",
                  "Annotations and domains are optional advisory metadata. Counts and coverage do not change scores or mandatory COMMENT gates."),
            label("coverageの母数は、補助Collectorの収集対象と元の評価対象が重なるdistinct列です。直接登録と継承が同じ列にある場合も全体では1列です。未収集・失敗・対象列0件はN/Aです。",
                  "Coverage uses distinct columns shared by the collector scope and original scan. A column with both direct and inherited annotations counts once overall. Uncollected, failed, or zero-column scope is N/A."),
            label("値なしAnnotationや任意ラベルも有効です。登録数は意味の正しさを保証しません。DESCRIPTION／ALIASES／VALUESを含む内容は業務担当者が確認してください。Domain名の ? は由来情報の不足です。",
                  "Valueless annotations and arbitrary labels are valid. Registration counts do not prove semantic correctness. A business owner must review meaning, including DESCRIPTION, ALIASES, and VALUES. A ? in a domain identifier means missing provenance information."),
            label("ALL_*で現セッションに見える範囲のみです。データ所有者と実行Userの可視性、収集日時、対象範囲を照合してください。View経由の継承や高度なDomain機能は未対応です。",
                  "Only metadata visible to the current session through ALL_* is covered. Compare the data owner's and execution user's visibility, timestamps, and scope. View inheritance and advanced domain features are outside this version's scope."),
            label("ランタイム証跡は references/semantics-evidence-template.md に独立して記録してください。RUNSQLは別の生成試行であり、レビューした保存SQLの実行ではありません。",
                  "Record runtime evidence separately using references/semantics-evidence-template.md. RUNSQL is a separate generation trial, not execution of the reviewed saved SQL."),
        ],
        "tables": [
            (label("収集状態", "Collection states"), ["Component", "State", "Diagnostic"], status_rows),
            (label("集計", "Metrics"), ["Metric", "Value"], metrics),
            (label("収集コンテキスト", "Collection context"), ["Field", "Value"], context),
            (label("Annotationと由来", "Annotations and provenance"), ["Object", "Level", "Category", "Name", "Value", "Origin", "Domain"], annotation_rows),
            (label("列のDomain関連付け", "Column domain associations"), ["Column", "Domain", "Domain column"], domain_rows),
            (label("独立した検証事項", "Independent verification stages"), ["Stage", "Evidence"], evidence_rows),
        ],
    }


def semantics_md_cell(value):
    """Neutralize HTML and Markdown syntax; only our own <br> is markup."""
    text = str(value) if value is not None else "—"
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = html_escape(text, quote=True)
    for char in "\\`*_{}[]()|!~":
        text = text.replace(char, "&#{0};".format(ord(char)))
    return text.replace("\n", "<br>")


def render_ai_semantics_markdown(data, lang):
    presentation = ai_semantics_sections(data, lang)
    lines = ["", "## 13. AI Semantics Readiness (Advisory)", ""]
    lines.extend(presentation["notes"])
    for title, headers, rows in presentation["tables"]:
        lines.extend(["", "### " + title, "", "| " + " | ".join(headers) + " |",
                      "| " + " | ".join("---" for _ in headers) + " |"])
        if not rows:
            rows = [["該当する収集済みレコードなし" if lang == "ja" else "No collected records"] + ["—"] * (len(headers) - 1)]
        for row in rows:
            lines.append("| " + " | ".join(semantics_md_cell(cell) for cell in row) + " |")
    return lines


def render_ai_semantics_html(data, lang):
    presentation = ai_semantics_sections(data, lang)
    esc = lambda value: html_escape(str(value), quote=True).replace("\n", "<br>")
    parts = ['<section id="ai-semantics"><h2>AI Semantics Readiness (Advisory)</h2>']
    parts.extend("<p>{0}</p>".format(esc(note)) for note in presentation["notes"])
    for title, headers, rows in presentation["tables"]:
        parts.append("<h3>{0}</h3><div class=\"table-wrap\"><table><thead><tr>{1}</tr></thead><tbody>".format(
            esc(title), "".join("<th>{0}</th>".format(esc(header)) for header in headers)))
        if not rows:
            rows = [["該当する収集済みレコードなし" if lang == "ja" else "No collected records"] + ["—"] * (len(headers) - 1)]
        for row in rows:
            parts.append("<tr>{0}</tr>".format("".join("<td>{0}</td>".format(esc(cell)) for cell in row)))
        parts.append("</tbody></table></div>")
    parts.append("</section>")
    return "".join(parts)


def build_sql_text(data, max_sql, max_items, lang):
    comment_sql, omitted_sql = make_comment_sql(data, max_sql, lang)
    advisory_sql = make_advisory_sql(data, max_items, lang)
    all_sql = list(comment_sql)
    if omitted_sql:
        all_sql.append("-- {0} additional COMMENT statements omitted because --max-sql was reached.".format(omitted_sql))
    all_sql.extend(advisory_sql)
    sql_text = "\n".join(all_sql).strip()
    if not sql_text:
        sql_text = "-- No executable improvement SQL generated from the available metadata."
    return sql_text + "\n"


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
    sql_text = build_sql_text(data, max_sql, max_items, lang)
    actions = build_next_actions(data, lang)
    quality_state = comment_quality_status(data)

    if lang == "ja":
        lines = [
            "# " + title,
            "",
            "## 1. エグゼクティブサマリー",
            "- 総合スコア: **{0} / 1.00**".format(score(overall)),
            "- Profile: **{0}**".format(profile),
            "- Mandatory comment gate: **{0}**".format(gate_label),
            "- Comment quality review: **{0}**".format(quality_state),
            "- Semantic type warnings: **{0}件**".format(len(data.get("semantic_type_warnings", []))),
            "- 結論: **{0}**".format(conclusion),
            "- コメント有無チェックは必須条件です。コメント品質とSemantic type mismatchは初期実装では警告であり、既存スコアには影響しません。",
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
            "| 注意事項 | ALL_* dictionary viewsで見えるメタデータを評価します。実データ値、業務上の正しさ、法令遵守は別途レビューが必要です。 |",
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
            "| Table comment quality coverage | {0} | {1} | コメント本文がplaceholder、短すぎる説明、汎用文ではない割合です。初期実装では警告のみです。 |".format(pct(metric(data, "table_comment_quality_coverage")), quality_state),
            "| Column comment quality coverage | {0} | {1} | コメント本文がplaceholder、短すぎる説明、汎用文ではない割合です。初期実装では警告のみです。 |".format(pct(metric(data, "column_comment_quality_coverage")), quality_state),
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
        lines.extend(["", "## 8. コメント品質"])
        lines.extend(render_comment_quality_markdown(data, lang))
        lines.extend(["", "## 9. Semantic type mismatch"])
        lines.extend(render_semantic_markdown(data, lang))
        lines.extend([
            "",
            "## 10. 改善SQLの考え方",
            "| SQLカテゴリ | 理由 | 目的 | 実行前確認 |",
            "|---|---|---|---|",
            "| COMMENT ON TABLE / COLUMN | コメント欠落はmandatory gateとContextual scoreを下げます。 | 業務意味、粒度、単位、NULL意味、機微性を明文化します。 | TODO文を実説明に置換し、業務オーナー承認後に実行します。 |",
            "| Comment quality review | コメントが存在してもplaceholderや汎用文ではAIへ十分な意味を伝えられません。 | 実際の業務説明へ置き換えます。 | 自動上書きはせず、人間がレビューします。 |",
            "| Semantic type review | 文字列型に数値・日付が保存されるとNL2SQLで暗黙変換や文字列比較が発生します。 | 型付き列、仮想列、AI用Viewを検討します。 | 自動ALTERは生成しません。データとアプリ影響を確認します。 |",
            "| DBMS_STATS.GATHER_TABLE_STATS | LAST_ANALYZED未設定/古い統計はClean/Current scoreを下げます。 | 統計情報を収集します。 | 大規模表ではDBA確認が必要です。 |",
            "| PRIMARY KEY / freshness column | キーや鮮度列の不足は根拠追跡や新しさ説明を弱くします。 | 根拠行の特定と鮮度説明を可能にします。 | テンプレートのため設計レビューが必要です。 |",
            "| REVOKE候補 | 広いデータ権限はAI利用前の公開範囲確認が必要です。 | 不要な公開を減らします。 | 依存利用者への影響を確認します。 |",
            "",
            "```sql",
            sql_text.rstrip(),
            "```",
            "",
            "## 11. 手動レビューが必要な項目",
            "- 機微情報候補列: {0}件。業務オーナーによる分類が必要です。".format(len(data["sensitive_cols"])),
            "- 広いデータ権限候補: {0}件。DBA確認が必要です。".format(len(data["broad_data_grants"])),
            "- Semantic type mismatch候補: {0}件。推定のため業務・アプリ仕様と照合してください。".format(len(data.get("semantic_type_warnings", []))),
            "- 主キー、外部キー、更新日時、データ粒度、保持期間はアプリケーション仕様と照合してください。",
            "",
            "## 12. 次のアクション",
        ])
        for index, action in enumerate(actions, 1):
            lines.append("{0}. {1}".format(index, action))
    else:
        lines = [
            "# " + title,
            "",
            "## 1. Executive summary",
            "- Overall score: **{0} / 1.00**".format(score(overall)),
            "- Profile: **{0}**".format(profile),
            "- Mandatory comment gate: **{0}**".format(gate_label),
            "- Comment quality review: **{0}**".format(quality_state),
            "- Semantic type warnings: **{0}**".format(len(data.get("semantic_type_warnings", []))),
            "- Conclusion: **{0}**".format(conclusion),
            "- Comment presence is mandatory. Comment quality and semantic type checks are warnings and do not change existing scores in this version.",
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
            "| Caveat | Assesses metadata visible through ALL_* views; data correctness and compliance require separate review. |",
            "",
            "## 3. Dimension definitions",
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
            "| Consumable | {0} | {1} | text tables {2}, vector tables {3}, documentation {4}, PK {5} |".format(format_weight(weights, "consumable"), score(dimensions["consumable"]), pct(metric(data, "text_table_coverage")), pct(metric(data, "vector_table_coverage")), pct((metric(data, "table_comment_coverage") + metric(data, "column_comment_coverage")) / 2.0), pct(metric(data, "pk_coverage"))),
            "| Current | {0} | {1} | freshness {2}, recent stats {3} |".format(format_weight(weights, "current"), score(dimensions["current"]), pct(metric(data, "freshness_coverage")), pct(metric(data, "recent_stats_coverage"))),
            "| Correlated | {0} | {1} | FK {2}, source metadata {3}, PK {4} |".format(format_weight(weights, "correlated"), score(dimensions["correlated"]), pct(metric(data, "fk_coverage")), pct(metric(data, "source_coverage")), pct(metric(data, "pk_coverage"))),
            "| Compliant | {0} | {1} | sensitive documented {2}, broad grant absence {3} |".format(format_weight(weights, "compliant"), score(dimensions["compliant"]), pct(metric(data, "sensitive_documented_coverage")), pct(metric(data, "broad_data_grant_absence"))),
            "",
            "## 5. Metric details",
            "| Metric | Value | Status | Explanation |",
            "|---|---:|---|---|",
        ])
        lines.extend(render_metric_rows(data, lang))
        lines.extend([
            "| Table comment quality coverage | {0} | {1} | Share of table comments without placeholders, overly short text, or generic wording. Warning only. |".format(pct(metric(data, "table_comment_quality_coverage")), quality_state),
            "| Column comment quality coverage | {0} | {1} | Share of column comments without placeholders, overly short text, or generic wording. Warning only. |".format(pct(metric(data, "column_comment_quality_coverage")), quality_state),
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
        lines.extend(["", "## 8. Comment quality"])
        lines.extend(render_comment_quality_markdown(data, lang))
        lines.extend(["", "## 9. Semantic type mismatch"])
        lines.extend(render_semantic_markdown(data, lang))
        lines.extend([
            "",
            "## 10. Improvement SQL rationale",
            "```sql",
            sql_text.rstrip(),
            "```",
            "",
            "## 11. Manual review items",
            "- Sensitive-name candidates: {0}.".format(len(data["sensitive_cols"])),
            "- Broad data grant candidates: {0}.".format(len(data["broad_data_grants"])),
            "- Semantic type mismatch candidates: {0}.".format(len(data.get("semantic_type_warnings", []))),
            "- Validate keys, freshness, data grain, and retention against application design.",
            "",
            "## 12. Next actions",
        ])
        for index, action in enumerate(actions, 1):
            lines.append("{0}. {1}".format(index, action))
    lines.extend(render_ai_semantics_markdown(data, lang))
    return "\n".join(lines).rstrip() + "\n", sql_text


def html_status_class(status):
    return {"pass": "pass", "good": "pass", "warning": "warning", "review": "warning", "fail": "fail"}.get(status, "info")


def render_html(data, source, sql_text, lang):
    ctx = first_context(data)
    overall = float(data["overall"])
    gate = "pass" if data["mandatory_gate_pass"] else "fail"
    quality = comment_quality_status(data)
    conclusion = interpretation(overall, bool(data["mandatory_gate_pass"]), lang)
    actions = build_next_actions(data, lang)
    title = "Oracle Database AI Ready 評価レポート" if lang == "ja" else "Oracle Database AI Ready Assessment Report"
    dimensions = data["dimension_scores"]
    weights = data["weights"]
    quality_data = data.get("comment_quality", {})
    semantic = data.get("semantic_type_warnings", [])

    def esc(value):
        return html_escape(clean_cell(value), quote=True)

    dim_rows = []
    for name in ["clean", "contextual", "consumable", "current", "correlated", "compliant"]:
        value = float(dimensions[name])
        dim_rows.append(
            '<tr><td>{0}</td><td>{1}</td><td><div class="bar"><span style="width:{2:.1f}%"></span></div></td><td>{3}</td></tr>'.format(
                esc(name.title()), esc(format_weight(weights, name)), value * 100.0, esc(score(value))
            )
        )

    metric_labels = [
        ("table_comment_coverage", "Table comment coverage"),
        ("column_comment_coverage", "Column comment coverage"),
        ("table_comment_quality_coverage", "Table comment quality coverage"),
        ("column_comment_quality_coverage", "Column comment quality coverage"),
        ("pk_coverage", "PK coverage"),
        ("fk_coverage", "FK coverage"),
        ("relationship_coverage", "Relationship coverage"),
        ("constraint_coverage", "Constraint coverage"),
        ("table_stats_coverage", "Table stats coverage"),
        ("column_stats_coverage", "Column stats coverage"),
        ("recent_stats_coverage", "Recent stats coverage"),
        ("freshness_coverage", "Freshness coverage"),
        ("source_coverage", "Source metadata coverage"),
        ("text_table_coverage", "Text-bearing table coverage"),
        ("vector_table_coverage", "Vector table coverage"),
        ("sensitive_documented_coverage", "Sensitive documentation"),
        ("broad_data_grant_absence", "Broad data grant absence"),
    ]
    metric_rows = []
    for key, label in metric_labels:
        value = metric(data, key)
        if key in set(["table_comment_coverage", "column_comment_coverage"]):
            status = "pass" if value >= 1.0 else "fail"
        elif key in set(["table_comment_quality_coverage", "column_comment_quality_coverage"]):
            status = quality
        elif key in set(["text_table_coverage", "vector_table_coverage"]):
            status = "info"
        elif key == "broad_data_grant_absence":
            status = "pass" if value >= 1.0 else ("warning" if value >= 0.8 else "fail")
        else:
            status = "pass" if value >= 0.8 else ("warning" if value >= 0.5 else "fail")
        metric_rows.append('<tr><td>{0}</td><td>{1}</td><td><span class="badge {2}">{3}</span></td></tr>'.format(
            esc(label), esc(pct(value)), html_status_class(status), esc(status.upper())
        ))

    quality_rows = []
    for item in quality_data.get("issues", []):
        quality_rows.append('<tr><td>{0}</td><td>{1}</td><td>{2}</td></tr>'.format(
            esc(format_object_name(item)), esc(", ".join(item.get("issues", []))), esc(item.get("comment", ""))
        ))
    if not quality_rows:
        quality_rows.append('<tr><td colspan="3">{0}</td></tr>'.format(esc("コメント品質の自動レビュー対象はありません。" if lang == "ja" else "No automatic comment-quality findings.")))

    semantic_rows = []
    for item in semantic:
        recommendation = item["recommendation_ja"] if lang == "ja" else item["recommendation_en"]
        semantic_rows.append('<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td><td>{4}</td></tr>'.format(
            esc("{0}.{1}.{2}".format(item["owner"], item["table_name"], item["column_name"])),
            esc(item["data_type"]), esc(item["inferred_type"]), esc(item["evidence"]), esc(recommendation)
        ))
    if not semantic_rows:
        semantic_rows.append('<tr><td colspan="5">{0}</td></tr>'.format(esc("Semantic type mismatch候補はありません。" if lang == "ja" else "No semantic type mismatch candidates.")))

    action_items = "".join("<li>{0}</li>".format(esc(item)) for item in actions)
    finding_lines = render_findings(data, lang)
    findings_html = "".join("<p>{0}</p>".format(esc(line.lstrip("- "))) for line in finding_lines if line.startswith("- "))

    css = r'''
:root{--bg:#f4f7fb;--panel:#fff;--text:#1f2937;--muted:#64748b;--line:#dbe4ef;--accent:#2563eb;--pass:#15803d;--warn:#b45309;--fail:#b91c1c;--info:#475569}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans JP",sans-serif;line-height:1.6}
main{max-width:1180px;margin:0 auto;padding:28px}h1{font-size:2rem;margin:0 0 8px}h2{margin-top:38px;border-bottom:2px solid var(--line);padding-bottom:8px}h3{margin-top:24px}.muted{color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin:22px 0}.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:0 4px 18px rgba(15,23,42,.05)}.card .label{color:var(--muted);font-size:.9rem}.card .value{font-size:1.65rem;font-weight:700;margin-top:4px}
.badge{display:inline-block;padding:3px 10px;border-radius:999px;font-weight:700;font-size:.78rem}.badge.pass{background:#dcfce7;color:var(--pass)}.badge.warning{background:#ffedd5;color:var(--warn)}.badge.fail{background:#fee2e2;color:var(--fail)}.badge.info{background:#e2e8f0;color:var(--info)}
section{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px;margin:18px 0;box-shadow:0 4px 18px rgba(15,23,42,.04)}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:650px}th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:#f8fafc}.bar{height:10px;background:#e2e8f0;border-radius:999px;overflow:hidden;min-width:180px}.bar span{display:block;height:100%;background:var(--accent)}
pre{white-space:pre-wrap;word-break:break-word;background:#0f172a;color:#e2e8f0;border-radius:10px;padding:16px;overflow:auto}details summary{cursor:pointer;font-weight:700;padding:8px 0}ol{padding-left:1.4rem}@media print{body{background:#fff}main{max-width:none;padding:0}.card,section{box-shadow:none;break-inside:avoid}}
'''

    html = '''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{css}</style></head>
<body><main>
<header><h1>{title}</h1><p class="muted">{source}</p></header>
<div class="cards">
<div class="card"><div class="label">Overall score</div><div class="value">{overall}</div></div>
<div class="card"><div class="label">Mandatory comment gate</div><div class="value"><span class="badge {gate_class}">{gate}</span></div></div>
<div class="card"><div class="label">Comment quality</div><div class="value"><span class="badge {quality_class}">{quality}</span></div></div>
<div class="card"><div class="label">Semantic warnings</div><div class="value">{semantic_count}</div></div>
</div>
<section><h2>{summary_heading}</h2><p><strong>{conclusion_label}:</strong> {conclusion}</p><div class="table-wrap"><table><tbody>
<tr><th>Schema</th><td>{schema}</td><th>Profile</th><td>{profile}</td></tr>
<tr><th>Tables</th><td>{tables}</td><th>Columns</th><td>{columns}</td></tr>
<tr><th>Scan timestamp</th><td colspan="3">{timestamp}</td></tr>
</tbody></table></div></section>
<section><h2>{dimensions_heading}</h2><div class="table-wrap"><table><thead><tr><th>Dimension</th><th>Weight</th><th>Progress</th><th>Score</th></tr></thead><tbody>{dim_rows}</tbody></table></div></section>
<section><h2>{metrics_heading}</h2><div class="table-wrap"><table><thead><tr><th>Metric</th><th>Value</th><th>Status</th></tr></thead><tbody>{metric_rows}</tbody></table></div></section>
<section><h2>{findings_heading}</h2>{findings}</section>
<section><h2>{quality_heading}</h2><p>{quality_summary}</p><div class="table-wrap"><table><thead><tr><th>Object</th><th>Issue</th><th>Current comment</th></tr></thead><tbody>{quality_rows}</tbody></table></div></section>
<section><h2>Semantic type mismatch</h2><p>{semantic_note}</p><div class="table-wrap"><table><thead><tr><th>Column</th><th>DB type</th><th>Inferred</th><th>Evidence</th><th>Recommendation</th></tr></thead><tbody>{semantic_rows}</tbody></table></div></section>
<section><h2>{actions_heading}</h2><ol>{actions}</ol></section>
<section><h2>{sql_heading}</h2><details><summary>{sql_summary}</summary><pre>{sql}</pre></details></section>
{ai_semantics}
</main></body></html>'''.format(
        lang="ja" if lang == "ja" else "en", title=esc(title), css=css, source=esc(source.name), overall=esc(score(overall)),
        gate_class=html_status_class(gate), gate=esc(gate.upper()), quality_class=html_status_class(quality), quality=esc(quality.upper()),
        semantic_count=len(semantic), summary_heading=esc("エグゼクティブサマリー" if lang == "ja" else "Executive summary"),
        conclusion_label=esc("結論" if lang == "ja" else "Conclusion"), conclusion=esc(conclusion), schema=esc(ctx.get("TARGET_OWNER")), profile=esc(data.get("profile")),
        tables=data.get("total_tables", 0), columns=data.get("total_columns", 0), timestamp=esc(ctx.get("SCAN_TIMESTAMP")),
        dimensions_heading=esc("Dimensionスコア" if lang == "ja" else "Dimension scores"), dim_rows="".join(dim_rows),
        metrics_heading=esc("メトリクス詳細" if lang == "ja" else "Metric details"), metric_rows="".join(metric_rows),
        findings_heading=esc("主要な発見事項" if lang == "ja" else "Key findings"), findings=findings_html,
        quality_heading=esc("コメント品質" if lang == "ja" else "Comment quality"),
        quality_summary=esc(("Table {0} / Column {1}" if lang == "ja" else "Table {0} / Column {1}").format(pct(quality_data.get("table_quality_coverage", 0.0)), pct(quality_data.get("column_quality_coverage", 0.0)))),
        quality_rows="".join(quality_rows),
        semantic_note=esc("推定結果のため、自動的な型変更は行いません。" if lang == "ja" else "Heuristic only; no automatic type changes are generated."),
        semantic_rows="".join(semantic_rows), actions_heading=esc("次のアクション" if lang == "ja" else "Next actions"), actions=action_items,
        sql_heading=esc("改善SQL" if lang == "ja" else "Improvement SQL"), sql_summary=esc("SQLを表示" if lang == "ja" else "Show SQL"), sql=esc(sql_text),
        ai_semantics=render_ai_semantics_html(data, lang),
    )
    return html


def main(argv=None):
    parser = argparse.ArgumentParser(description="Score Oracle AI-ready metadata from SQLcl spool output.")
    parser.add_argument("scan_file", help="SQLcl spool output generated by oracle_ai_ready_collect.sql")
    parser.add_argument("--profile", choices=("scan", "rag"), help="override profile detected from run_context")
    parser.add_argument("--language", choices=("ja", "en"), default="ja", help="report language")
    parser.add_argument("--max-sql", type=int, default=200, help="maximum generated COMMENT statements to include")
    parser.add_argument("--max-items", type=int, default=50, help="maximum advisory SQL items per category")
    parser.add_argument("--output", "-o", help="write Markdown report to this file")
    parser.add_argument("--html-output", help="write a self-contained HTML report to this file")
    parser.add_argument("--sql-output", help="write improvement SQL to this file")
    parser.add_argument("--semantics-input", help="optional oracle-ai-semantics-v1 collector JSON (advisory only)")
    args = parser.parse_args(argv)

    path = Path(args.scan_file)
    if not path.exists():
        print("error: scan file not found: {0}".format(path), file=sys.stderr)
        return 2

    try:
        sections = parse_sections(path)
        profile = get_profile(sections.get("run_context", []), args.profile)
        data = calculate(sections, profile)
        semantics = load_semantics(Path(args.semantics_input)) if args.semantics_input else None
        enrich_analysis(sections, data, semantics)
        markdown, sql_text = render_markdown(data, source=path, max_sql=max(0, args.max_sql), max_items=max(0, args.max_items), lang=args.language)
        html_text = render_html(data, source=path, sql_text=sql_text, lang=args.language) if args.html_output else None
    except Exception as exc:
        print("error: {0}".format(exc), file=sys.stderr)
        return 1

    if args.output:
        write_text(Path(args.output), markdown)
    else:
        sys.stdout.write(markdown)

    if args.html_output and html_text is not None:
        write_text(Path(args.html_output), html_text)

    if args.sql_output:
        write_text(Path(args.sql_output), sql_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
