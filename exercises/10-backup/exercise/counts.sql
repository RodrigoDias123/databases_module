SELECT 'payment' AS table_name, count(*) AS rows FROM payment
UNION ALL SELECT 'film_actor', count(*) FROM film_actor
UNION ALL SELECT 'film_category', count(*) FROM film_category;
