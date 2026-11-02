-- Row count and checksum of each restored table. Run it on the restored database
-- and on a full restore of the same dump: the two outputs must be identical.
SELECT 'payment' AS table_name, count(*) AS rows,
       md5(string_agg(p::text, ',' ORDER BY payment_id, payment_date)) AS checksum
FROM payment p
UNION ALL
SELECT 'film_actor', count(*),
       md5(string_agg(fa::text, ',' ORDER BY actor_id, film_id))
FROM film_actor fa
UNION ALL
SELECT 'film_category', count(*),
       md5(string_agg(fc::text, ',' ORDER BY film_id, category_id))
FROM film_category fc;
