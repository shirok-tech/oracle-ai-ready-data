-- Run as ADMIN, SYS, or a user that can CREATE USER.
-- Usage in SQLcl:
--   @00_admin_create_schema.sql
-- The password is requested interactively and is not echoed.
--
-- This script drops BAD_AI_READY if it already exists.
-- Use only in an isolated test database or disposable schema.

set define on
set verify off
set feedback on
set serveroutput on

whenever sqlerror continue none
drop user bad_ai_ready cascade;
whenever sqlerror exit sql.sqlcode rollback

accept bad_ai_ready_password char prompt 'Enter a strong password for BAD_AI_READY: ' hide

create user bad_ai_ready identified by "&&bad_ai_ready_password"
  account unlock;

declare
  l_tablespace varchar2(128);
begin
  select default_tablespace
    into l_tablespace
    from dba_users
   where username = 'BAD_AI_READY';

  execute immediate
    'alter user bad_ai_ready quota unlimited on "' ||
    replace(l_tablespace, '"', '""') || '"';

  dbms_output.put_line('Quota granted on default tablespace: ' || l_tablespace);
end;
/

grant create session to bad_ai_ready;
grant create table to bad_ai_ready;
grant create view to bad_ai_ready;
grant create sequence to bad_ai_ready;

undefine bad_ai_ready_password

prompt BAD_AI_READY user created.
prompt Reconnect as BAD_AI_READY and run 01_create_bad_tables.sql.
