-- Run as the Select AI user used in the Qiita procedure, normally ADB_USER.
-- Prerequisites:
--   * DBMS_CLOUD_AI execute privilege and network ACL are already configured.
--   * OPENAI_CRED already exists for this user.
--   * 10_grant_select_ai_access.sql was run by BAD_AI_READY.
--
-- No model is hard-coded so this script can use the same working OpenAI model
-- configuration as the referenced Qiita procedure. Add a "model" attribute
-- here only when your environment requires an explicit model name.

set define off
set serveroutput on
set feedback on
whenever sqlerror exit sql.sqlcode rollback

begin
  begin
    dbms_cloud_ai.clear_profile;
  exception
    when others then null;
  end;

  begin
    dbms_cloud_ai.drop_profile(profile_name => 'BAD_AI_READY_OPENAI');
  exception
    when others then null;
  end;

  dbms_cloud_ai.create_profile(
    profile_name => 'BAD_AI_READY_OPENAI',
    description  => 'NL2SQL functional verification for the improved BAD_AI_READY demo schema',
    attributes   => q'~{
      "provider": "openai",
      "credential_name": "OPENAI_CRED",
      "object_list": [
        {"owner": "BAD_AI_READY", "name": "RAW_CUSTOMERS"},
        {"owner": "BAD_AI_READY", "name": "RAW_ORDERS"},
        {"owner": "BAD_AI_READY", "name": "RAW_ORDER_LINES"},
        {"owner": "BAD_AI_READY", "name": "CUSTOMER_FEATURES"},
        {"owner": "BAD_AI_READY", "name": "SUPPORT_TICKETS"},
        {"owner": "BAD_AI_READY", "name": "ORPHAN_REGIONS"},
        {"owner": "BAD_AI_READY", "name": "AI_DOCUMENTS"},
        {"owner": "BAD_AI_READY", "name": "EMPTY_EXPORT"}
      ],
      "object_list_mode": "all",
      "enforce_object_list": true,
      "comments": true,
      "constraints": true,
      "conversation": false
    }~'
  );

  dbms_cloud_ai.set_profile(profile_name => 'BAD_AI_READY_OPENAI');
end;
/

select dbms_cloud_ai.get_profile() as active_ai_profile from dual;

prompt AI profile BAD_AI_READY_OPENAI is active for this session.
prompt Table and column comments are enabled with comments=true.
prompt PK/FK metadata is enabled with constraints=true.
