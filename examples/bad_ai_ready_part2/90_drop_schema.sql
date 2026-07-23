-- Run as ADMIN, SYS, or another account that can DROP USER.
-- Destructive: removes BAD_AI_READY and every object in the schema.

set feedback on
whenever sqlerror exit sql.sqlcode rollback

drop user bad_ai_ready cascade;

prompt BAD_AI_READY dropped.
