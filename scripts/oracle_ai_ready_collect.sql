-- Oracle AI Ready Data metadata collector for SQLcl
-- Usage:
--   sql -s user/password@connect @oracle_ai_ready_collect.sql <schema_owner> <table_like_pattern> <profile>
-- Example:
--   sql -s ai_audit/****@dbhost:1521/service @oracle_ai_ready_collect.sql HR % rag
--
-- This script is read-only. It queries ALL_* dictionary views visible to the connected user.

-- Do not inherit ECHO ON: echoed SQL would corrupt the sectioned CSV spool.
set echo off
set define on
set verify off
set feedback off
set heading on
set pagesize 50000
set linesize 32767
set long 200000
set longchunksize 200000
set trimspool on
set termout on
set sqlformat csv

define ai_owner = "&1"
define ai_table_like = "&2"
define ai_profile = "&3"

spool oracle_ai_ready_scan_&&ai_owner._&&ai_profile..out replace

prompt @@ORACLE_AI_READY_COLLECTOR_VERSION:1
prompt @@SECTION:run_context
select
  sys_context('USERENV','DB_NAME') as db_name,
  sys_context('USERENV','CON_NAME') as con_name,
  sys_context('USERENV','CURRENT_SCHEMA') as current_schema,
  sys_context('USERENV','SESSION_USER') as session_user,
  upper('&&ai_owner') as target_owner,
  upper('&&ai_table_like') as table_like_pattern,
  lower('&&ai_profile') as profile,
  to_char(systimestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF TZH:TZM') as scan_timestamp
from dual;
prompt @@END_SECTION

prompt @@SECTION:table_inventory
select
  t.owner,
  t.table_name,
  t.num_rows,
  to_char(t.last_analyzed, 'YYYY-MM-DD HH24:MI:SS') as last_analyzed,
  t.temporary,
  t.nested,
  t.secondary,
  t.iot_type,
  t.partitioned
from all_tables t
where t.owner = upper('&&ai_owner')
  and t.table_name like upper('&&ai_table_like') escape '\'
  and nvl(t.temporary, 'N') = 'N'
  and nvl(t.nested, 'NO') = 'NO'
  and nvl(t.secondary, 'N') = 'N'
order by t.owner, t.table_name;
prompt @@END_SECTION

prompt @@SECTION:column_inventory
select
  c.owner,
  c.table_name,
  c.column_id,
  c.column_name,
  c.data_type,
  c.data_length,
  c.data_precision,
  c.data_scale,
  c.nullable,
  c.num_distinct,
  c.num_nulls,
  to_char(c.last_analyzed, 'YYYY-MM-DD HH24:MI:SS') as last_analyzed
from all_tab_columns c
where c.owner = upper('&&ai_owner')
  and c.table_name like upper('&&ai_table_like') escape '\'
  and exists (
    select 1
    from all_tables t
    where t.owner = c.owner
      and t.table_name = c.table_name
      and nvl(t.temporary, 'N') = 'N'
      and nvl(t.nested, 'NO') = 'NO'
      and nvl(t.secondary, 'N') = 'N'
  )
order by c.owner, c.table_name, c.column_id;
prompt @@END_SECTION

prompt @@SECTION:table_comments
select
  t.owner,
  t.table_name,
  tc.comments
from all_tables t
left join all_tab_comments tc
  on tc.owner = t.owner
 and tc.table_name = t.table_name
where t.owner = upper('&&ai_owner')
  and t.table_name like upper('&&ai_table_like') escape '\'
  and nvl(t.temporary, 'N') = 'N'
  and nvl(t.nested, 'NO') = 'NO'
  and nvl(t.secondary, 'N') = 'N'
order by t.owner, t.table_name;
prompt @@END_SECTION

prompt @@SECTION:column_comments
select
  c.owner,
  c.table_name,
  c.column_name,
  cc.comments
from all_tab_columns c
left join all_col_comments cc
  on cc.owner = c.owner
 and cc.table_name = c.table_name
 and cc.column_name = c.column_name
where c.owner = upper('&&ai_owner')
  and c.table_name like upper('&&ai_table_like') escape '\'
  and exists (
    select 1
    from all_tables t
    where t.owner = c.owner
      and t.table_name = c.table_name
      and nvl(t.temporary, 'N') = 'N'
      and nvl(t.nested, 'NO') = 'NO'
      and nvl(t.secondary, 'N') = 'N'
  )
order by c.owner, c.table_name, c.column_name;
prompt @@END_SECTION

prompt @@SECTION:constraints
select
  ac.owner,
  ac.table_name,
  ac.constraint_name,
  ac.constraint_type,
  ac.status,
  ac.validated,
  ac.r_owner,
  ac.r_constraint_name,
  ac.delete_rule,
  ac.deferrable,
  ac.deferred
from all_constraints ac
where ac.owner = upper('&&ai_owner')
  and ac.table_name like upper('&&ai_table_like') escape '\'
  and ac.constraint_type in ('P','U','R','C')
  and exists (
    select 1
    from all_tables t
    where t.owner = ac.owner
      and t.table_name = ac.table_name
      and nvl(t.temporary, 'N') = 'N'
      and nvl(t.nested, 'NO') = 'NO'
      and nvl(t.secondary, 'N') = 'N'
  )
order by ac.owner, ac.table_name, ac.constraint_type, ac.constraint_name;
prompt @@END_SECTION

prompt @@SECTION:constraint_columns
select
  acc.owner,
  acc.table_name,
  acc.constraint_name,
  acc.column_name,
  acc.position
from all_cons_columns acc
where acc.owner = upper('&&ai_owner')
  and acc.table_name like upper('&&ai_table_like') escape '\'
  and exists (
    select 1
    from all_constraints ac
    where ac.owner = acc.owner
      and ac.constraint_name = acc.constraint_name
      and ac.table_name = acc.table_name
      and ac.constraint_type in ('P','U','R','C')
  )
order by acc.owner, acc.table_name, acc.constraint_name, acc.position;
prompt @@END_SECTION

prompt @@SECTION:rag_candidate_columns
select
  c.owner,
  c.table_name,
  c.column_name,
  c.data_type,
  c.data_length,
  case
    when upper(c.data_type) = 'VECTOR' then 'vector'
    when upper(c.data_type) in ('CLOB','NCLOB','LONG') then 'long_text'
    when upper(c.data_type) in ('VARCHAR2','NVARCHAR2','CHAR','NCHAR') and nvl(c.data_length,0) >= 100 then 'text'
    else 'other'
  end as ai_candidate_type
from all_tab_columns c
where c.owner = upper('&&ai_owner')
  and c.table_name like upper('&&ai_table_like') escape '\'
  and (
    upper(c.data_type) = 'VECTOR'
    or upper(c.data_type) in ('CLOB','NCLOB','LONG')
    or (upper(c.data_type) in ('VARCHAR2','NVARCHAR2','CHAR','NCHAR') and nvl(c.data_length,0) >= 100)
  )
order by c.owner, c.table_name, c.column_id;
prompt @@END_SECTION

prompt @@SECTION:freshness_columns
select
  c.owner,
  c.table_name,
  c.column_name,
  c.data_type
from all_tab_columns c
where c.owner = upper('&&ai_owner')
  and c.table_name like upper('&&ai_table_like') escape '\'
  and regexp_like(c.column_name, '(^|_)(CREATED|UPDATED|UPDATE|MODIFIED|CHANGED|LOAD|LOADED|REFRESH|REFRESHED|EFFECTIVE|VALID|START|END)(_|$)|LAST_.*(DATE|TIME)|.*(_AT|_TS|_DATE)$', 'i')
  and (
    upper(c.data_type) = 'DATE'
    or upper(c.data_type) like 'TIMESTAMP%'
    or regexp_like(c.column_name, '(DATE|TIME|TS|AT)$', 'i')
  )
order by c.owner, c.table_name, c.column_id;
prompt @@END_SECTION

prompt @@SECTION:source_metadata_columns
select
  c.owner,
  c.table_name,
  c.column_name,
  c.data_type
from all_tab_columns c
where c.owner = upper('&&ai_owner')
  and c.table_name like upper('&&ai_table_like') escape '\'
  and regexp_like(c.column_name, '(^|_)(SOURCE|SRC|BATCH|LOAD|JOB|ETL|PIPELINE|FILE|SYSTEM|CREATED_BY|UPDATED_BY|INSERTED_BY|MODIFIED_BY)(_|$)|SOURCE_SYSTEM|SOURCE_ID|BATCH_ID|LOAD_ID|JOB_ID', 'i')
order by c.owner, c.table_name, c.column_id;
prompt @@END_SECTION

prompt @@SECTION:sensitive_candidate_columns
select
  c.owner,
  c.table_name,
  c.column_name,
  c.data_type,
  case
    when regexp_like(c.column_name, '(SSN|SIN|NATIONAL_ID|PASSPORT|DRIVER|LICENSE|TAX_ID|TIN|MYNUMBER|MY_NUMBER)', 'i') then 'government_id_candidate'
    when regexp_like(c.column_name, '(EMAIL|E_MAIL|PHONE|MOBILE|FAX|ADDRESS|ADDR|POSTAL|ZIP)', 'i') then 'contact_candidate'
    when regexp_like(c.column_name, '(DOB|BIRTH|BIRTHDAY|AGE|GENDER|SEX)', 'i') then 'demographic_candidate'
    when regexp_like(c.column_name, '(CARD|CREDIT|BANK|IBAN|ACCOUNT|SALARY|PAY|COMPENSATION)', 'i') then 'financial_candidate'
    when regexp_like(c.column_name, '(PASSWORD|PASSWD|TOKEN|SECRET|API_KEY|CREDENTIAL)', 'i') then 'credential_candidate'
    else 'sensitive_name_candidate'
  end as sensitivity_reason
from all_tab_columns c
where c.owner = upper('&&ai_owner')
  and c.table_name like upper('&&ai_table_like') escape '\'
  and regexp_like(c.column_name, '(SSN|SIN|NATIONAL_ID|PASSPORT|DRIVER|LICENSE|TAX_ID|TIN|MYNUMBER|MY_NUMBER|EMAIL|E_MAIL|PHONE|MOBILE|FAX|ADDRESS|ADDR|POSTAL|ZIP|DOB|BIRTH|BIRTHDAY|AGE|GENDER|SEX|CARD|CREDIT|BANK|IBAN|ACCOUNT|SALARY|PAY|COMPENSATION|PASSWORD|PASSWD|TOKEN|SECRET|API_KEY|CREDENTIAL)', 'i')
order by c.owner, c.table_name, c.column_id;
prompt @@END_SECTION

prompt @@SECTION:object_grants
select
  p.table_schema as owner,
  p.table_name,
  p.grantee,
  p.privilege,
  p.grantable
from all_tab_privs p
where p.table_schema = upper('&&ai_owner')
  and p.table_name like upper('&&ai_table_like') escape '\'
order by p.table_schema, p.table_name, p.grantee, p.privilege;
prompt @@END_SECTION

prompt @@END_ORACLE_AI_READY_COLLECTOR

spool off
exit
