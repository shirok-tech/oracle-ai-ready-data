
-- Optional schema-only RAG preparation for AI_DOCUMENTS.
-- Run only on Oracle Database releases that support the VECTOR data type.
-- This creates the storage column and documentation, but it does not generate
-- embeddings. Actual embedding generation and retrieval-quality validation remain
-- separate tasks for the RAG episode.

set define off
set feedback on
set serveroutput on
whenever sqlerror exit sql.sqlcode rollback

begin
  if user <> 'BAD_AI_READY' then
    raise_application_error(-20001, 'Connect as BAD_AI_READY before running this script.');
  end if;
end;
/

declare
  l_count pls_integer;
begin
  select count(*)
    into l_count
    from user_tab_columns
   where table_name = 'AI_DOCUMENTS'
     and column_name = 'EMBEDDING';

  if l_count = 0 then
    execute immediate 'alter table "AI_DOCUMENTS" add ("EMBEDDING" VECTOR(384, FLOAT32))';
    dbms_output.put_line('Added AI_DOCUMENTS.EMBEDDING VECTOR(384, FLOAT32).');
  else
    dbms_output.put_line('AI_DOCUMENTS.EMBEDDING already exists.');
  end if;
end;
/

COMMENT ON COLUMN "BAD_AI_READY"."AI_DOCUMENTS"."EMBEDDING" IS
  'BODY_TEXTから生成する384次元の埋め込みベクトル。NULLは未生成を表す。モデル名と生成手順はRAG運用設計で別途管理する。';

begin
  dbms_stats.gather_table_stats(
    ownname => user,
    tabname => 'AI_DOCUMENTS',
    cascade => true,
    method_opt => 'FOR ALL COLUMNS SIZE AUTO'
  );
end;
/

prompt For a RAG-focused Skill rerun, scope the table pattern to AI_DOCUMENTS.
prompt Do not describe retrieval as production-ready until embeddings are populated and evaluated.
