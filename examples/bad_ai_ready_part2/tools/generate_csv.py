
#!/usr/bin/env python3
"""Regenerate deterministic, PK/FK-ready CSV data for BAD_AI_READY Part 2."""

from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DATA.mkdir(parents=True, exist_ok=True)

COLUMNS = {
    'raw_customers.csv': ['CUSTOMER_ID','FULL_NAME','EMAIL','PHONE','SSN','BIRTHDATE_TXT','COUNTRY_CODE','SIGNUP_WHEN_TXT','STATUS_TXT','LAST_PURCHASE_AMT','NOTES'],
    'raw_orders.csv': ['ORDER_ID','CUSTOMER_ID','ORDER_TIME_TXT','AMOUNT_TXT','CURRENCY_CODE','SHIPPING_POSTAL_CODE','PAYMENT_CARD_HINT','ORDER_PAYLOAD'],
    'raw_order_lines.csv': ['ORDER_ID','LINE_NO','SKU','QUANTITY_TXT','UNIT_PRICE_TXT','DISCOUNT_TXT','LINE_COMMENT'],
    'ai_documents.csv': ['DOC_ID','ORIGIN_URI','TITLE_TXT','BODY_TEXT','CHUNK_NUMBER','EMBEDDING_BLOB_TXT','LIFECYCLE_STATE'],
    'customer_features.csv': ['CUSTOMER_ID','CHURN_SCORE_TXT','LIFETIME_VALUE_TXT','SEGMENT_CODE','FEATURE_NOTES'],
    'support_tickets.csv': ['TICKET_ID','CUSTOMER_ID','SEVERITY_TXT','AGENT_EMAIL','REQUESTER_PHONE','TICKET_STATUS','PROBLEM_DESCRIPTION','RESOLUTION_TEXT'],
    'orphan_regions.csv': ['COUNTRY_CODE','REGION_NAME','RISK_TIER_TXT'],
    'empty_export.csv': ['EXPORT_ID','EXPORT_NAME','PAYLOAD'],
}

def write_csv(name: str, rows: Iterable[Dict[str, Any]]) -> int:
    rows = list(rows)
    with (DATA / name).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS[name], lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: '' if v is None else v for k, v in row.items()})
    return len(rows)

def line_values(order_no: int, line_no: int):
    if line_no == 1:
        quantity = 1 + order_no % 3
        unit_price = 12.00 + order_no % 17 * 1.25
        discount = 5 if order_no % 4 == 0 else 0
    else:
        quantity = 1 + order_no % 2
        unit_price = 7.50 + order_no % 11 * 0.95
        discount = 10 if order_no % 6 == 0 else 0
    return quantity, unit_price, discount, f'SKU-{((order_no - 1) * 2 + line_no):04d}'

regions = [
    {'COUNTRY_CODE':'JP','REGION_NAME':'Japan','RISK_TIER_TXT':'MEDIUM'},
    {'COUNTRY_CODE':'US','REGION_NAME':'United States','RISK_TIER_TXT':'LOW'},
    {'COUNTRY_CODE':'GB','REGION_NAME':'United Kingdom','RISK_TIER_TXT':'LOW'},
    {'COUNTRY_CODE':'DE','REGION_NAME':'Germany','RISK_TIER_TXT':'LOW'},
    {'COUNTRY_CODE':'SG','REGION_NAME':'Singapore','RISK_TIER_TXT':'MEDIUM'},
    {'COUNTRY_CODE':'AU','REGION_NAME':'Australia','RISK_TIER_TXT':'LOW'},
]
countries = [r['COUNTRY_CODE'] for r in regions]
customers = []
for i in range(1, 51):
    birth = date(1972,1,1) + timedelta(days=(i*173) % 14000)
    signup = date(2022,1,1) + timedelta(days=i*19)
    status = 'SUSPENDED' if i % 13 == 0 else ('INACTIVE' if i % 7 == 0 else 'ACTIVE')
    customers.append({
        'CUSTOMER_ID':i,'FULL_NAME':f'Demo Customer {i:03d}','EMAIL':f'customer{i:03d}@example.invalid',
        'PHONE':f'+81-50-{1000+i:04d}-{2000+i:04d}','SSN':f'999-{(10+i)%100:02d}-{1000+i:04d}',
        'BIRTHDATE_TXT':birth.isoformat(),'COUNTRY_CODE':countries[(i-1)%len(countries)],
        'SIGNUP_WHEN_TXT':f'{signup.isoformat()} 09:00:00','STATUS_TXT':status,
        'LAST_PURCHASE_AMT':f'{125.00+i*23.75:.2f}',
        'NOTES':'Synthetic customer record for the AI Ready metadata demonstration. All contact values are artificial.'
    })
currency = {'JP':'JPY','US':'USD','GB':'GBP','DE':'EUR','SG':'SGD','AU':'AUD'}
customer_country = {r['CUSTOMER_ID']:r['COUNTRY_CODE'] for r in customers}
orders = []
lines = []
for i in range(1, 101):
    total = 0.0
    for line_no in (1,2):
        qty, price, disc, sku = line_values(i,line_no)
        total += qty*price*(1-disc/100)
        lines.append({'ORDER_ID':f'ORD-{i:04d}','LINE_NO':line_no,'SKU':sku,'QUANTITY_TXT':str(qty),
                      'UNIT_PRICE_TXT':f'{price:.2f}','DISCOUNT_TXT':str(disc),
                      'LINE_COMMENT':'Primary item' if line_no == 1 else 'Accessory item'})
    cid = (i-1)%50+1
    orders.append({'ORDER_ID':f'ORD-{i:04d}','CUSTOMER_ID':cid,
                   'ORDER_TIME_TXT':(date(2025,1,1)+timedelta(days=i*3)).isoformat(),
                   'AMOUNT_TXT':f'{total:.2f}','CURRENCY_CODE':currency[customer_country[cid]],
                   'SHIPPING_POSTAL_CODE':f'{100+(i%800):03d}-{1000+i:04d}',
                   'PAYMENT_CARD_HINT':f'****-****-****-{1000+i:04d}',
                   'ORDER_PAYLOAD':json.dumps({'channel':'WEB' if i%2 else 'STORE','priority':'STANDARD','demo':True},separators=(',',':'))})
features = [{'CUSTOMER_ID':i,'CHURN_SCORE_TXT':f'{((i*13)%100)/100:.2f}',
             'LIFETIME_VALUE_TXT':f'{500+i*73.25:.2f}','SEGMENT_CODE':f'S{((i-1)%4)+1}',
             'FEATURE_NOTES':'Deterministic synthetic feature row for demonstration.'} for i in range(1,51)]
statuses = ['OPEN','IN_PROGRESS','RESOLVED','CLOSED']
tickets = []
for i in range(1,31):
    status = statuses[(i-1)%4]
    tickets.append({'TICKET_ID':f'T-{i:04d}','CUSTOMER_ID':((i*7-1)%50)+1,
                    'SEVERITY_TXT':str(((i-1)%5)+1),'AGENT_EMAIL':f'agent{((i-1)%6)+1}@example.invalid',
                    'REQUESTER_PHONE':f'+81-70-{3000+i:04d}-{4000+i:04d}','TICKET_STATUS':status,
                    'PROBLEM_DESCRIPTION':f'Synthetic support request {i:04d}. The user reports a repeatable login or order-status issue.',
                    'RESOLUTION_TEXT':None if status in {'OPEN','IN_PROGRESS'} else 'Issue resolved using the documented standard procedure.'})
topics = ['Account access','Order status','Refund policy','Shipping guidance','Security review','Support escalation']
docs = []
for doc_id, topic in enumerate(topics,1):
    for chunk in (1,2):
        docs.append({'DOC_ID':doc_id,'ORIGIN_URI':f'https://example.invalid/docs/doc-{doc_id:03d}',
                     'TITLE_TXT':f'{topic} guide',
                     'BODY_TEXT':f'{topic} demonstration text, chunk {chunk}. This synthetic passage explains the standard process and the expected evidence for an AI-generated answer.',
                     'CHUNK_NUMBER':chunk,'EMBEDDING_BLOB_TXT':None,'LIFECYCLE_STATE':'READY'})
datasets = {
    'raw_customers.csv':customers,'raw_orders.csv':orders,'raw_order_lines.csv':lines,
    'ai_documents.csv':docs,'customer_features.csv':features,'support_tickets.csv':tickets,
    'orphan_regions.csv':regions,'empty_export.csv':[],
}
counts = {name:write_csv(name,rows) for name,rows in datasets.items()}
manifest = {
    'version':'2.0.0',
    'total_rows':sum(counts.values()),
    'row_counts':counts,
    'design':'Metadata is intentionally weak; row data is PK/FK ready.',
    'primary_key_candidates': {
        'RAW_CUSTOMERS':['CUSTOMER_ID'],
        'RAW_ORDERS':['ORDER_ID'],
        'RAW_ORDER_LINES':['ORDER_ID','LINE_NO'],
        'AI_DOCUMENTS':['DOC_ID','CHUNK_NUMBER'],
        'CUSTOMER_FEATURES':['CUSTOMER_ID'],
        'SUPPORT_TICKETS':['TICKET_ID'],
        'ORPHAN_REGIONS':['COUNTRY_CODE'],
        'EMPTY_EXPORT':['EXPORT_ID'],
    },
    'foreign_key_candidates': [
        ['RAW_CUSTOMERS.COUNTRY_CODE','ORPHAN_REGIONS.COUNTRY_CODE'],
        ['RAW_ORDERS.CUSTOMER_ID','RAW_CUSTOMERS.CUSTOMER_ID'],
        ['RAW_ORDER_LINES.ORDER_ID','RAW_ORDERS.ORDER_ID'],
        ['CUSTOMER_FEATURES.CUSTOMER_ID','RAW_CUSTOMERS.CUSTOMER_ID'],
        ['SUPPORT_TICKETS.CUSTOMER_ID','RAW_CUSTOMERS.CUSTOMER_ID'],
    ],
}
(DATA/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
