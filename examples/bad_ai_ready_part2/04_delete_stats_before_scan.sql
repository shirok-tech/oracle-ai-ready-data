-- Run as BAD_AI_READY immediately before collecting AI-ready metadata.
-- Autonomous AI Database can gather optimizer statistics automatically,
-- so this makes the missing-statistics test reproducible for the next scan.

set define off
set feedback on
set serveroutput on

whenever sqlerror exit sql.sqlcode rollback

begin
  if user <> 'BAD_AI_READY' then
    raise_application_error(-20001, 'Connect as BAD_AI_READY before running this script.');
  end if;

  dbms_stats.delete_schema_stats(ownname => user);
  dbms_output.put_line('Optimizer statistics deleted for ' || user || '.');
end;
/

prompt Run the oracle-ai-ready-data collector soon after this script.
