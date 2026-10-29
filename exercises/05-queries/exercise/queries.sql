-- Exercise 05: 10 business questions on Pagila
--
-- Runs on a fresh copy: ./scripts/create-db.sh ex05 --pagila --reset
-- No window functions (they are the topic of session 06).
-- A film can belong to more than one category; per category, it counts in each one.

-- 1. The number of films per category, including categories with no films,
--    most films first, then by category name.

select c.category_id, c.name as category, count(fc.film_id) as films
from category c
left join film_category fc on fc.category_id = c.category_id
group by c.category_id
order by films desc, c.name;

-- 2. Revenue per category per month in 2025, by payment_date.

select c.name as category,
       date_trunc('month', p.payment_date)::date as month,
       sum(p.amount) as revenue
from payment p
join rental r         on r.rental_id = p.rental_id
join inventory i      on i.inventory_id = r.inventory_id
join film_category fc on fc.film_id = i.film_id
join category c       on c.category_id = fc.category_id
where p.payment_date >= '2025-01-01' and p.payment_date < '2026-01-01'
group by c.category_id, month
order by c.name, month;

-- 3. Films that have never been rented, including films with no copy in any store.

select f.film_id, f.title
from film f
where not exists (
    select 1
    from inventory i
    join rental r on r.inventory_id = i.inventory_id
    where i.film_id = f.film_id
)
order by f.film_id;

-- 4. Customers who have rented films of all 5 ratings.

select c.customer_id, c.first_name, c.last_name
from customer c
join rental r    on r.customer_id = c.customer_id
join inventory i on i.inventory_id = r.inventory_id
join film f      on f.film_id = i.film_id
group by c.customer_id
having count(distinct f.rating) = (select count(distinct rating) from film)
order by c.customer_id;

-- 5. Pairs of actors who appeared together in more than 3 films, each pair
--    listed once, with the number of films (self join).

select a1.actor_id, a1.first_name || ' ' || a1.last_name as actor,
       a2.actor_id as other_actor_id, a2.first_name || ' ' || a2.last_name as other_actor,
       count(*) as films
from film_actor fa1
join film_actor fa2 on fa2.film_id = fa1.film_id
                   and fa2.actor_id > fa1.actor_id   -- each pair once, never an actor with itself
join actor a1 on a1.actor_id = fa1.actor_id
join actor a2 on a2.actor_id = fa2.actor_id
group by a1.actor_id, a2.actor_id
having count(*) > 3
order by films desc, a1.actor_id, a2.actor_id;

-- 6. Countries with more than 20 customers, with the number of customers and
--    the total they paid, most customers first.
--
-- Payments are summed per customer first: joining payment directly would
-- repeat each customer once per payment and inflate count(*).

with paid as (
    select customer_id, sum(amount) as total
    from payment
    group by customer_id
)
select co.country, count(*) as customers, coalesce(sum(p.total), 0) as paid
from customer c
join address a  on a.address_id = c.address_id
join city ci    on ci.city_id = a.city_id
join country co on co.country_id = ci.country_id
left join paid p on p.customer_id = c.customer_id
group by co.country_id
having count(*) > 20
order by customers desc, co.country;

-- 7. Customers who paid more in total than the average customer of their own
--    country. A customer with no payments counts as 0.

with customer_total as (
    select c.customer_id, c.first_name, c.last_name, ci.country_id,
           coalesce((select sum(p.amount) from payment p
                     where p.customer_id = c.customer_id), 0) as total
    from customer c
    join address a on a.address_id = c.address_id
    join city ci   on ci.city_id = a.city_id
),
country_avg as (
    select country_id, avg(total) as avg_total
    from customer_total
    group by country_id
)
select ct.customer_id, ct.first_name, ct.last_name, co.country,
       ct.total, round(ca.avg_total, 2) as country_avg
from customer_total ct
join country_avg ca on ca.country_id = ct.country_id
join country co     on co.country_id = ct.country_id
where ct.total > ca.avg_total
order by co.country, ct.total desc, ct.customer_id;

-- 8. The longest films of each rating, including ties, using a subquery.

select f.rating, f.film_id, f.title, f.length
from film f
where f.length = (
    select max(f2.length) from film f2 where f2.rating = f.rating
)
order by f.rating, f.film_id;

-- 9. Customers with no rental on or after 2026-04-01.

select c.customer_id, c.first_name, c.last_name
from customer c
where not exists (
    select 1 from rental r
    where r.customer_id = c.customer_id
      and r.rental_date >= '2026-04-01'
)
order by c.customer_id;

-- 10. For each category, the average number of days a film stays out
--     (return_date - rental_date, returned rentals only), rounded to 2
--     decimals, highest first.

select c.name as category,
       round(avg(extract(epoch from r.return_date - r.rental_date) / 86400), 2) as avg_days
from rental r
join inventory i      on i.inventory_id = r.inventory_id
join film_category fc on fc.film_id = i.film_id
join category c       on c.category_id = fc.category_id
where r.return_date is not null
group by c.category_id
order by avg_days desc, c.name;
