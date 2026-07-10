-- Deliberately incomplete example for readiness testing.
CREATE TABLE bad_ai_ready_customer (
  id NUMBER,
  nm VARCHAR2(100),
  sts VARCHAR2(1),
  txt VARCHAR2(4000)
);

GRANT SELECT ON bad_ai_ready_customer TO PUBLIC;
