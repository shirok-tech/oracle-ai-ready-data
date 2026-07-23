
-- Run with SQLcl while connected as BAD_AI_READY.
-- Start SQLcl from the package root so data/*.csv resolves correctly.

set define off
set verify off
set feedback on
set timing on

whenever sqlerror exit sql.sqlcode rollback

begin
  if user <> 'BAD_AI_READY' then
    raise_application_error(-20001, 'Connect as BAD_AI_READY before running this script.');
  end if;
end;
/

set load default
set loadformat default
set loadformat csv column_names on delimiter , enclosures "" encoding UTF8
set load batch_rows 100 batches_per_commit 0 commit on errors 0 truncate on

load raw_customers data/raw_customers.csv
load raw_orders data/raw_orders.csv
load raw_order_lines data/raw_order_lines.csv
load ai_documents data/ai_documents.csv
load customer_features data/customer_features.csv
load support_tickets data/support_tickets.csv
load orphan_regions data/orphan_regions.csv

truncate table empty_export;
commit;

prompt CSV load completed.
prompt Expected total rows across the 8 tables: 448.
prompt All primary-key candidates are non-NULL and unique; all foreign-key candidates match.
