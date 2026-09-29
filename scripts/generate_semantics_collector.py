#!/usr/bin/env python3
"""Generate a read-only SQLcl collector for optional annotation/domain evidence.

This command does not connect to a database. Generate the script locally, review
it, then execute it in an already connected SQLcl session when authorized.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Sequence

from generate_select_ai_setup import sql_literal, validate_identifier


def validate_table_pattern(value: str) -> str:
    """Accept unquoted Oracle names and SQL LIKE wildcards, with explicit escapes."""
    if not re.fullmatch(r"[A-Za-z0-9_$#%\\]{1,256}", value):
        raise ValueError(
            "table-like must contain 1-256 letters, digits, _, $, #, %, or backslashes"
        )
    index = 0
    while index < len(value):
        if value[index] == "\\":
            index += 1
            if index == len(value) or value[index] not in "%_\\":
                raise ValueError("table-like backslash must escape %, _, or a backslash")
        index += 1
    return value.upper()


def validate_spool_filename(value: str) -> str:
    # SQLcl SPOOL is a client command: SQL literal quoting cannot protect it.
    # Restrict it to a filename in SQLcl's working directory, never a command/path.
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,199}", value):
        raise ValueError("spool-file must be a simple ASCII filename without directories")
    if value.upper() in {"OFF", "OUT"}:
        raise ValueError("spool-file must not be the SQLcl SPOOL command OFF or OUT")
    return value


def generate(owner: str, table_like: str = "%", spool_file: str = "oracle_ai_semantics.json") -> str:
    owner = validate_identifier(owner, "owner")
    table_like = validate_table_pattern(table_like)
    spool_file = validate_spool_filename(spool_file)
    template = Path(__file__).with_name("oracle_ai_semantics_collect.sql.in").read_text(encoding="utf-8")
    replacements = {
        "__OWNER__": sql_literal(owner),
        "__TABLE_LIKE__": sql_literal(table_like),
        "__SPOOL_FILE__": spool_file,
    }
    # Match only the original template. Oracle names/patterns may themselves
    # contain marker-looking text, which must never be interpreted recursively.
    return re.sub(r"__OWNER__|__TABLE_LIKE__|__SPOOL_FILE__",
                  lambda match: replacements[match.group(0)], template)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True, help="Unquoted target schema owner")
    parser.add_argument("--table-like", default="%", help="Table LIKE pattern; backslash escapes %% or _")
    parser.add_argument("--output", type=Path, default=Path("collect_ai_semantics.sql"))
    parser.add_argument("--spool-file", default="oracle_ai_semantics.json", help="Evidence filename in SQLcl's working directory")
    args = parser.parse_args(argv)
    try:
        sql = generate(args.owner, args.table_like, args.spool_file)
        args.output.write_text(sql, encoding="utf-8")
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
