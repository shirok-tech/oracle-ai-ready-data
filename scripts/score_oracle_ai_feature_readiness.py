#!/usr/bin/env python3
"""Score Oracle AI feature readiness from SQLcl collector output.

Python 3.6+ compatible. Uses only the standard library.
"""

import argparse
import csv
import io
import os
import re
import sys
from collections import defaultdict

FEATURES = [
    ("select_ai_nl2sql", "Select AI / NL2SQL", 0.25),
    ("select_ai_rag", "Select AI RAG", 0.20),
    ("native_vector", "Oracle AI Vector Search / Vector Index", 0.15),
    ("agent_sql", "Select AI Agent - SQL tool", 0.15),
    ("agent_rag", "Select AI Agent - RAG tool", 0.10),
    ("sdg", "Synthetic Data Generation (SDG)", 0.08),
    ("feedback", "NL2SQL Feedback", 0.04),
    ("auto_object_selection", "Auto Object Selection", 0.03),
]

STATUS_READY = "利用可能そう"
STATUS_SETUP = "対応あり・設定必要"
STATUS_BLOCKED = "機能は見えるが前提不足"
STATUS_MISSING = "現ユーザーから未検出"
STATUS_UNKNOWN = "不明・手動確認"

STATUS_POINTS = {
    STATUS_READY: 1.0,
    STATUS_SETUP: 0.60,
    STATUS_BLOCKED: 0.35,
    STATUS_UNKNOWN: 0.20,
    STATUS_MISSING: 0.0,
}

FEATURE_EXPLANATIONS = {
    "select_ai_nl2sql": "自然言語からSQLを生成・実行・説明するための中核機能です。AI profile、provider、credential、model/endpoint、対象object設定が実利用の鍵です。",
    "select_ai_rag": "LLM回答を企業内データや文書でgroundingする機能です。embedding model、vector index、vector index属性、参照先データ設計が必要です。",
    "native_vector": "VECTOR列、native vector index、Select AI管理のvector indexによりsemantic searchを行う基盤です。RAGやauto object selectionの前提になります。",
    "agent_sql": "DB内でagent/tool/teamを定義し、SQL toolなどを呼び出すワークフロー向け機能です。DBMS_CLOUD_AI_AGENT と Select AI profile が前提です。",
    "agent_rag": "AgentからRAG toolを使うための準備状態です。Agent機能に加えてRAG/vector indexが必要です。",
    "sdg": "スキーマ準拠の合成データを生成する機能です。AI profileと対象schema metadataの品質が重要です。",
    "feedback": "生成SQLへのフィードバックを蓄積し、NL2SQL精度改善に使う機能です。プロシージャ可視性とprofileが前提です。",
    "auto_object_selection": "promptに関連する表メタデータを自動選択する機能です。object_list_mode=automated と vector index support が重要です。",
}


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def parse_sections(text):
    sections = defaultdict(list)
    current = None
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if line.startswith("@@SECTION:"):
            current = line.split(":", 1)[1].strip()
            sections[current] = []
            continue
        if line.startswith("@@END_SECTION"):
            current = None
            continue
        if current is not None:
            # Ignore SQLcl noise that can appear around PL/SQL sections.
            if line.strip() in ("", "PL/SQL procedure successfully completed."):
                continue
            sections[current].append(line)
    return sections


def parse_csv_lines(lines):
    if not lines:
        return []
    data = "\n".join(lines) + "\n"
    try:
        reader = csv.DictReader(io.StringIO(data))
        rows = []
        for row in reader:
            normalized = {}
            for k, v in row.items():
                if k is None:
                    continue
                normalized[str(k).strip().upper()] = "" if v is None else str(v).strip()
            # Drop fully empty rows only when there is no useful probe status.
            if any(v != "" for v in normalized.values()):
                rows.append(normalized)
        return rows
    except Exception:
        return []


def get_rows(sections, name):
    return parse_csv_lines(sections.get(name, []))


def uniq(values):
    seen = []
    for v in values:
        if v and v not in seen:
            seen.append(v)
    return seen


def has_package(rows, package_name):
    p = package_name.upper()
    for r in rows:
        if r.get("OBJECT_NAME", "").upper() == p or r.get("SYNONYM_NAME", "").upper() == p:
            return True
    return False


def procedure_set(rows, package_name):
    p = package_name.upper()
    out = set()
    for r in rows:
        if r.get("OBJECT_NAME", "").upper() == p:
            out.add(r.get("PROCEDURE_NAME", "").upper())
    return out


def nonempty_probe_rows(rows, key):
    return [r for r in rows if r.get("PROBE_STATUS", "").upper() == "OK" and r.get(key, "")]


def probe_errors(rows):
    return [r for r in rows if r.get("PROBE_STATUS", "").upper() == "ERROR"]


def lower_attrs(rows):
    attrs = defaultdict(dict)
    for r in rows:
        if r.get("PROBE_STATUS", "").upper() != "OK":
            continue
        profile = r.get("PROFILE_NAME", "")
        attr = r.get("ATTRIBUTE_NAME", "")
        value = r.get("ATTRIBUTE_VALUE", "")
        if profile and attr:
            attrs[profile][attr.lower()] = value
    return attrs


def any_enabled_profiles(rows):
    out = []
    for r in rows:
        if r.get("PROBE_STATUS", "").upper() == "OK" and r.get("PROFILE_NAME", ""):
            if r.get("STATUS", "").lower() in ("enabled", "enable", "true", "y", ""):
                out.append(r)
    return out


def evaluate(sections):
    run_context = get_rows(sections, "run_context")
    db_version = get_rows(sections, "database_version")
    package_objects = get_rows(sections, "package_objects")
    package_synonyms = get_rows(sections, "package_synonyms")
    package_subprograms = get_rows(sections, "package_subprograms")
    target_vectors = get_rows(sections, "target_vector_columns")
    native_vector_indexes = get_rows(sections, "native_vector_indexes")
    ai_profiles = get_rows(sections, "ai_profiles")
    ai_profile_attrs = get_rows(sections, "ai_profile_attributes")
    cloud_vector_indexes = get_rows(sections, "cloud_vector_indexes")
    cloud_vector_attrs = get_rows(sections, "cloud_vector_index_attributes")
    creds = get_rows(sections, "user_credentials")
    params = get_rows(sections, "database_parameters")

    object_rows = package_objects + package_synonyms
    ai_visible = has_package(object_rows, "DBMS_CLOUD_AI") or bool(procedure_set(package_subprograms, "DBMS_CLOUD_AI"))
    agent_visible = has_package(object_rows, "DBMS_CLOUD_AI_AGENT") or bool(procedure_set(package_subprograms, "DBMS_CLOUD_AI_AGENT"))
    vector_visible = (
        has_package(object_rows, "DBMS_VECTOR")
        or has_package(object_rows, "DBMS_VECTOR_CHAIN")
        or bool(procedure_set(package_subprograms, "DBMS_VECTOR"))
        or bool(procedure_set(package_subprograms, "DBMS_VECTOR_CHAIN"))
        or len(target_vectors) > 0
        or len(native_vector_indexes) > 0
    )

    ai_procs = procedure_set(package_subprograms, "DBMS_CLOUD_AI")
    agent_procs = procedure_set(package_subprograms, "DBMS_CLOUD_AI_AGENT")
    vector_procs = procedure_set(package_subprograms, "DBMS_VECTOR") | procedure_set(package_subprograms, "DBMS_VECTOR_CHAIN")

    enabled_profiles = any_enabled_profiles(ai_profiles)
    profile_attrs = lower_attrs(ai_profile_attrs)
    credentials = nonempty_probe_rows(creds, "CREDENTIAL_NAME")
    cloud_v_indexes = nonempty_probe_rows(cloud_vector_indexes, "INDEX_NAME")
    cloud_v_attrs = [r for r in cloud_vector_attrs if r.get("PROBE_STATUS", "").upper() == "OK" and r.get("INDEX_NAME", "")]

    # Check profile completeness from attributes. Attribute names vary slightly by release/provider, so use tolerant matching.
    profile_has_provider = False
    profile_has_credential = False
    profile_has_model = False
    profile_has_object_list = False
    profile_has_embedding = False
    profile_has_vector_index = False
    profile_auto_object = False
    for profile, attrs in profile_attrs.items():
        keys = set(attrs.keys())
        if "provider" in keys:
            profile_has_provider = True
        if "credential_name" in keys or "credential" in keys:
            profile_has_credential = True
        if "model" in keys or "model_name" in keys or "endpoint" in keys or "model_endpoint" in keys:
            profile_has_model = True
        if "object_list" in keys or "object_list_mode" in keys:
            profile_has_object_list = True
        if "embedding_model" in keys or "embedding_model_name" in keys:
            profile_has_embedding = True
        if "vector_index_name" in keys:
            profile_has_vector_index = True
        if attrs.get("object_list_mode", "").lower() == "automated":
            profile_auto_object = True

    profile_ready = bool(enabled_profiles and profile_has_provider and profile_has_credential and profile_has_model)
    profile_config_started = bool(enabled_profiles or profile_attrs or credentials)
    create_vector_index_visible = "CREATE_VECTOR_INDEX" in ai_procs
    rag_config_ready = bool(create_vector_index_visible and cloud_v_indexes and profile_has_embedding and profile_has_vector_index)
    rag_config_started = bool(create_vector_index_visible or cloud_v_indexes or profile_has_embedding or profile_has_vector_index)
    native_vector_configured = bool(target_vectors or native_vector_indexes)

    features = {}

    if not ai_visible:
        features["select_ai_nl2sql"] = (STATUS_MISSING, "DBMS_CLOUD_AI was not visible to the current user.", "Confirm environment support and package privileges. In OCI Base Database Service, Select AI packages may not be present even when native vector packages are present.")
    elif profile_ready:
        features["select_ai_nl2sql"] = (STATUS_READY, "DBMS_CLOUD_AI core procedures and an enabled profile with provider/credential/model evidence were detected.", "Run SELECT AI showsql first, then runsql after review.")
    else:
        evidence = "DBMS_CLOUD_AI core procedures visible; enabled profiles: %d; credentials visible: %d" % (len(enabled_profiles), len(credentials))
        features["select_ai_nl2sql"] = (STATUS_SETUP, evidence, "Create or fix an enabled AI profile with provider, credential, model/endpoint, comments, constraints, and target object settings.")

    if not create_vector_index_visible:
        features["select_ai_rag"] = (STATUS_MISSING, "CREATE_VECTOR_INDEX was not visible through DBMS_CLOUD_AI.", "Use a Select AI RAG capable environment or check DBMS_CLOUD_AI privileges.")
    elif rag_config_ready:
        features["select_ai_rag"] = (STATUS_READY, "CREATE_VECTOR_INDEX visible and profile/vector index configuration evidence was detected.", "Run a small RAG query and validate sources/chunks before production use.")
    else:
        features["select_ai_rag"] = (STATUS_SETUP, "CREATE_VECTOR_INDEX visible, but no complete RAG profile/index configuration detected.", "Create an embedding-enabled profile, create/enable a vector index, and set vector_index_name on the profile.")

    if native_vector_configured:
        features["native_vector"] = (STATUS_READY, "VECTOR columns or native vector indexes were detected in the target scope.", "Run a vector-distance smoke test and review index accuracy/performance.")
    elif vector_visible or create_vector_index_visible:
        features["native_vector"] = (STATUS_SETUP, "Vector-related package/procedure visible, but no configured vector index/column detected in scope.", "Create a VECTOR column/table or vector index, or document an external vector store design.")
    else:
        features["native_vector"] = (STATUS_MISSING, "No vector package, VECTOR column, or vector index evidence was detected.", "Use a vector-capable release/environment or configure an external vector store.")

    if not agent_visible:
        features["agent_sql"] = (STATUS_MISSING, "DBMS_CLOUD_AI_AGENT was not visible to the current user.", "Confirm agent support and package privileges.")
    elif features["select_ai_nl2sql"][0] == STATUS_READY:
        features["agent_sql"] = (STATUS_READY, "DBMS_CLOUD_AI_AGENT procedures visible and NL2SQL profile readiness looks complete.", "Start with a least-privilege SQL tool and audit logging.")
    else:
        features["agent_sql"] = (STATUS_SETUP, "DBMS_CLOUD_AI_AGENT procedures visible, but NL2SQL profile readiness is incomplete.", "Complete Select AI profile setup before agent SQL tool rollout.")

    if not agent_visible:
        features["agent_rag"] = (STATUS_MISSING, "Agent package support was not visible.", "Confirm DBMS_CLOUD_AI_AGENT availability and privileges.")
    elif features["select_ai_rag"][0] == STATUS_READY:
        features["agent_rag"] = (STATUS_READY, "Agent and complete RAG/vector index evidence were detected.", "Create a narrowly scoped RAG tool and validate source attribution.")
    else:
        features["agent_rag"] = (STATUS_SETUP, "Agent and RAG packages visible, but complete RAG profile/index configuration was not detected.", "Complete RAG configuration before enabling agent RAG tools.")

    if "GENERATE_SYNTHETIC_DATA" not in ai_procs and "GENERATE_SYNTHETIC_DATA_ONCE" not in ai_procs:
        features["sdg"] = (STATUS_MISSING, "GENERATE_SYNTHETIC_DATA was not visible.", "Confirm release support and DBMS_CLOUD_AI privileges.")
    elif profile_ready:
        features["sdg"] = (STATUS_READY, "Synthetic data procedures and a usable profile were detected.", "Use a non-production schema and review constraints/sensitive columns.")
    else:
        features["sdg"] = (STATUS_SETUP, "GENERATE_SYNTHETIC_DATA visible, but no complete enabled AI profile was detected.", "Complete AI profile setup and review target schema constraints/comments.")

    if "FEEDBACK" not in ai_procs:
        features["feedback"] = (STATUS_MISSING, "FEEDBACK procedure was not visible.", "Confirm release support and privileges.")
    elif profile_ready:
        features["feedback"] = (STATUS_READY, "FEEDBACK visible and AI profile readiness looks complete.", "Collect feedback only after reviewing generated SQL quality.")
    else:
        features["feedback"] = (STATUS_SETUP, "FEEDBACK visible, but AI profile setup is incomplete.", "Complete profile setup before collecting feedback.")

    if profile_auto_object and create_vector_index_visible:
        features["auto_object_selection"] = (STATUS_READY, "A profile with object_list_mode=automated and vector index support was detected.", "Validate object selection on representative prompts.")
    elif create_vector_index_visible:
        features["auto_object_selection"] = (STATUS_SETUP, "Vector index support visible, but no profile with object_list_mode=automated detected.", "Set object_list_mode=automated on an appropriate profile if auto object selection is desired.")
    else:
        features["auto_object_selection"] = (STATUS_MISSING, "Auto object selection requires vector-index support, which was not visible.", "Use manual object_list or check Select AI vector index support.")

    score = 0.0
    for key, _name, weight in FEATURES:
        status = features[key][0]
        score += weight * STATUS_POINTS.get(status, 0.0)
    # Add a small collector-success floor so a valid negative result is distinct from a parse failure.
    if run_context:
        score = max(score, 0.10)
    score = min(score, 1.0)

    if any(features[k][0] == STATUS_READY for k, _n, _w in FEATURES):
        conclusion = "一部機能は利用可能そうです。残りは設定または手動確認が必要です。"
    elif any(features[k][0] == STATUS_SETUP for k, _n, _w in FEATURES):
        conclusion = "AI機能は見えていますが、profile/credential/vector index などの設定が必要です。"
    elif any(features[k][0] == STATUS_BLOCKED for k, _n, _w in FEATURES):
        conclusion = "機能の一部は見えますが、前提設定不足で利用判断は保留です。"
    else:
        conclusion = "現ユーザーからは主要AI機能を十分確認できません。"

    return {
        "sections": sections,
        "run_context": run_context,
        "db_version": db_version,
        "package_objects": package_objects,
        "package_subprograms": package_subprograms,
        "target_vectors": target_vectors,
        "native_vector_indexes": native_vector_indexes,
        "ai_profiles": ai_profiles,
        "ai_profile_attrs": ai_profile_attrs,
        "cloud_vector_indexes": cloud_vector_indexes,
        "cloud_vector_attrs": cloud_vector_attrs,
        "credentials": creds,
        "params": params,
        "ai_visible": ai_visible,
        "agent_visible": agent_visible,
        "vector_visible": vector_visible,
        "ai_procs": ai_procs,
        "agent_procs": agent_procs,
        "vector_procs": vector_procs,
        "enabled_profiles": enabled_profiles,
        "credentials_nonempty": credentials,
        "cloud_v_indexes": cloud_v_indexes,
        "cloud_v_attrs": cloud_v_attrs,
        "features": features,
        "score": score,
        "conclusion": conclusion,
        "probe_errors": {
            "ai_profiles": probe_errors(ai_profiles),
            "ai_profile_attributes": probe_errors(ai_profile_attrs),
            "cloud_vector_indexes": probe_errors(cloud_vector_indexes),
            "cloud_vector_index_attributes": probe_errors(cloud_vector_attrs),
            "user_credentials": probe_errors(creds),
            "database_parameters": probe_errors(params),
        },
    }


def first(rowlist, key, default=""):
    if not rowlist:
        return default
    return rowlist[0].get(key, default)


def md_escape(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def join_or_none(items, none="none", limit=40):
    vals = uniq([str(x) for x in items if x])
    if not vals:
        return none
    if len(vals) > limit:
        return ", ".join(vals[:limit]) + ", ..."
    return ", ".join(vals)


def make_report(result, input_file):
    rc = result["run_context"]
    dbv = result["db_version"]
    features = result["features"]
    ready = [name for key, name, _w in FEATURES if features[key][0] == STATUS_READY]
    setup = [name for key, name, _w in FEATURES if features[key][0] == STATUS_SETUP]
    missing = [name for key, name, _w in FEATURES if features[key][0] == STATUS_MISSING]

    db_version_text = " ".join([first(dbv, "PRODUCT"), first(dbv, "VERSION_FULL") or first(dbv, "VERSION"), first(dbv, "STATUS")]).strip()
    target_schema = first(rc, "TARGET_OWNER", "unknown")
    table_pattern = first(rc, "TABLE_LIKE_PATTERN", "unknown")

    lines = []
    lines.append("# Oracle AI Feature Readiness 評価レポート")
    lines.append("")
    lines.append("## 1. エグゼクティブサマリー")
    lines.append("- Feature readiness score: **%.2f / 1.00**" % result["score"])
    lines.append("- 結論: **%s**" % result["conclusion"])
    lines.append("- AI機能の存在: **%s**" % ("あり" if (result["ai_visible"] or result["agent_visible"] or result["vector_visible"]) else "現ユーザーからは未確認"))
    lines.append("- すぐ利用できそうな機能: **%s**" % (join_or_none(ready, "なし")))
    lines.append("- 対応はありそうだが設定が必要な機能: **%s**" % (join_or_none(setup, "なし")))
    lines.append("- 現ユーザーから未検出の機能: **%s**" % (join_or_none(missing, "なし")))
    lines.append("- 注意: 未検出は、未サポートだけでなく、権限不足、別スキーマ所有、PDBで未展開、または接続ユーザーの可視範囲不足の可能性があります。")
    lines.append("")
    lines.append("## 2. スコープと環境")
    lines.append("| 項目 | 値 |")
    lines.append("|---|---|")
    lines.append("| Target schema | %s |" % md_escape(target_schema))
    lines.append("| Table pattern | %s |" % md_escape(table_pattern))
    lines.append("| Session user | %s |" % md_escape(first(rc, "SESSION_USER", "")))
    lines.append("| Current schema | %s |" % md_escape(first(rc, "CURRENT_SCHEMA", "")))
    lines.append("| DB / PDB | %s / %s |" % (md_escape(first(rc, "DB_NAME", "")), md_escape(first(rc, "CON_NAME", ""))))
    lines.append("| Database version evidence | %s |" % md_escape(db_version_text))
    compats = [r.get("VALUE", "") for r in result["params"] if r.get("NAME", "") == "compatible"]
    if compats:
        lines.append("| compatible parameter | %s |" % md_escape(compats[0]))
    lines.append("| SQLcl spool | %s |" % md_escape(os.path.basename(input_file)))
    lines.append("| Scan timestamp | %s |" % md_escape(first(rc, "SCAN_TIMESTAMP", "")))
    lines.append("")

    lines.append("## 3. 機能別判定")
    lines.append("| Feature | Status | 何を評価しているか | 主な根拠 | 次のアクション |")
    lines.append("|---|---|---|---|---|")
    for key, name, _w in FEATURES:
        status, evidence, action = features[key]
        lines.append("| %s | %s | %s | %s | %s |" % (md_escape(name), md_escape(status), md_escape(FEATURE_EXPLANATIONS[key]), md_escape(evidence), md_escape(action)))
    lines.append("")

    lines.append("## 4. パッケージ / プロシージャ証跡")
    lines.append("| 項目 | 検出内容 |")
    lines.append("|---|---|")
    lines.append("| DBMS_CLOUD_AI visible | %s |" % ("yes" if result["ai_visible"] else "no"))
    lines.append("| DBMS_CLOUD_AI procedures | %s |" % md_escape(join_or_none(sorted(result["ai_procs"]), "none", 80)))
    lines.append("| DBMS_CLOUD_AI_AGENT visible | %s |" % ("yes" if result["agent_visible"] else "no"))
    lines.append("| DBMS_CLOUD_AI_AGENT procedures | %s |" % md_escape(join_or_none(sorted(result["agent_procs"]), "none", 80)))
    lines.append("| DBMS_VECTOR / DBMS_VECTOR_CHAIN visible | %s |" % ("yes" if result["vector_visible"] else "no"))
    lines.append("| Vector procedures | %s |" % md_escape(join_or_none(sorted(result["vector_procs"]), "none", 80)))
    lines.append("")

    lines.append("## 5. AI Profile 検出結果")
    profile_rows = nonempty_probe_rows(result["ai_profiles"], "PROFILE_NAME")
    if profile_rows:
        lines.append("| Profile | Status | Description |")
        lines.append("|---|---|---|")
        for r in profile_rows:
            lines.append("| %s | %s | %s |" % (md_escape(r.get("PROFILE_NAME", "")), md_escape(r.get("STATUS", "")), md_escape(r.get("DESCRIPTION", ""))))
    else:
        lines.append("AI profile は検出されませんでした。`USER_CLOUD_AI_PROFILES` が未サポート/権限不足、または profile 未作成の可能性があります。")
    lines.append("")

    lines.append("## 6. Vector / RAG 検出結果")
    lines.append("| 項目 | 件数 | 説明 |")
    lines.append("|---|---:|---|")
    lines.append("| USER_CLOUD_VECTOR_INDEXES | %d | Select AI が管理する vector index の可視件数です。 |" % len(result["cloud_v_indexes"]))
    lines.append("| USER_CLOUD_VECTOR_INDEX_ATTRIBUTES | %d | vector index の属性数です。chunk、location、refreshなどの確認に使います。 |" % len(result["cloud_v_attrs"]))
    lines.append("| Target VECTOR columns | %d | 対象スキーマ内の VECTOR 型カラム数です。 |" % len(result["target_vectors"]))
    lines.append("| Native vector-like indexes | %d | 対象スキーマ内の vector 関連 index 候補です。 |" % len(result["native_vector_indexes"]))
    lines.append("")

    lines.append("## 7. 主要ギャップ")
    gaps = []
    if not result["ai_visible"]:
        gaps.append("DBMS_CLOUD_AI が現ユーザーから見えません。Select AI / NL2SQL / RAG / SDG の利用可否を、このユーザーでは判断できません。")
    elif not result["enabled_profiles"]:
        gaps.append("利用可能そうな NL2SQL 用 AI profile がありません。provider、credential_name、model/endpoint を持つ enabled profile が必要です。")
    if features["select_ai_rag"][0] != STATUS_READY:
        gaps.append("RAG はまだ利用可能とは判定できません。embedding_model、vector_index_name、有効な vector index を確認してください。")
    if features["agent_sql"][0] != STATUS_READY:
        gaps.append("Agent SQL tool は未完了です。DBMS_CLOUD_AI_AGENT と Select AI profile の両方を確認してください。")
    if features["sdg"][0] != STATUS_READY:
        gaps.append("SDG は未完了です。GENERATE_SYNTHETIC_DATA の可視性と AI profile を確認してください。")
    for section_name, errors in result["probe_errors"].items():
        for e in errors:
            gaps.append("%s のprobeでエラー: %s %s" % (section_name, e.get("ERROR_CODE", ""), e.get("ERROR_MESSAGE", "")))
    if not gaps:
        gaps.append("自動検出された主要ギャップはありません。実プロンプトで機能テストを行ってください。")
    for g in gaps:
        lines.append("- %s" % g)
    lines.append("")

    lines.append("## 8. セットアップ SQL テンプレート")
    lines.append("以下はレビュー用テンプレートです。Credential、provider、model、object storage、権限は環境に合わせて置換してください。")
    lines.append("")
    lines.append("```sql")
    lines.append(make_setup_sql(result).rstrip())
    lines.append("```")
    lines.append("")

    lines.append("## 9. 次のアクション")
    if result["ai_visible"]:
        lines.append("1. Select AI profile と credential を優先して整備する。")
        lines.append("2. まず `SELECT AI showsql ...` で NL2SQL を検証し、`runsql` は生成SQLレビュー後に使う。")
        lines.append("3. RAG を使う場合は、embedding model、vector index、source location、chunking、refresh_rate を決める。")
        lines.append("4. Agent を使う場合は、まず SQL tool を最小権限で試し、RAG tool は vector index 確認後に進める。")
    elif result["vector_visible"]:
        lines.append("1. Base Database Service など Select AI が見えない環境では、Native Vector Search の smoke test を先に行う。")
        lines.append("2. RAG はアプリケーション側で embedding/LLM を呼び、Oracle Database を vector store として使う構成を検討する。")
        lines.append("3. Select AI が必要な場合は、DBMS_CLOUD_AI が提供される Autonomous AI Database などで検証する。")
    else:
        lines.append("1. DBA/SYSDBA または環境管理者で DBMS_CLOUD_AI / DBMS_VECTOR の存在と権限を確認する。")
        lines.append("2. Select AI / RAG が必要な場合は、対応環境またはサービス種別を確認する。")
    return "\n".join(lines) + "\n"


def make_setup_sql(result):
    parts = []
    ai_visible = result["ai_visible"]
    vector_visible = result["vector_visible"]
    target = first(result["run_context"], "TARGET_OWNER", "TARGET_SCHEMA")
    if ai_visible:
        parts.append("""-- Template: create a Select AI profile for NL2SQL
-- Reason: Select AI / NL2SQL を使うには、有効な AI profile、provider、credential、model、対象object設定が必要です。
-- Purpose: 自然言語SQL生成を、対象スキーマに限定して安全に試せる状態にします。
-- Review: provider/model/credential/object_list は環境に合わせて置換し、credential は事前作成してください。
BEGIN
  DBMS_CLOUD_AI.CREATE_PROFILE(
    profile_name => 'AI_READY_NL2SQL',
    status       => 'enabled',
    description  => 'AI Ready NL2SQL profile scoped for review',
    attributes   => JSON_OBJECT(
      'provider'        VALUE 'oci',
      'credential_name' VALUE 'TODO_AI_PROVIDER_CRED',
      'model'           VALUE 'TODO_MODEL_NAME',
      'object_list'     VALUE JSON_ARRAY(JSON_OBJECT('owner' VALUE '%s')),
      'comments'        VALUE true,
      'constraints'     VALUE true,
      'enforce_object_list' VALUE true
    )
  );
END;
/""" % target)
        if "CREATE_VECTOR_INDEX" in result["ai_procs"]:
            parts.append("""-- Template: create a Select AI vector index for RAG
-- Reason: RAG を使うには、embedding model と vector index が必要です。
-- Purpose: Object Storage や directory object から文書を取り込み、RAG の検索根拠を構成します。
-- Review: location、object_storage_credential_name、chunk_size、refresh_rate、dimension は設計レビュー後に決めてください。
BEGIN
  DBMS_CLOUD_AI.CREATE_VECTOR_INDEX(
    index_name => 'AI_READY_RAG_INDEX',
    status     => 'enabled',
    wait_for_completion => false,
    description => 'AI Ready RAG vector index for review',
    attributes => JSON_OBJECT(
      'vector_db_provider' VALUE 'oracle',
      'vector_table_name'  VALUE 'AI_READY_RAG_VECTOR_TABLE',
      'profile_name'       VALUE 'AI_READY_NL2SQL',
      'location'           VALUE 'TODO_OBJECT_STORAGE_OR_DIRECTORY_LOCATION',
      'object_storage_credential_name' VALUE 'TODO_OBJECT_STORAGE_CRED',
      'chunk_size'         VALUE 1024,
      'chunk_overlap'      VALUE 128,
      'refresh_rate'       VALUE 720
    )
  );
END;
/""")
            parts.append("""-- Template: attach RAG settings to the AI profile
-- Reason: AI profile に embedding_model と vector_index_name がないと、Select AI RAG の利用準備が完了しません。
-- Purpose: 既存 profile から RAG vector index を参照できるようにします。
-- Review: embedding model は provider が対応するものを選び、index 作成完了後に設定してください。
BEGIN
  DBMS_CLOUD_AI.SET_ATTRIBUTE('AI_READY_NL2SQL', 'embedding_model', 'TODO_EMBEDDING_MODEL');
  DBMS_CLOUD_AI.SET_ATTRIBUTE('AI_READY_NL2SQL', 'vector_index_name', 'AI_READY_RAG_INDEX');
  DBMS_CLOUD_AI.SET_ATTRIBUTE('AI_READY_NL2SQL', 'enable_sources', 'true');
END;
/""")
            parts.append("""-- Template: enable auto object selection for NL2SQL
-- Reason: 大きいスキーマでは object_list を手動で絞るより、自動object選択が有効な場合があります。
-- Purpose: promptに関連するメタデータだけをLLMへ渡す設計に近づけます。
-- Review: vector index support が必要です。対象外オブジェクトが選ばれないかPoCで確認してください。
BEGIN
  DBMS_CLOUD_AI.SET_ATTRIBUTE('AI_READY_NL2SQL', 'object_list_mode', 'automated');
END;
/""")
        if result["agent_visible"]:
            parts.append("""-- Template only: agent setup placeholder
-- Reason: Agent は実行可能なtoolを持つため、最小権限と監査設計が必要です。
-- Purpose: SQL tool / RAG tool を作る前に、profile、権限、ログ、実行範囲を明確にします。
-- Review: DBMS_CLOUD_AI_AGENT の実際の引数は利用releaseのドキュメントに合わせ、いきなり本番実行しないでください。
-- BEGIN
--   DBMS_CLOUD_AI_AGENT.CREATE_AGENT(...);
--   DBMS_CLOUD_AI_AGENT.CREATE_TOOL(...);
--   DBMS_CLOUD_AI_AGENT.CREATE_TEAM(...);
-- END;
-- /""")
    else:
        parts.append("""-- Select AI setup is blocked in the current environment.
-- Reason: DBMS_CLOUD_AI was not visible to the current user, so CREATE_PROFILE / SELECT AI templates would fail.
-- Purpose: Avoid generating unusable DBMS_CLOUD_AI SQL for OCI Base Database Service or non-Select-AI environments.
-- Review: Confirm whether this service/PDB provides DBMS_CLOUD_AI, or use an Autonomous AI Database / Select AI-enabled environment.""")

    if vector_visible and not ai_visible:
        parts.append("""-- Native Vector Search smoke test template
-- Reason: DBMS_VECTOR or DBMS_VECTOR_CHAIN is visible, even though Select AI is not.
-- Purpose: Confirm that VECTOR data type and VECTOR_DISTANCE work in this PDB.
-- Review: Run in a scratch schema only.
CREATE TABLE ai_vector_probe (
  id NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  text_value VARCHAR2(200),
  embedding VECTOR(3, FLOAT32)
);

INSERT INTO ai_vector_probe (text_value, embedding) VALUES ('apple', '[1.0, 0.0, 0.0]');
INSERT INTO ai_vector_probe (text_value, embedding) VALUES ('banana', '[0.9, 0.1, 0.0]');
INSERT INTO ai_vector_probe (text_value, embedding) VALUES ('car', '[0.0, 1.0, 0.0]');
COMMIT;

SELECT id,
       text_value,
       VECTOR_DISTANCE(embedding, TO_VECTOR('[1.0, 0.0, 0.0]'), COSINE) AS distance
FROM ai_vector_probe
ORDER BY distance
FETCH FIRST 3 ROWS ONLY;

DROP TABLE ai_vector_probe PURGE;""")
    return "\n\n".join(parts) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Score Oracle AI feature readiness from SQLcl output.")
    parser.add_argument("input", help="SQLcl feature readiness .out file")
    parser.add_argument("--language", default="ja", choices=["ja", "en"], help="Report language. ja is currently the primary template.")
    parser.add_argument("--output", default="oracle_ai_feature_readiness.md", help="Markdown report path")
    parser.add_argument("--sql-output", default="oracle_ai_feature_setup.sql", help="Setup SQL template path")
    args = parser.parse_args(argv)

    text = read_text(args.input)
    sections = parse_sections(text)
    result = evaluate(sections)
    report = make_report(result, args.input)
    setup_sql = make_setup_sql(result)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)
    with open(args.sql_output, "w", encoding="utf-8") as f:
        f.write(setup_sql)
    print("Wrote %s" % args.output)
    print("Wrote %s" % args.sql_output)
    print("Feature readiness score: %.2f" % result["score"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
