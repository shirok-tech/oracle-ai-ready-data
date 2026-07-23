
-- Reference queries for Part 3 Select AI / NL2SQL comparisons.
-- The row data is consistent; the comparison focuses on whether comments and
-- declared PK/FK relationships improve generated SQL.

-- 1. Active customers in Japan and their order totals.
select c.customer_id,
       c.full_name,
       sum(to_number(o.amount_txt, '999999999999D99', q'[NLS_NUMERIC_CHARACTERS='.,']')) as order_total
  from raw_customers c
  join raw_orders o
    on o.customer_id = c.customer_id
 where c.status_txt = 'ACTIVE'
   and c.country_code = 'JP'
 group by c.customer_id, c.full_name
 order by order_total desc
 fetch first 10 rows only;

-- 2. Customers with no orders. The packaged data has two orders per customer,
--    so the expected result is 0.
select count(*) as customers_without_orders
  from raw_customers c
 where not exists (
       select 1
         from raw_orders o
        where o.customer_id = c.customer_id
     );

-- 3. Monthly order totals for 2025.
select to_char(to_date(order_time_txt, 'YYYY-MM-DD'), 'YYYY-MM') as order_month,
       currency_code,
       sum(to_number(amount_txt, '999999999999D99', q'[NLS_NUMERIC_CHARACTERS='.,']')) as order_total
  from raw_orders
 where to_date(order_time_txt, 'YYYY-MM-DD') >= date '2025-01-01'
   and to_date(order_time_txt, 'YYYY-MM-DD') < date '2026-01-01'
 group by to_char(to_date(order_time_txt, 'YYYY-MM-DD'), 'YYYY-MM'), currency_code
 order by order_month, currency_code;

-- 4. Open or in-progress high-severity tickets by customer.
select t.customer_id,
       c.full_name,
       count(*) as ticket_count
  from support_tickets t
  join raw_customers c
    on c.customer_id = t.customer_id
 where t.ticket_status in ('OPEN', 'IN_PROGRESS')
   and to_number(t.severity_txt) >= 4
 group by t.customer_id, c.full_name
 order by ticket_count desc, t.customer_id;
