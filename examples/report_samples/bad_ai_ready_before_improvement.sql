-- Remediation: missing table comments
-- Reason: テーブルコメントがないため、Contextual score と mandatory comment gate が低下します。
-- Purpose: テーブルの業務目的、粒度、更新頻度、AI利用時の注意点を明文化します。
-- Review: TODOコメントを業務オーナーが実際の説明に置き換えてから実行してください。
COMMENT ON TABLE "BAD_AI_READY"."AI_DOCUMENTS" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.AI_DOCUMENTS.';
COMMENT ON TABLE "BAD_AI_READY"."CUSTOMER_FEATURES" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.CUSTOMER_FEATURES.';
COMMENT ON TABLE "BAD_AI_READY"."EMPTY_EXPORT" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.EMPTY_EXPORT.';
COMMENT ON TABLE "BAD_AI_READY"."ORPHAN_REGIONS" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.ORPHAN_REGIONS.';
COMMENT ON TABLE "BAD_AI_READY"."RAW_CUSTOMERS" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.RAW_CUSTOMERS.';
COMMENT ON TABLE "BAD_AI_READY"."RAW_ORDERS" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.RAW_ORDERS.';
COMMENT ON TABLE "BAD_AI_READY"."RAW_ORDER_LINES" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.RAW_ORDER_LINES.';
COMMENT ON TABLE "BAD_AI_READY"."SUPPORT_TICKETS" IS 'TODO: describe business purpose, grain, refresh cadence, owner, and AI usage guidance for BAD_AI_READY.SUPPORT_TICKETS.';

-- Remediation: missing column comments
-- Reason: カラムコメントがないため、AIが列の意味、単位、NULLの意味、機微性を誤解する可能性があります。
-- Purpose: 各カラムの意味、形式、許容値、NULLの扱い、出所、機微性を明文化します。
-- Review: TODOコメントを業務オーナーが実際の説明に置き換えてから実行してください。
COMMENT ON COLUMN "BAD_AI_READY"."AI_DOCUMENTS"."BODY_TEXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AI_DOCUMENTS.BODY_TEXT.';
COMMENT ON COLUMN "BAD_AI_READY"."AI_DOCUMENTS"."CHUNK_NUMBER" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AI_DOCUMENTS.CHUNK_NUMBER.';
COMMENT ON COLUMN "BAD_AI_READY"."AI_DOCUMENTS"."DOC_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AI_DOCUMENTS.DOC_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."AI_DOCUMENTS"."EMBEDDING_BLOB_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AI_DOCUMENTS.EMBEDDING_BLOB_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."AI_DOCUMENTS"."LIFECYCLE_STATE" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AI_DOCUMENTS.LIFECYCLE_STATE.';
COMMENT ON COLUMN "BAD_AI_READY"."AI_DOCUMENTS"."ORIGIN_URI" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AI_DOCUMENTS.ORIGIN_URI.';
COMMENT ON COLUMN "BAD_AI_READY"."AI_DOCUMENTS"."TITLE_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.AI_DOCUMENTS.TITLE_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."CUSTOMER_FEATURES"."CHURN_SCORE_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.CUSTOMER_FEATURES.CHURN_SCORE_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."CUSTOMER_FEATURES"."CUSTOMER_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.CUSTOMER_FEATURES.CUSTOMER_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."CUSTOMER_FEATURES"."FEATURE_NOTES" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.CUSTOMER_FEATURES.FEATURE_NOTES.';
COMMENT ON COLUMN "BAD_AI_READY"."CUSTOMER_FEATURES"."LIFETIME_VALUE_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.CUSTOMER_FEATURES.LIFETIME_VALUE_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."CUSTOMER_FEATURES"."SEGMENT_CODE" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.CUSTOMER_FEATURES.SEGMENT_CODE.';
COMMENT ON COLUMN "BAD_AI_READY"."EMPTY_EXPORT"."EXPORT_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.EMPTY_EXPORT.EXPORT_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."EMPTY_EXPORT"."EXPORT_NAME" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.EMPTY_EXPORT.EXPORT_NAME.';
COMMENT ON COLUMN "BAD_AI_READY"."EMPTY_EXPORT"."PAYLOAD" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.EMPTY_EXPORT.PAYLOAD.';
COMMENT ON COLUMN "BAD_AI_READY"."ORPHAN_REGIONS"."COUNTRY_CODE" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.ORPHAN_REGIONS.COUNTRY_CODE.';
COMMENT ON COLUMN "BAD_AI_READY"."ORPHAN_REGIONS"."REGION_NAME" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.ORPHAN_REGIONS.REGION_NAME.';
COMMENT ON COLUMN "BAD_AI_READY"."ORPHAN_REGIONS"."RISK_TIER_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.ORPHAN_REGIONS.RISK_TIER_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."BIRTHDATE_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.BIRTHDATE_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."COUNTRY_CODE" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.COUNTRY_CODE.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."CUSTOMER_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.CUSTOMER_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."EMAIL" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.EMAIL.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."FULL_NAME" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.FULL_NAME.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."LAST_PURCHASE_AMT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.LAST_PURCHASE_AMT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."NOTES" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.NOTES.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."PHONE" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.PHONE.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."SIGNUP_WHEN_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.SIGNUP_WHEN_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."SSN" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.SSN.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_CUSTOMERS"."STATUS_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_CUSTOMERS.STATUS_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDERS"."AMOUNT_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDERS.AMOUNT_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDERS"."CURRENCY_CODE" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDERS.CURRENCY_CODE.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDERS"."CUSTOMER_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDERS.CUSTOMER_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDERS"."ORDER_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDERS.ORDER_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDERS"."ORDER_PAYLOAD" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDERS.ORDER_PAYLOAD.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDERS"."ORDER_TIME_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDERS.ORDER_TIME_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDERS"."PAYMENT_CARD_HINT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDERS.PAYMENT_CARD_HINT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDERS"."SHIPPING_POSTAL_CODE" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDERS.SHIPPING_POSTAL_CODE.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDER_LINES"."DISCOUNT_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDER_LINES.DISCOUNT_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDER_LINES"."LINE_COMMENT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDER_LINES.LINE_COMMENT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDER_LINES"."LINE_NO" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDER_LINES.LINE_NO.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDER_LINES"."ORDER_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDER_LINES.ORDER_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDER_LINES"."QUANTITY_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDER_LINES.QUANTITY_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDER_LINES"."SKU" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDER_LINES.SKU.';
COMMENT ON COLUMN "BAD_AI_READY"."RAW_ORDER_LINES"."UNIT_PRICE_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.RAW_ORDER_LINES.UNIT_PRICE_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."SUPPORT_TICKETS"."AGENT_EMAIL" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.SUPPORT_TICKETS.AGENT_EMAIL.';
COMMENT ON COLUMN "BAD_AI_READY"."SUPPORT_TICKETS"."CUSTOMER_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.SUPPORT_TICKETS.CUSTOMER_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."SUPPORT_TICKETS"."PROBLEM_DESCRIPTION" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.SUPPORT_TICKETS.PROBLEM_DESCRIPTION.';
COMMENT ON COLUMN "BAD_AI_READY"."SUPPORT_TICKETS"."REQUESTER_PHONE" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.SUPPORT_TICKETS.REQUESTER_PHONE.';
COMMENT ON COLUMN "BAD_AI_READY"."SUPPORT_TICKETS"."RESOLUTION_TEXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.SUPPORT_TICKETS.RESOLUTION_TEXT.';
COMMENT ON COLUMN "BAD_AI_READY"."SUPPORT_TICKETS"."SEVERITY_TXT" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.SUPPORT_TICKETS.SEVERITY_TXT.';
COMMENT ON COLUMN "BAD_AI_READY"."SUPPORT_TICKETS"."TICKET_ID" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.SUPPORT_TICKETS.TICKET_ID.';
COMMENT ON COLUMN "BAD_AI_READY"."SUPPORT_TICKETS"."TICKET_STATUS" IS 'TODO: define meaning, unit/format, null semantics, allowed values, source, and sensitivity for BAD_AI_READY.SUPPORT_TICKETS.TICKET_STATUS.';

-- Remediation: missing or stale optimizer statistics
-- Reason: LAST_ANALYZEDが未設定または古いため、Clean/Current score が低下します。
-- Purpose: Oracle optimizer統計を収集し、メタデータ上もデータ状態を確認しやすくします。
-- Review: 大きい表ではメンテナンス時間、DBMS_STATS設定、サンプリング方針をDBAと確認してください。
-- Target: BAD_AI_READY.EMPTY_EXPORT; stats_reason=missing
BEGIN
  DBMS_STATS.GATHER_TABLE_STATS(
    ownname => 'BAD_AI_READY',
    tabname => 'EMPTY_EXPORT',
    cascade => TRUE,
    method_opt => 'FOR ALL COLUMNS SIZE AUTO'
  );
END;
/

-- Template only: primary key candidates
-- Reason: 主キー未検出のため、Clean/Correlated/Consumable score が低下します。
-- Purpose: AI回答の根拠行を安定して参照できる業務キーを明確にします。
-- Review: 重複データ、NULL、既存アプリ影響、制約名、索引方針を確認するまで実行しないでください。
-- ALTER TABLE "BAD_AI_READY"."AI_DOCUMENTS" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);
-- ALTER TABLE "BAD_AI_READY"."CUSTOMER_FEATURES" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);
-- ALTER TABLE "BAD_AI_READY"."EMPTY_EXPORT" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);
-- ALTER TABLE "BAD_AI_READY"."ORPHAN_REGIONS" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);
-- ALTER TABLE "BAD_AI_READY"."RAW_CUSTOMERS" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);
-- ALTER TABLE "BAD_AI_READY"."RAW_ORDERS" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);
-- ALTER TABLE "BAD_AI_READY"."RAW_ORDER_LINES" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);
-- ALTER TABLE "BAD_AI_READY"."SUPPORT_TICKETS" ADD CONSTRAINT <constraint_name> PRIMARY KEY (<column_list>);

-- Template only: freshness column candidates
-- Reason: 鮮度列が未検出のため、Current score が低下し、AI回答でデータの新しさを説明しづらくなります。
-- Purpose: 更新日時、取込日時、有効期間などを明示し、RAG/agent回答の鮮度説明を可能にします。
-- Review: アプリが別の方法で鮮度を管理していないか確認し、列追加の影響をレビューしてください。
-- ALTER TABLE "BAD_AI_READY"."AI_DOCUMENTS" ADD "UPDATED_AT" TIMESTAMP(6);
-- ALTER TABLE "BAD_AI_READY"."CUSTOMER_FEATURES" ADD "UPDATED_AT" TIMESTAMP(6);
-- ALTER TABLE "BAD_AI_READY"."EMPTY_EXPORT" ADD "UPDATED_AT" TIMESTAMP(6);
-- ALTER TABLE "BAD_AI_READY"."ORPHAN_REGIONS" ADD "UPDATED_AT" TIMESTAMP(6);
-- ALTER TABLE "BAD_AI_READY"."RAW_CUSTOMERS" ADD "UPDATED_AT" TIMESTAMP(6);
-- ALTER TABLE "BAD_AI_READY"."RAW_ORDERS" ADD "UPDATED_AT" TIMESTAMP(6);
-- ALTER TABLE "BAD_AI_READY"."RAW_ORDER_LINES" ADD "UPDATED_AT" TIMESTAMP(6);
-- ALTER TABLE "BAD_AI_READY"."SUPPORT_TICKETS" ADD "UPDATED_AT" TIMESTAMP(6);

-- Review only: broad data grants
-- Reason: PUBLICなど広い相手へのデータアクセス権限があるため、Compliant score が低下します。
-- Purpose: AI利用前に公開範囲が意図通りかを確認し、不要な広い権限を減らします。
-- Review: REVOKEはアプリや利用者に影響するため、DBA/業務オーナー確認後に個別判断してください。
-- Review grant: SELECT on BAD_AI_READY.RAW_CUSTOMERS to PUBLIC
-- REVOKE SELECT ON "BAD_AI_READY"."RAW_CUSTOMERS" FROM "PUBLIC";
-- Review grant: SELECT on BAD_AI_READY.RAW_ORDERS to PUBLIC
-- REVOKE SELECT ON "BAD_AI_READY"."RAW_ORDERS" FROM "PUBLIC";
-- Review grant: SELECT on BAD_AI_READY.SUPPORT_TICKETS to PUBLIC
-- REVOKE SELECT ON "BAD_AI_READY"."SUPPORT_TICKETS" FROM "PUBLIC";
