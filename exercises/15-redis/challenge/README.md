# Challenge 15: Redis I, data structures and patterns

Opcional.

## Enunciado

The fixed-window rate limit above lets a client send 20 requests in two seconds (10 at the end of one minute, 10 at the start of the next). Implement a sliding-window rate limit with a sorted set (timestamps as scores), as a Lua script so that the check and the insert are atomic. Write a test that shows the burst passing the fixed window and being blocked by the sliding one.
