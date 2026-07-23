-- Deterministic reference SQL for comparing Select AI generated SQL and results.
-- Run as BAD_AI_READY, or prefix objects with BAD_AI_READY when run as ADB_USER.

set linesize 250
set pagesize 1000
set feedback on

prompt T01
select count(*) as customer_count
  from bad_ai_ready.raw_customers;

prompt T02
select r.region_name,
       count(*) as active_customer_count
  from bad_ai_ready.raw_customers c
  join bad_ai_ready.orphan_regions r
    on r.country_code = c.country_code
 where c.status_txt = 'ACTIVE'
 group by r.region_name
 order by active_customer_count desc, r.region_name asc;

prompt T03
select c.customer_id,
       c.full_name,
       sum(to_number(o.amount_txt,
                     '999999999999D99',
                     q'[NLS_NUMERIC_CHARACTERS='.,']')) as total_order_amount,
       o.currency_code
  from bad_ai_ready.raw_customers c
  join bad_ai_ready.raw_orders o
    on o.customer_id = c.customer_id
 where c.status_txt = 'ACTIVE'
   and c.country_code = 'JP'
 group by c.customer_id, c.full_name, o.currency_code
 order by total_order_amount desc, c.customer_id asc
 fetch first 10 rows only;

prompt T04
select to_char(to_date(o.order_time_txt, 'YYYY-MM-DD'), 'YYYY-MM') as order_month,
       o.currency_code,
       sum(to_number(o.amount_txt,
                     '999999999999D99',
                     q'[NLS_NUMERIC_CHARACTERS='.,']')) as total_order_amount
  from bad_ai_ready.raw_orders o
 where to_date(o.order_time_txt, 'YYYY-MM-DD') >= date '2025-01-01'
   and to_date(o.order_time_txt, 'YYYY-MM-DD') <  date '2026-01-01'
 group by to_char(to_date(o.order_time_txt, 'YYYY-MM-DD'), 'YYYY-MM'),
          o.currency_code
 order by order_month asc, o.currency_code asc;

prompt T05
select count(*) as customers_without_orders
  from bad_ai_ready.raw_customers c
 where not exists (
       select 1
         from bad_ai_ready.raw_orders o
        where o.customer_id = c.customer_id
     );

prompt T06
select c.customer_id,
       c.full_name,
       count(*) as ticket_count
  from bad_ai_ready.support_tickets t
  join bad_ai_ready.raw_customers c
    on c.customer_id = t.customer_id
 where t.ticket_status in ('OPEN', 'IN_PROGRESS')
   and to_number(t.severity_txt) >= 4
 group by c.customer_id, c.full_name
 order by ticket_count desc, c.customer_id asc;

prompt T07
select f.segment_code,
       count(*) as customer_count,
       avg(to_number(f.lifetime_value_txt,
                     '999999999999D99',
                     q'[NLS_NUMERIC_CHARACTERS='.,']')) as average_lifetime_value
  from bad_ai_ready.customer_features f
 where to_number(f.churn_score_txt,
                 '0D99',
                 q'[NLS_NUMERIC_CHARACTERS='.,']') >= 0.80
 group by f.segment_code
 order by f.segment_code asc;

prompt T08
select l.sku,
       sum(to_number(l.quantity_txt)) as total_quantity
  from bad_ai_ready.raw_customers c
  join bad_ai_ready.raw_orders o
    on o.customer_id = c.customer_id
  join bad_ai_ready.raw_order_lines l
    on l.order_id = o.order_id
 where c.status_txt = 'ACTIVE'
   and c.country_code = 'JP'
 group by l.sku
 order by total_quantity desc, l.sku asc
 fetch first 10 rows only;

prompt T09
select o.source_system,
       count(*) as row_count,
       max(o.updated_at) as latest_updated_at
  from bad_ai_ready.raw_orders o
 group by o.source_system
 order by o.source_system asc;

prompt T10
select count(*) as external_export_count
  from bad_ai_ready.empty_export;
