# Exercise 08: Transactions and concurrency

- [ ] Lost update reproduced in two psql sessions (balance column on customer), with command sequence
- [ ] Fix 1: atomic UPDATE
- [ ] Fix 2: SELECT ... FOR UPDATE
- [ ] Deadlock caused and PostgreSQL message explained
- [ ] Write skew: Python script with 20 simultaneous requests, rule broken under READ COMMITTED, fixed with SERIALIZABLE + retries, exactly one member stays active
