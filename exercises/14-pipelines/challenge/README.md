# Challenge 14: MongoDB II, aggregation pipelines and reports

Obrigatório.

## Enunciado

Build an incremental daily revenue report with `$merge`: each run processes only the days that changed since the last run (track a watermark in a separate document), and running it twice in a row produces exactly the same result. Prove both properties with a test that inserts new rentals between runs.
