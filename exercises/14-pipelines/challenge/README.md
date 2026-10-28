# Challenge 14: MongoDB II, aggregation pipelines and reports

Opcional.

## Enunciado

Folder: `exercises/14-pipelines/challenge/`

**Goal.** Keep a report up to date incrementally with `$merge`, so that each run is cheap and running it again changes nothing.

**Starting point.** The `rentals` collection of the exercise of session 13.

**Tasks.**

1. `daily_revenue.js` (or `.py`) builds the collection `daily_revenue` with one document per day: `_id` (the day), `rentals` and `revenue`, using `$merge` with `whenMatched: "replace"`.
2. Track a watermark in a collection `report_state`: the highest `rentals._id` processed. Each run finds the days of the rentals with `_id` above the watermark, recomputes only those days from all their rentals, merges them, and then moves the watermark.
3. Write a test that:
   1. runs the report on the full collection;
   2. inserts 5 new rentals into `rentals`, with `_id` above the current maximum: 3 on `2026-07-28` (a day that already has rentals) and 2 on `2026-07-29` (a new day);
   3. runs the report again and checks that only those 2 days changed;
   4. compares `daily_revenue` with a full recomputation from scratch;
   5. runs the report a third time and checks that nothing changed.

**Deliverables.**

- The report script and the test.
- `README.md` with how to run them, the output of the test, and why recomputing a whole day is safer than adding the new amounts to it.

**Done when.** The test passes: the second run touches only 2 days, the result equals a full recomputation, and the third run changes nothing.
