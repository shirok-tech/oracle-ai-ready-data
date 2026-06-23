-- bad_ai_ready_schema.sql
-- Purpose: create an intentionally AI-not-ready Oracle Database schema for testing
--          the oracle-ai-ready-data Skill and comparing against HR.
--
-- Run with SQLcl as a PDB admin or another account allowed to CREATE USER,
-- CREATE TABLE in another schema, and GRANT object privileges.
--
-- Example:
--   sql admin/password@dbhost:1521/pdb1 @bad_ai_ready_schema.sql
--
-- Notes:
--   * This script DROPS user BAD_AI_READY if it already exists.
--   * Connect to a PDB, not CDB$ROOT, unless you intentionally adapt the username.
--   * The schema intentionally has no table comments and no column comments.
--   * The schema intentionally has no primary keys, foreign keys, unique keys, or check constraints.
--   * The schema intentionally has dirty data, duplicate identifiers, NULL-heavy columns,
--     inconsistent text formats, PII-like columns, and a PUBLIC SELECT grant.
--   * The script intentionally does NOT gather DBMS_STATS so LAST_ANALYZED is likely NULL.

set define off
set verify off
set feedback on
set serveroutput on
set timing on

prompt ============================================================================
prompt Reset BAD_AI_READY schema
prompt ============================================================================

whenever sqlerror continue none
drop user bad_ai_ready cascade;
whenever sqlerror exit sql.sqlcode

create user bad_ai_ready identified by "BadAiReady#2026"
  default tablespace users
  temporary tablespace temp
  quota unlimited on users
  account unlock;

grant create session to bad_ai_ready;
grant create table to bad_ai_ready;
grant create view to bad_ai_ready;
grant create sequence to bad_ai_ready;

prompt ============================================================================
prompt Create intentionally weak tables - no constraints, no comments
prompt ============================================================================

create table bad_ai_ready.raw_customers (
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

create table bad_ai_ready.raw_orders (
  order_id             varchar2(80),
  customer_id          number,
  order_time_txt       varchar2(80),
  amount_txt           varchar2(80),
  currency_code        varchar2(20),
  shipping_postal_code varchar2(40),
  payment_card_hint    varchar2(80),
  order_payload        clob
);

create table bad_ai_ready.raw_order_lines (
  order_id             varchar2(80),
  line_no              number,
  sku                  varchar2(80),
  quantity_txt         varchar2(80),
  unit_price_txt       varchar2(80),
  discount_txt         varchar2(80),
  line_comment         varchar2(4000)
);

create table bad_ai_ready.ai_documents (
  doc_id               number,
  origin_uri           varchar2(1000),
  title_txt            varchar2(1000),
  body_text            clob,
  chunk_number         number,
  embedding_blob_txt   varchar2(4000),
  lifecycle_state      varchar2(80)
);

create table bad_ai_ready.customer_features (
  customer_id          number,
  churn_score_txt      varchar2(80),
  lifetime_value_txt   varchar2(80),
  segment_code         varchar2(80),
  feature_notes        varchar2(4000)
);

create table bad_ai_ready.support_tickets (
  ticket_id            varchar2(80),
  customer_id          number,
  severity_txt         varchar2(80),
  agent_email          varchar2(320),
  requester_phone      varchar2(80),
  ticket_status        varchar2(80),
  problem_description  clob,
  resolution_text      clob
);

create table bad_ai_ready.empty_export (
  export_id            number,
  export_name          varchar2(200),
  payload              clob
);

create table bad_ai_ready.orphan_regions (
  country_code         varchar2(20),
  region_name          varchar2(200),
  risk_tier_txt        varchar2(80)
);

prompt ============================================================================
prompt Insert intentionally dirty data
prompt ============================================================================

declare
  v_email varchar2(320);
  v_phone varchar2(80);
  v_ssn   varchar2(40);
begin
  for i in 1 .. 120 loop
    v_email := case
      when mod(i, 16) = 0 then 'not-an-email'
      when mod(i, 23) = 0 then null
      when mod(i, 29) = 0 then 'duplicate@example.invalid'
      else 'customer' || i || '@example.invalid'
    end;

    v_phone := case
      when mod(i, 12) = 0 then null
      when mod(i, 17) = 0 then 'CALL-ME-MAYBE'
      else '+1-555-' || lpad(to_char(mod(i * 37, 10000)), 4, '0')
    end;

    v_ssn := case
      when mod(i, 15) = 0 then null
      when mod(i, 22) = 0 then '000-00-0000'
      else lpad(to_char(mod(i * 1009, 900) + 100), 3, '0') || '-' ||
           lpad(to_char(mod(i * 37, 90) + 10), 2, '0') || '-' ||
           lpad(to_char(mod(i * 719, 9000) + 1000), 4, '0')
    end;

    insert into bad_ai_ready.raw_customers (
      customer_id,
      full_name,
      email,
      phone,
      ssn,
      birthdate_txt,
      country_code,
      signup_when_txt,
      status_txt,
      last_purchase_amt,
      notes
    ) values (
      case
        when mod(i, 20) = 0 then null
        when mod(i, 11) = 0 then i - 1
        else i
      end,
      case
        when mod(i, 13) = 0 then null
        when mod(i, 19) = 0 then '   '
        else 'Customer ' || i
      end,
      v_email,
      v_phone,
      v_ssn,
      case
        when mod(i, 30) = 0 then '2099-12-31'
        when mod(i, 31) = 0 then 'not a date'
        when mod(i, 7) = 0 then to_char(date '1970-01-01' + mod(i * 13, 15000), 'DD/MM/YYYY')
        else to_char(date '1970-01-01' + mod(i * 13, 15000), 'YYYY-MM-DD')
      end,
      case
        when mod(i, 18) = 0 then null
        when mod(i, 14) = 0 then 'XX'
        when mod(i, 5) = 0 then 'JPN'
        when mod(i, 3) = 0 then 'US'
        else 'usa'
      end,
      case
        when mod(i, 21) = 0 then 'yesterday'
        when mod(i, 10) = 0 then '2026/99/99'
        else to_char(date '2021-01-01' + mod(i * 5, 1500), 'YYYY-MM-DD HH24:MI:SS')
      end,
      case
        when mod(i, 17) = 0 then null
        when mod(i, 9) = 0 then 'Active '
        when mod(i, 8) = 0 then 'A'
        when mod(i, 7) = 0 then 'unknown'
        else 'active'
      end,
      case
        when mod(i, 22) = 0 then 'not numeric'
        when mod(i, 25) = 0 then '-999.99'
        when mod(i, 18) = 0 then null
        else to_char(round(i * 12.345, 2))
      end,
      to_clob('Raw customer row with mixed formats and possible PII. Email=' || nvl(v_email, '<null>') ||
              ', phone=' || nvl(v_phone, '<null>') || ', ssn=' || nvl(v_ssn, '<null>') || '. ' ||
              rpad('No controlled vocabulary. ', 300, '*'))
    );
  end loop;
end;
/

declare
  v_customer_id number;
begin
  for i in 1 .. 300 loop
    v_customer_id := case
      when mod(i, 37) = 0 then 999999
      when mod(i, 41) = 0 then null
      else mod(i, 135) + 1
    end;

    insert into bad_ai_ready.raw_orders (
      order_id,
      customer_id,
      order_time_txt,
      amount_txt,
      currency_code,
      shipping_postal_code,
      payment_card_hint,
      order_payload
    ) values (
      case
        when mod(i, 25) = 0 then 'ORD-' || to_char(i - 1)
        when mod(i, 44) = 0 then null
        else 'ORD-' || to_char(i)
      end,
      v_customer_id,
      case
        when mod(i, 21) = 0 then 'today'
        when mod(i, 18) = 0 then '2026-02-31T99:99:99'
        when mod(i, 5) = 0 then to_char(date '2024-01-01' + mod(i, 800), 'DD-MON-YYYY')
        else to_char(date '2024-01-01' + mod(i, 800), 'YYYY-MM-DD')
      end,
      case
        when mod(i, 19) = 0 then 'free'
        when mod(i, 33) = 0 then null
        when mod(i, 27) = 0 then '-42.00'
        else to_char(round(i * 3.14159, 2))
      end,
      case
        when mod(i, 20) = 0 then '???'
        when mod(i, 11) = 0 then null
        when mod(i, 4) = 0 then 'JPY'
        else 'usd'
      end,
      case
        when mod(i, 12) = 0 then null
        when mod(i, 31) = 0 then 'ABCDE'
        else lpad(to_char(mod(i * 97, 100000)), 5, '0')
      end,
      case
        when mod(i, 9) = 0 then '411111******1111'
        when mod(i, 20) = 0 then 'card token missing'
        else null
      end,
      to_clob('{bad_json: true, order=' || i || ', customer=' || nvl(to_char(v_customer_id), 'null') ||
              ', notes="payload stored as opaque text"}')
    );
  end loop;
end;
/

begin
  for i in 1 .. 600 loop
    insert into bad_ai_ready.raw_order_lines (
      order_id,
      line_no,
      sku,
      quantity_txt,
      unit_price_txt,
      discount_txt,
      line_comment
    ) values (
      case
        when mod(i, 53) = 0 then 'ORD-999999'
        else 'ORD-' || to_char(mod(i, 320) + 1)
      end,
      case
        when mod(i, 47) = 0 then null
        when mod(i, 30) = 0 then 1
        else mod(i, 5) + 1
      end,
      case
        when mod(i, 29) = 0 then null
        when mod(i, 17) = 0 then 'UNKNOWN'
        else 'SKU-' || lpad(to_char(mod(i * 13, 200)), 4, '0')
      end,
      case
        when mod(i, 22) = 0 then 'many'
        when mod(i, 28) = 0 then '-1'
        else to_char(mod(i, 8) + 1)
      end,
      case
        when mod(i, 26) = 0 then null
        when mod(i, 31) = 0 then 'n/a'
        else to_char(round(mod(i * 1.77, 200), 2))
      end,
      case
        when mod(i, 16) = 0 then 'one hundred percent'
        when mod(i, 25) = 0 then '-10'
        else to_char(mod(i, 30))
      end,
      case
        when mod(i, 6) = 0 then rpad('Unstructured line note with inconsistent meaning. ', 500, '#')
        else null
      end
    );
  end loop;
end;
/

begin
  for i in 1 .. 40 loop
    insert into bad_ai_ready.ai_documents (
      doc_id,
      origin_uri,
      title_txt,
      body_text,
      chunk_number,
      embedding_blob_txt,
      lifecycle_state
    ) values (
      case when mod(i, 13) = 0 then null when mod(i, 10) = 0 then i - 1 else i end,
      case when mod(i, 9) = 0 then null else 's3://unknown-bucket/raw/doc_' || i || '.txt' end,
      case when mod(i, 8) = 0 then null else 'Document ' || i end,
      case
        when mod(i, 11) = 0 then null
        else to_clob(rpad('Long text document without chunking policy, embeddings, retention owner, or provenance. ', 1200, '~'))
      end,
      case when mod(i, 7) = 0 then null else 1 end,
      case when mod(i, 5) = 0 then 'not a vector; just serialized text' else null end,
      case when mod(i, 6) = 0 then '???' else 'loaded' end
    );
  end loop;
end;
/

begin
  for i in 1 .. 120 loop
    insert into bad_ai_ready.customer_features (
      customer_id,
      churn_score_txt,
      lifetime_value_txt,
      segment_code,
      feature_notes
    ) values (
      case when mod(i, 10) = 0 then i - 1 else i end,
      case when mod(i, 18) = 0 then 'high' when mod(i, 25) = 0 then null else to_char(round(mod(i * 0.037, 1), 4)) end,
      case when mod(i, 21) = 0 then 'unknown' when mod(i, 33) = 0 then '-1000' else to_char(round(i * 42.42, 2)) end,
      case when mod(i, 14) = 0 then null when mod(i, 9) = 0 then 'segment-x' else 'S' || mod(i, 5) end,
      case when mod(i, 12) = 0 then rpad('Feature row without training/serving lineage. ', 1000, '!') else null end
    );
  end loop;
end;
/

begin
  for i in 1 .. 90 loop
    insert into bad_ai_ready.support_tickets (
      ticket_id,
      customer_id,
      severity_txt,
      agent_email,
      requester_phone,
      ticket_status,
      problem_description,
      resolution_text
    ) values (
      case when mod(i, 20) = 0 then null when mod(i, 15) = 0 then 'T-' || to_char(i - 1) else 'T-' || to_char(i) end,
      case when mod(i, 17) = 0 then 777777 else mod(i, 140) + 1 end,
      case when mod(i, 13) = 0 then 'catastrophic-ish' when mod(i, 11) = 0 then null else to_char(mod(i, 5) + 1) end,
      case when mod(i, 19) = 0 then 'invalid-agent-email' else 'agent' || mod(i, 7) || '@example.invalid' end,
      case when mod(i, 16) = 0 then null else '+81-90-' || lpad(to_char(mod(i * 123, 10000)), 4, '0') || '-' || lpad(to_char(mod(i * 321, 10000)), 4, '0') end,
      case when mod(i, 12) = 0 then 'done?' when mod(i, 22) = 0 then null else 'open' end,
      to_clob(rpad('Customer reported a vague issue. Contains personal contact fragments and no taxonomy. ', 900, '?')),
      case when mod(i, 4) = 0 then to_clob('') else to_clob(rpad('Resolution text is incomplete or inconsistent. ', 400, '.')) end
    );
  end loop;
end;
/

insert into bad_ai_ready.orphan_regions values ('US',  'North America', 'low');
insert into bad_ai_ready.orphan_regions values ('usa', 'North America duplicate code', 'LOW');
insert into bad_ai_ready.orphan_regions values ('JPN', 'Japan', 'medium');
insert into bad_ai_ready.orphan_regions values ('XX',  null, 'unknown');
insert into bad_ai_ready.orphan_regions values (null,  'Missing code region', 'high');

commit;

prompt ============================================================================
prompt Add intentionally broad grants for compliance-gate testing
prompt ============================================================================

-- Intentionally bad for a sandbox schema: broad grants should be flagged by the Skill.
-- Comment these out if your environment forbids PUBLIC grants.
grant select on bad_ai_ready.raw_customers to public;
grant select on bad_ai_ready.raw_orders to public;
grant select on bad_ai_ready.support_tickets to public;

prompt ============================================================================
prompt Verification summary - comments should be zero and constraints should be zero
prompt ============================================================================

set pagesize 200
set linesize 200
column owner format a16
column table_name format a28
column column_name format a30
column num_rows format 999999
column last_analyzed format a20

select owner, table_name, num_rows, last_analyzed
from all_tables
where owner = 'BAD_AI_READY'
order by table_name;

select count(*) as table_comment_count
from all_tab_comments
where owner = 'BAD_AI_READY'
  and comments is not null;

select count(*) as column_comment_count
from all_col_comments
where owner = 'BAD_AI_READY'
  and comments is not null;

select count(*) as constraint_count
from all_constraints
where owner = 'BAD_AI_READY'
  and constraint_type in ('P','U','R','C');

select table_name, count(*) as sensitive_name_candidate_columns
from all_tab_columns
where owner = 'BAD_AI_READY'
  and regexp_like(column_name, '(SSN|EMAIL|PHONE|POSTAL|CARD|BIRTH|PAY)', 'i')
group by table_name
order by table_name;

select grantee, table_name, privilege
from all_tab_privs
where table_schema = 'BAD_AI_READY'
  and grantee = 'PUBLIC'
order by table_name, privilege;

prompt ============================================================================
prompt Done.
prompt Next, run the Skill collector, for example:
prompt   sql -s ai_audit/password@dbhost:1521/pdb1 @oracle_ai_ready_collect.sql BAD_AI_READY % scan
prompt   sql -s ai_audit/password@dbhost:1521/pdb1 @oracle_ai_ready_collect.sql HR % scan
prompt ============================================================================
