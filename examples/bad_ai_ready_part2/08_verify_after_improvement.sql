
-- Run as BAD_AI_READY after 07_apply_ai_ready_improvements.sql.

set define off
set verify off
set feedback on
set pagesize 200
set linesize 240
set null <NULL>

column metric format a54
column actual format 999999
column expected format 999999
column result format a8
column constraint_name format a28
column table_name format a24
column constraint_type format a4

prompt ============================================================================
prompt 1. AI Ready remediation checklist
prompt ============================================================================

with checks as (
  select 'Target tables' metric, 8 expected,
         (select count(*) from user_tables where table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS')) actual
    from dual
  union all
  select 'Table comments', 8,
         (select count(*) from user_tab_comments where table_type = 'TABLE' and table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS') and comments is not null)
    from dual
  union all
  select 'Commented columns after metadata columns are added', 68,
         (select count(*) from user_col_comments where table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS') and comments is not null)
    from dual
  union all
  select 'Primary keys', 8,
         (select count(*) from user_constraints where table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS') and constraint_type = 'P' and status = 'ENABLED' and validated = 'VALIDATED')
    from dual
  union all
  select 'Foreign keys', 5,
         (select count(*) from user_constraints where table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS') and constraint_type = 'R' and status = 'ENABLED' and validated = 'VALIDATED')
    from dual
  union all
  select 'Tables with UPDATED_AT', 8,
         (select count(distinct table_name) from user_tab_columns where table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS') and column_name = 'UPDATED_AT')
    from dual
  union all
  select 'Tables with SOURCE_SYSTEM', 8,
         (select count(distinct table_name) from user_tab_columns where table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS') and column_name = 'SOURCE_SYSTEM')
    from dual
  union all
  select 'Tables with optimizer statistics', 8,
         (select count(*) from user_tables where table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS') and last_analyzed is not null)
    from dual
  union all
  select 'Broad PUBLIC SELECT or READ grants', 0,
         (select count(*) from user_tab_privs_made where grantee = 'PUBLIC' and table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS') and privilege in ('SELECT','READ'))
    from dual
)
select metric,
       actual,
       expected,
       case when actual = expected then 'PASS' else 'FAIL' end result
  from checks
 order by metric;

prompt ============================================================================
prompt 2. Enabled and validated PK/FK constraints
prompt ============================================================================

select constraint_name, table_name, constraint_type, status, validated
  from user_constraints
 where table_name in ('AI_DOCUMENTS','CUSTOMER_FEATURES','EMPTY_EXPORT','ORPHAN_REGIONS','RAW_CUSTOMERS','RAW_ORDERS','RAW_ORDER_LINES','SUPPORT_TICKETS')
   and constraint_type in ('P','R')
 order by constraint_type, table_name, constraint_name;

prompt ============================================================================
prompt 3. Referential integrity remains valid
prompt ============================================================================

column issue format a56
column issue_count format 999999

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

prompt Every checklist row should be PASS and every integrity count should be 0.
prompt Then rerun the Skill. The Mandatory comment gate should pass.
