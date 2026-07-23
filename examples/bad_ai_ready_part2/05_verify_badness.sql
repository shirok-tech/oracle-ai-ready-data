
-- Run as BAD_AI_READY after loading the CSV files and before applying improvements.
-- The expected design is:
--   metadata deficiencies exist, but every PK/FK candidate is immediately valid.

set define off
set verify off
set feedback on
set pagesize 200
set linesize 240
set null <NULL>

column table_name format a24
column issue format a56
column issue_count format 999999
column last_analyzed format a20

prompt ============================================================================
prompt 1. Row counts
prompt ============================================================================

select 'AI_DOCUMENTS' table_name, count(*) row_count from ai_documents
union all select 'CUSTOMER_FEATURES', count(*) from customer_features
union all select 'EMPTY_EXPORT', count(*) from empty_export
union all select 'ORPHAN_REGIONS', count(*) from orphan_regions
union all select 'RAW_CUSTOMERS', count(*) from raw_customers
union all select 'RAW_ORDER_LINES', count(*) from raw_order_lines
union all select 'RAW_ORDERS', count(*) from raw_orders
union all select 'SUPPORT_TICKETS', count(*) from support_tickets
order by table_name;

prompt ============================================================================
prompt 2. Metadata deficiencies expected before remediation
prompt ============================================================================

select 'Table comments present; expected 0' issue, count(*) issue_count
  from user_tab_comments
 where table_type = 'TABLE'
   and table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS')
   and comments is not null
union all
select 'Column comments present; expected 0', count(*)
  from user_col_comments
 where table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS')
   and comments is not null
union all
select 'PK/UQ/FK/CHECK constraints; expected 0', count(*)
  from user_constraints
 where table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS')
   and constraint_type in ('P','U','R','C')
union all
select 'Tables with optimizer stats; expected 0 after script 04', count(*)
  from user_tables
 where table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS')
   and last_analyzed is not null
union all
select 'Tables with UPDATED_AT; expected 0', count(distinct table_name)
  from user_tab_columns
 where table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS')
   and column_name = 'UPDATED_AT'
union all
select 'Tables with SOURCE_SYSTEM; expected 0', count(distinct table_name)
  from user_tab_columns
 where table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS')
   and column_name = 'SOURCE_SYSTEM'
union all
select 'VECTOR columns; expected 0', count(*)
  from user_tab_columns
 where table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS')
   and data_type = 'VECTOR';

prompt ============================================================================
prompt 3. PK candidate violations - every count must be 0
prompt ============================================================================

select 'RAW_CUSTOMERS: NULL or duplicate CUSTOMER_ID' issue, count(*) issue_count
  from (
    select customer_id
      from raw_customers
     group by customer_id
    having customer_id is null or count(*) > 1
  )
union all
select 'RAW_ORDERS: NULL or duplicate ORDER_ID', count(*)
  from (
    select order_id
      from raw_orders
     group by order_id
    having order_id is null or count(*) > 1
  )
union all
select 'RAW_ORDER_LINES: NULL or duplicate ORDER_ID/LINE_NO', count(*)
  from (
    select order_id, line_no
      from raw_order_lines
     group by order_id, line_no
    having order_id is null or line_no is null or count(*) > 1
  )
union all
select 'AI_DOCUMENTS: NULL or duplicate DOC_ID/CHUNK_NUMBER', count(*)
  from (
    select doc_id, chunk_number
      from ai_documents
     group by doc_id, chunk_number
    having doc_id is null or chunk_number is null or count(*) > 1
  )
union all
select 'CUSTOMER_FEATURES: NULL or duplicate CUSTOMER_ID', count(*)
  from (
    select customer_id
      from customer_features
     group by customer_id
    having customer_id is null or count(*) > 1
  )
union all
select 'SUPPORT_TICKETS: NULL or duplicate TICKET_ID', count(*)
  from (
    select ticket_id
      from support_tickets
     group by ticket_id
    having ticket_id is null or count(*) > 1
  )
union all
select 'ORPHAN_REGIONS: NULL or duplicate COUNTRY_CODE', count(*)
  from (
    select country_code
      from orphan_regions
     group by country_code
    having country_code is null or count(*) > 1
  );

prompt ============================================================================
prompt 4. FK candidate violations - every count must be 0
prompt ============================================================================

select 'RAW_CUSTOMERS.COUNTRY_CODE without region master' issue, count(*) issue_count
  from raw_customers c
 where not exists (select 1 from orphan_regions r where r.country_code = c.country_code)
union all
select 'RAW_ORDERS.CUSTOMER_ID without customer', count(*)
  from raw_orders o
 where not exists (select 1 from raw_customers c where c.customer_id = o.customer_id)
union all
select 'RAW_ORDER_LINES.ORDER_ID without order', count(*)
  from raw_order_lines l
 where not exists (select 1 from raw_orders o where o.order_id = l.order_id)
union all
select 'CUSTOMER_FEATURES.CUSTOMER_ID without customer', count(*)
  from customer_features f
 where not exists (select 1 from raw_customers c where c.customer_id = f.customer_id)
union all
select 'SUPPORT_TICKETS.CUSTOMER_ID without customer', count(*)
  from support_tickets t
 where not exists (select 1 from raw_customers c where c.customer_id = t.customer_id);

prompt ============================================================================
prompt 5. Canonical text values - every count must be 0
prompt ============================================================================

select 'Noncanonical RAW_ORDERS.AMOUNT_TXT' issue, count(*) issue_count
  from raw_orders
 where not regexp_like(amount_txt, '^[0-9]+([.][0-9]{2})$')
union all
select 'Noncanonical RAW_ORDERS.ORDER_TIME_TXT', count(*)
  from raw_orders
 where not regexp_like(order_time_txt, '^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
union all
select 'Unexpected RAW_CUSTOMERS.STATUS_TXT', count(*)
  from raw_customers
 where status_txt not in ('ACTIVE','INACTIVE','SUSPENDED')
union all
select 'Unexpected SUPPORT_TICKETS.TICKET_STATUS', count(*)
  from support_tickets
 where ticket_status not in ('OPEN','IN_PROGRESS','RESOLVED','CLOSED');

prompt ============================================================================
prompt 6. Broad grants, if the optional injection script was executed
prompt ============================================================================

select grantee, table_name, privilege, grantable
  from user_tab_privs_made
 where grantee = 'PUBLIC'
 order by table_name, privilege;

prompt Verification complete.
prompt All sections 3, 4, and 5 should show zero violations.
prompt You can apply 07_apply_ai_ready_improvements.sql without cleaning the CSV rows.
