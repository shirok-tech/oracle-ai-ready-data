
-- Run while connected as BAD_AI_READY.
-- The row data is internally consistent, but the metadata is intentionally not AI-ready:
--   * no table comments or column comments
--   * no primary keys, foreign keys, unique keys, or check constraints
--   * no freshness columns or source-system metadata
--   * no optimizer statistics immediately before the first scan
--   * long text exists, but there is no VECTOR column
--
-- The data is deliberately clean enough that 07_apply_ai_ready_improvements.sql
-- can add PK/FK constraints without any preprocessing.

set define off
set verify off
set feedback on
set serveroutput on
set timing on

whenever sqlerror exit sql.sqlcode rollback

begin
  if user <> 'BAD_AI_READY' then
    raise_application_error(-20001, 'Connect as BAD_AI_READY before running this script.');
  end if;
end;
/

begin
  for r in (
    select table_name
      from user_tables
     where table_name in (
       'RAW_CUSTOMERS', 'RAW_ORDERS', 'RAW_ORDER_LINES', 'AI_DOCUMENTS',
       'CUSTOMER_FEATURES', 'SUPPORT_TICKETS', 'EMPTY_EXPORT', 'ORPHAN_REGIONS'
     )
  ) loop
    execute immediate 'drop table "' || r.table_name || '" cascade constraints purge';
  end loop;
end;
/

create table raw_customers (
  customer_id          number,
  full_name            varchar2(200),
  email                varchar2(320),
  phone                varchar2(80),
  ssn                  varchar2(40),
  birthdate_txt        varchar2(40),
  country_code         varchar2(20),
  signup_when_txt      varchar2(80),
  status_txt           varchar2(80),
  last_purchase_amt    varchar2(80),
  notes                clob
);

create table raw_orders (
  order_id             varchar2(80),
  customer_id          number,
  order_time_txt       varchar2(80),
  amount_txt           varchar2(80),
  currency_code        varchar2(20),
  shipping_postal_code varchar2(40),
  payment_card_hint    varchar2(80),
  order_payload        clob
);

create table raw_order_lines (
  order_id             varchar2(80),
  line_no              number,
  sku                  varchar2(80),
  quantity_txt         varchar2(80),
  unit_price_txt       varchar2(80),
  discount_txt         varchar2(80),
  line_comment         varchar2(4000)
);

create table ai_documents (
  doc_id               number,
  origin_uri           varchar2(1000),
  title_txt            varchar2(1000),
  body_text            clob,
  chunk_number         number,
  embedding_blob_txt   varchar2(4000),
  lifecycle_state      varchar2(80)
);

create table customer_features (
  customer_id          number,
  churn_score_txt      varchar2(80),
  lifetime_value_txt   varchar2(80),
  segment_code         varchar2(80),
  feature_notes        varchar2(4000)
);

create table support_tickets (
  ticket_id            varchar2(80),
  customer_id          number,
  severity_txt         varchar2(80),
  agent_email          varchar2(320),
  requester_phone      varchar2(80),
  ticket_status        varchar2(80),
  problem_description  clob,
  resolution_text      clob
);

create table empty_export (
  export_id            number,
  export_name          varchar2(200),
  payload              clob
);

create table orphan_regions (
  country_code         varchar2(20),
  region_name          varchar2(200),
  risk_tier_txt        varchar2(80)
);

prompt Created 8 intentionally metadata-poor tables.
prompt The CSV data is PK/FK ready; no COMMENT or constraint statement is executed yet.
