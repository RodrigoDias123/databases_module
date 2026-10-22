# Exercício 09: Security

## Enunciado

Folder: `exercises/09-security/`

1. `roles.sql` with three roles on Pagila (`migrations`, `app`, `readonly`) and proof that `DROP TABLE` as `app` fails, and that `SELECT` as `readonly` works while `INSERT` fails.
2. The mini-API in `exercises/09-security/vulnerable-api/` is vulnerable to SQL injection. Run it locally, document the payload that exploits it, and fix the code.
3. A Redis ACL user that can `GET` and `SET` but cannot `FLUSHALL`.

## Challenge (obrigatório, em `challenge/`)

Add row-level security to Pagila so that a connection can only see the rentals and payments of one customer. The application sets the customer with `SET app.customer_id = '42'` at the start of each request, and the policy uses `current_setting('app.customer_id')`. Prove that a query without a `WHERE` returns only that customer's rows, and that the `app` role cannot bypass the policy.

## Checklist

- [ ] roles.sql with proof (see roles.sql)
- [ ] vulnerable-api/: run it, document the SQL injection payload, fix the code
- [ ] Redis ACL user that can GET and SET but cannot FLUSHALL (with proof)
