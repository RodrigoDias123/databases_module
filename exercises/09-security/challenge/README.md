# Challenge 09: Security

Obrigatório.

## Enunciado

Add row-level security to Pagila so that a connection can only see the rentals and payments of one customer. The application sets the customer with `SET app.customer_id = '42'` at the start of each request, and the policy uses `current_setting('app.customer_id')`. Prove that a query without a `WHERE` returns only that customer's rows, and that the `app` role cannot bypass the policy.
