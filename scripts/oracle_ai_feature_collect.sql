-- Oracle AI Feature Readiness collector for SQLcl
-- Usage:
--   sql -s user/password@connect @oracle_ai_feature_collect.sql <schema_owner> <table_like_pattern>
-- Example:
--   sql -s admin/****@adb @scripts/oracle_ai_feature_collect.sql HR %
--
-- This script is read-only. It checks whether Select AI, AI Agent, and native Vector Search
-- packages/views are visible to the connected user, then inspects AI profiles and vector objects.

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
set serveroutput on size unlimited

define ai_owner = "&1"
define ai_table_like = "&2"

spool oracle_ai_feature_readiness_&&ai_owner..out replace

prompt @@ORACLE_AI_FEATURE_COLLECTOR_VERSION:2
prompt @@SECTION:run_context
select
  sys_context('USERENV','DB_NAME') as db_name,
  sys_context('USERENV','CON_NAME') as con_name,
  sys_context('USERENV','CURRENT_SCHEMA') as current_schema,
  sys_context('USERENV','SESSION_USER') as session_user,
  upper('&&ai_owner') as target_owner,
  upper('&&ai_table_like') as table_like_pattern,
  to_char(systimestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF TZH:TZM') as scan_timestamp
from dual;
prompt @@END_SECTION

prompt @@SECTION:database_version
select product, version, version_full, status
from product_component_version
where product like 'Oracle%Database%'
order by product;
prompt @@END_SECTION

prompt @@SECTION:package_objects
select owner, object_name, object_type, status
from all_objects
where object_name in (
  'DBMS_CLOUD_AI',
  'DBMS_CLOUD_AI_AGENT',
  'DBMS_CLOUD',
  'DBMS_CLOUD_PIPELINE',
  'DBMS_VECTOR',
  'DBMS_VECTOR_CHAIN'
)
order by object_name, owner, object_type;
prompt @@END_SECTION

prompt @@SECTION:package_synonyms
select owner, synonym_name, table_owner, table_name, db_link
from all_synonyms
where synonym_name in (
  'DBMS_CLOUD_AI',
  'DBMS_CLOUD_AI_AGENT',
  'DBMS_CLOUD',
  'DBMS_CLOUD_PIPELINE',
  'DBMS_VECTOR',
  'DBMS_VECTOR_CHAIN'
)
order by synonym_name, owner;
prompt @@END_SECTION

prompt @@SECTION:package_subprograms
select owner,
       object_name,
       nvl(procedure_name, '(package)') as procedure_name,
       object_type,
       nvl(subprogram_id, 0) as subprogram_id
from all_procedures
where object_name in (
  'DBMS_CLOUD_AI',
  'DBMS_CLOUD_AI_AGENT',
  'DBMS_CLOUD',
  'DBMS_CLOUD_PIPELINE',
  'DBMS_VECTOR',
  'DBMS_VECTOR_CHAIN'
)
order by object_name, owner, subprogram_id, procedure_name;
prompt @@END_SECTION

prompt @@SECTION:target_vector_columns
select owner,
       table_name,
       column_name,
       data_type,
       data_length,
       data_precision,
       data_scale
from all_tab_columns
where owner = upper('&&ai_owner')
  and table_name like upper('&&ai_table_like') escape '\'
  and upper(data_type) = 'VECTOR'
order by owner, table_name, column_name;
prompt @@END_SECTION

prompt @@SECTION:native_vector_indexes
select i.owner,
       i.index_name,
       i.table_owner,
       i.table_name,
       i.index_type,
       i.status,
       ic.column_name,
       c.data_type
from all_indexes i
left join all_ind_columns ic
  on ic.index_owner = i.owner
 and ic.index_name = i.index_name
left join all_tab_columns c
  on c.owner = i.table_owner
 and c.table_name = i.table_name
 and c.column_name = ic.column_name
where i.table_owner = upper('&&ai_owner')
  and i.table_name like upper('&&ai_table_like') escape '\'
  and (
    upper(i.index_type) like '%VECTOR%'
    or upper(i.index_name) like '%VECTOR%'
    or upper(i.index_name) like '%HNSW%'
    or upper(i.index_name) like '%IVF%'
    or upper(nvl(c.data_type, '')) = 'VECTOR'
  )
order by i.owner, i.index_name, ic.column_position;
prompt @@END_SECTION

prompt @@SECTION:session_privileges
select privilege
from session_privs
where privilege in (
  'CREATE TABLE',
  'CREATE ANY TABLE',
  'CREATE PROCEDURE',
  'CREATE ANY PROCEDURE',
  'CREATE JOB',
  'CREATE CREDENTIAL',
  'EXECUTE ANY PROCEDURE'
)
order by privilege;
prompt @@END_SECTION

prompt @@SECTION:database_parameters
begin
  dbms_output.put_line('PROBE_STATUS,ERROR_CODE,ERROR_MESSAGE,NAME,VALUE');
  begin
    for r in (select name, value from v$parameter where name in ('compatible')) loop
      dbms_output.put_line('"OK","","","' || replace(r.name,'"','""') || '","' || replace(r.value,'"','""') || '"');
    end loop;
  exception
    when others then
      dbms_output.put_line('"ERROR","' || sqlcode || '","' || replace(sqlerrm,'"','""') || '","",""');
  end;
end;
/
prompt @@END_SECTION

prompt @@SECTION:ai_profiles
DECLARE
  c SYS_REFCURSOR;
  v_profile_name varchar2(4000);
  v_status varchar2(4000);
  v_description varchar2(4000);
  v_created varchar2(4000);
  v_last_modified varchar2(4000);
  v_count pls_integer := 0;
  function esc(p varchar2) return varchar2 is
  begin
    return '"' || replace(nvl(p,''), '"', '""') || '"';
  end;
BEGIN
  dbms_output.put_line('PROBE_STATUS,ERROR_CODE,ERROR_MESSAGE,PROFILE_NAME,STATUS,DESCRIPTION,CREATED,LAST_MODIFIED');
  begin
    open c for 'select profile_name, status, description, to_char(created, ''YYYY-MM-DD HH24:MI:SS''), to_char(last_modified, ''YYYY-MM-DD HH24:MI:SS'') from user_cloud_ai_profiles order by profile_name';
    loop
      fetch c into v_profile_name, v_status, v_description, v_created, v_last_modified;
      exit when c%notfound;
      v_count := v_count + 1;
      dbms_output.put_line(esc('OK') || ',' || esc('') || ',' || esc('') || ',' || esc(v_profile_name) || ',' || esc(v_status) || ',' || esc(v_description) || ',' || esc(v_created) || ',' || esc(v_last_modified));
    end loop;
    close c;
    if v_count = 0 then
      dbms_output.put_line(esc('OK') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc(''));
    end if;
  exception
    when others then
      if c%isopen then close c; end if;
      dbms_output.put_line(esc('ERROR') || ',' || esc(to_char(sqlcode)) || ',' || esc(sqlerrm) || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc(''));
  end;
END;
/
prompt @@END_SECTION

prompt @@SECTION:ai_profile_attributes
DECLARE
  c SYS_REFCURSOR;
  v_profile_name varchar2(4000);
  v_attribute_name varchar2(4000);
  v_attribute_value varchar2(4000);
  v_last_modified varchar2(4000);
  v_count pls_integer := 0;
  function esc(p varchar2) return varchar2 is
  begin
    return '"' || replace(nvl(p,''), '"', '""') || '"';
  end;
BEGIN
  dbms_output.put_line('PROBE_STATUS,ERROR_CODE,ERROR_MESSAGE,PROFILE_NAME,ATTRIBUTE_NAME,ATTRIBUTE_VALUE,LAST_MODIFIED');
  begin
    open c for 'select profile_name, attribute_name, substr(attribute_value,1,3900), to_char(last_modified, ''YYYY-MM-DD HH24:MI:SS'') from user_cloud_ai_profile_attributes order by profile_name, attribute_name';
    loop
      fetch c into v_profile_name, v_attribute_name, v_attribute_value, v_last_modified;
      exit when c%notfound;
      v_count := v_count + 1;
      dbms_output.put_line(esc('OK') || ',' || esc('') || ',' || esc('') || ',' || esc(v_profile_name) || ',' || esc(v_attribute_name) || ',' || esc(v_attribute_value) || ',' || esc(v_last_modified));
    end loop;
    close c;
    if v_count = 0 then
      dbms_output.put_line(esc('OK') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc(''));
    end if;
  exception
    when others then
      if c%isopen then close c; end if;
      dbms_output.put_line(esc('ERROR') || ',' || esc(to_char(sqlcode)) || ',' || esc(sqlerrm) || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc(''));
  end;
END;
/
prompt @@END_SECTION

prompt @@SECTION:cloud_vector_indexes
DECLARE
  c SYS_REFCURSOR;
  v_index_name varchar2(4000);
  v_status varchar2(4000);
  v_description varchar2(4000);
  v_created varchar2(4000);
  v_last_modified varchar2(4000);
  v_count pls_integer := 0;
  function esc(p varchar2) return varchar2 is
  begin
    return '"' || replace(nvl(p,''), '"', '""') || '"';
  end;
BEGIN
  dbms_output.put_line('PROBE_STATUS,ERROR_CODE,ERROR_MESSAGE,INDEX_NAME,STATUS,DESCRIPTION,CREATED,LAST_MODIFIED');
  begin
    open c for 'select index_name, status, description, to_char(created, ''YYYY-MM-DD HH24:MI:SS''), to_char(last_modified, ''YYYY-MM-DD HH24:MI:SS'') from user_cloud_vector_indexes order by index_name';
    loop
      fetch c into v_index_name, v_status, v_description, v_created, v_last_modified;
      exit when c%notfound;
      v_count := v_count + 1;
      dbms_output.put_line(esc('OK') || ',' || esc('') || ',' || esc('') || ',' || esc(v_index_name) || ',' || esc(v_status) || ',' || esc(v_description) || ',' || esc(v_created) || ',' || esc(v_last_modified));
    end loop;
    close c;
    if v_count = 0 then
      dbms_output.put_line(esc('OK') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc(''));
    end if;
  exception
    when others then
      if c%isopen then close c; end if;
      dbms_output.put_line(esc('ERROR') || ',' || esc(to_char(sqlcode)) || ',' || esc(sqlerrm) || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc(''));
  end;
END;
/
prompt @@END_SECTION

prompt @@SECTION:cloud_vector_index_attributes
DECLARE
  c SYS_REFCURSOR;
  v_index_name varchar2(4000);
  v_attribute_name varchar2(4000);
  v_attribute_value varchar2(4000);
  v_last_modified varchar2(4000);
  v_count pls_integer := 0;
  function esc(p varchar2) return varchar2 is
  begin
    return '"' || replace(nvl(p,''), '"', '""') || '"';
  end;
BEGIN
  dbms_output.put_line('PROBE_STATUS,ERROR_CODE,ERROR_MESSAGE,INDEX_NAME,ATTRIBUTE_NAME,ATTRIBUTE_VALUE,LAST_MODIFIED');
  begin
    open c for 'select index_name, attribute_name, substr(attribute_value,1,3900), to_char(last_modified, ''YYYY-MM-DD HH24:MI:SS'') from user_cloud_vector_index_attributes order by index_name, attribute_name';
    loop
      fetch c into v_index_name, v_attribute_name, v_attribute_value, v_last_modified;
      exit when c%notfound;
      v_count := v_count + 1;
      dbms_output.put_line(esc('OK') || ',' || esc('') || ',' || esc('') || ',' || esc(v_index_name) || ',' || esc(v_attribute_name) || ',' || esc(v_attribute_value) || ',' || esc(v_last_modified));
    end loop;
    close c;
    if v_count = 0 then
      dbms_output.put_line(esc('OK') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc(''));
    end if;
  exception
    when others then
      if c%isopen then close c; end if;
      dbms_output.put_line(esc('ERROR') || ',' || esc(to_char(sqlcode)) || ',' || esc(sqlerrm) || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc(''));
  end;
END;
/
prompt @@END_SECTION

prompt @@SECTION:user_credentials
DECLARE
  c SYS_REFCURSOR;
  v_credential_name varchar2(4000);
  v_username varchar2(4000);
  v_comments varchar2(4000);
  v_enabled varchar2(4000);
  v_count pls_integer := 0;
  function esc(p varchar2) return varchar2 is
  begin
    return '"' || replace(nvl(p,''), '"', '""') || '"';
  end;
BEGIN
  dbms_output.put_line('PROBE_STATUS,ERROR_CODE,ERROR_MESSAGE,CREDENTIAL_NAME,USERNAME,COMMENTS,ENABLED');
  begin
    open c for 'select credential_name, username, comments, enabled from user_credentials order by credential_name';
    loop
      fetch c into v_credential_name, v_username, v_comments, v_enabled;
      exit when c%notfound;
      v_count := v_count + 1;
      dbms_output.put_line(esc('OK') || ',' || esc('') || ',' || esc('') || ',' || esc(v_credential_name) || ',' || esc(v_username) || ',' || esc(v_comments) || ',' || esc(v_enabled));
    end loop;
    close c;
    if v_count = 0 then
      dbms_output.put_line(esc('OK') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc(''));
    end if;
  exception
    when others then
      if c%isopen then close c; end if;
      dbms_output.put_line(esc('ERROR') || ',' || esc(to_char(sqlcode)) || ',' || esc(sqlerrm) || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc(''));
  end;
END;
/
prompt @@END_SECTION

prompt @@SECTION:user_mining_models
DECLARE
  c SYS_REFCURSOR;
  v_model_name varchar2(4000);
  v_mining_function varchar2(4000);
  v_algorithm varchar2(4000);
  v_creation_date varchar2(4000);
  v_count pls_integer := 0;
  function esc(p varchar2) return varchar2 is
  begin
    return '"' || replace(nvl(p,''), '"', '""') || '"';
  end;
BEGIN
  dbms_output.put_line('PROBE_STATUS,ERROR_CODE,ERROR_MESSAGE,MODEL_NAME,MINING_FUNCTION,ALGORITHM,CREATION_DATE');
  begin
    open c for 'select model_name, mining_function, algorithm, to_char(creation_date, ''YYYY-MM-DD HH24:MI:SS'') from user_mining_models order by model_name';
    loop
      fetch c into v_model_name, v_mining_function, v_algorithm, v_creation_date;
      exit when c%notfound;
      v_count := v_count + 1;
      dbms_output.put_line(esc('OK') || ',' || esc('') || ',' || esc('') || ',' || esc(v_model_name) || ',' || esc(v_mining_function) || ',' || esc(v_algorithm) || ',' || esc(v_creation_date));
    end loop;
    close c;
    if v_count = 0 then
      dbms_output.put_line(esc('OK') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc(''));
    end if;
  exception
    when others then
      if c%isopen then close c; end if;
      dbms_output.put_line(esc('ERROR') || ',' || esc(to_char(sqlcode)) || ',' || esc(sqlerrm) || ',' || esc('') || ',' || esc('') || ',' || esc('') || ',' || esc(''));
  end;
END;
/
prompt @@END_SECTION

prompt @@END_ORACLE_AI_FEATURE_COLLECTOR

spool off
exit
