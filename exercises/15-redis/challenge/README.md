# Challenge 15: Redis I, data structures and patterns

Opcional.

## Enunciado

Folder: `exercises/15-redis/challenge/`

**Goal.** Replace the fixed-window rate limit with a sliding window and prove the difference with a test.

**Starting point.** The `allow_request` function of the exercise above, and `uv add pytest`.

**Tasks.**

1. Change the fixed-window function so that it takes the current time as an argument, `allow_request_fixed(customer_id, now)`, so that tests control the clock.
2. Write `allow_request_sliding(customer_id, now)`: 10 requests in any 60-second window, stored in a sorted set with the request time as score. Implement it as a Lua script that removes old entries, counts, and adds the new request in one atomic step. Each member must be unique even when two requests have the same time.
3. Write a pytest test that sends 10 requests at seconds 59.0 to 59.9 of one minute and 10 more at seconds 0.0 to 0.9 of the next, and shows that the fixed window accepts all 20 while the sliding window accepts only 10.
4. Write a test that sends 30 requests from 10 threads at the same moment to the sliding window and checks that exactly 10 are accepted.

**Deliverables.**

- The rate limit module and `tests/test_rate_limit.py`.
- `README.md` with `uv run pytest -v` output and an explanation of why the check and the insert must be atomic.

**Done when.** Both tests pass and show 20 accepted by the fixed window, 10 by the sliding window, and exactly 10 under concurrency.
