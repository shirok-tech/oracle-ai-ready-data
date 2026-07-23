-- Optional compliance-failure injection.
-- Run as BAD_AI_READY only in an isolated sandbox.
-- Some managed environments may prohibit broad PUBLIC grants.

set define off
set feedback on

whenever sqlerror continue none

grant select on raw_customers to public;
grant select on raw_orders to public;
grant select on support_tickets to public;

prompt Attempted 3 intentionally broad PUBLIC SELECT grants.
prompt Check USER_TAB_PRIVS_MADE or the verification script for the actual result.
