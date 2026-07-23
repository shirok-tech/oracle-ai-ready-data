
#!/usr/bin/env python3
"""Validate row counts, PK candidates, FK candidates, and SQL coverage."""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'

EXPECTED_ROWS = {
    'raw_customers.csv':50,'raw_orders.csv':100,'raw_order_lines.csv':200,
    'ai_documents.csv':12,'customer_features.csv':50,'support_tickets.csv':30,
    'orphan_regions.csv':6,'empty_export.csv':0,
}

def read(name):
    with (DATA/name).open('r',encoding='utf-8',newline='') as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == EXPECTED_ROWS[name], (name,len(rows),EXPECTED_ROWS[name])
    return rows

def duplicate_count(values):
    return sum(1 for count in Counter(values).values() if count > 1)

c = read('raw_customers.csv')
o = read('raw_orders.csv')
l = read('raw_order_lines.csv')
d = read('ai_documents.csv')
f = read('customer_features.csv')
t = read('support_tickets.csv')
r = read('orphan_regions.csv')
read('empty_export.csv')

customer_ids = [row['CUSTOMER_ID'] for row in c]
order_ids = [row['ORDER_ID'] for row in o]
line_keys = [(row['ORDER_ID'],row['LINE_NO']) for row in l]
doc_keys = [(row['DOC_ID'],row['CHUNK_NUMBER']) for row in d]
feature_ids = [row['CUSTOMER_ID'] for row in f]
ticket_ids = [row['TICKET_ID'] for row in t]
region_codes = [row['COUNTRY_CODE'] for row in r]

checks = {
    'total_rows':sum(EXPECTED_ROWS.values()) == 448,
    'customer_pk':all(customer_ids) and duplicate_count(customer_ids) == 0,
    'order_pk':all(order_ids) and duplicate_count(order_ids) == 0,
    'line_pk':all(a and b for a,b in line_keys) and duplicate_count(line_keys) == 0,
    'document_pk':all(a and b for a,b in doc_keys) and duplicate_count(doc_keys) == 0,
    'feature_pk':all(feature_ids) and duplicate_count(feature_ids) == 0,
    'ticket_pk':all(ticket_ids) and duplicate_count(ticket_ids) == 0,
    'region_pk':all(region_codes) and duplicate_count(region_codes) == 0,
    'customer_region_fk':all(row['COUNTRY_CODE'] in set(region_codes) for row in c),
    'order_customer_fk':all(row['CUSTOMER_ID'] in set(customer_ids) for row in o),
    'line_order_fk':all(row['ORDER_ID'] in set(order_ids) for row in l),
    'feature_customer_fk':all(row['CUSTOMER_ID'] in set(customer_ids) for row in f),
    'ticket_customer_fk':all(row['CUSTOMER_ID'] in set(customer_ids) for row in t),
    'order_amount_format':all(re.fullmatch(r'[0-9]+[.][0-9]{2}',row['AMOUNT_TXT']) for row in o),
    'order_date_format':all(re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',row['ORDER_TIME_TXT']) for row in o),
}

sql = (ROOT/'07_apply_ai_ready_improvements.sql').read_text(encoding='utf-8')
checks['no_todo_in_improvement_sql'] = 'TODO' not in sql.upper()
checks['table_comment_count'] = len(re.findall(r'^COMMENT ON TABLE ',sql,re.M)) == 8
checks['column_comment_count'] = len(re.findall(r'^COMMENT ON COLUMN ',sql,re.M)) == 68
checks['pk_ddl_count'] = len(re.findall(r"add_constraint_if_missing\('PK_",sql)) == 8
checks['fk_ddl_count'] = len(re.findall(r"add_constraint_if_missing\('FK_",sql)) == 5

failures = []
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'} {name}")
    if not ok:
        failures.append(name)
if failures:
    print('Validation failed: ' + ', '.join(failures), file=sys.stderr)
    raise SystemExit(1)
print('All package checks passed.')
