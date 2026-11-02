-- Payment ids handed out by the sequence after the last row in the backup.
-- The restored table ends at the backup's last id; the sequence was not restored,
-- so it still remembers every id issued before the incident.
SELECT max(payment_id)                                   AS last_id_in_backup,
       (SELECT last_value FROM payment_payment_id_seq)   AS last_id_issued,
       (SELECT last_value FROM payment_payment_id_seq) - max(payment_id) AS payments_lost
FROM payment;

-- The work of activity.sql: the 5 most recent rentals, which got a 1.99 payment
-- on 2026-07-30 after the backup. None of them has that payment now.
SELECT r.rental_id, r.customer_id, r.staff_id,
       p.payment_id IS NOT NULL AS payment_2026_07_30_present
FROM (SELECT * FROM rental ORDER BY rental_id DESC LIMIT 5) AS r
LEFT JOIN payment p
       ON p.rental_id = r.rental_id
      AND p.payment_date = timestamptz '2026-07-30 12:00+00'
ORDER BY r.rental_id DESC;
