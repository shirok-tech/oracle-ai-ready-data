-- Run as BAD_AI_READY after the tables are created.
-- It can be run either before or after 07_apply_ai_ready_improvements.sql.
-- This grants least-privilege read access to the dedicated Select AI user.
-- Change the following value when your Select AI user is not ADB_USER.

define SELECT_AI_USER = ADB_USER

set define on
set verify on
set feedback on
whenever sqlerror exit sql.sqlcode rollback

begin
  if user <> 'BAD_AI_READY' then
    raise_application_error(-20010,
      'Connect as BAD_AI_READY before running 10_grant_select_ai_access.sql.');
  end if;
end;
/

grant select on "BAD_AI_READY"."RAW_CUSTOMERS"     to &SELECT_AI_USER;
grant select on "BAD_AI_READY"."RAW_ORDERS"        to &SELECT_AI_USER;
grant select on "BAD_AI_READY"."RAW_ORDER_LINES"   to &SELECT_AI_USER;
grant select on "BAD_AI_READY"."CUSTOMER_FEATURES" to &SELECT_AI_USER;
grant select on "BAD_AI_READY"."SUPPORT_TICKETS"   to &SELECT_AI_USER;
grant select on "BAD_AI_READY"."ORPHAN_REGIONS"    to &SELECT_AI_USER;
grant select on "BAD_AI_READY"."AI_DOCUMENTS"      to &SELECT_AI_USER;
grant select on "BAD_AI_READY"."EMPTY_EXPORT"      to &SELECT_AI_USER;

prompt Granted SELECT on the eight BAD_AI_READY demo tables to &SELECT_AI_USER.
prompt Continue as &SELECT_AI_USER and run 11_create_select_ai_profile.sql.
