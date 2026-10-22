# Exercício 14: MongoDB II, aggregation pipelines and reports

## Enunciado

Folder: `exercises/14-pipelines/`

1. 4 pipelines: revenue per category per month; the actor with most films in each category; distribution of film lengths in ranges (`$bucket`); a `$facet` with 3 summaries.
2. A script to back up and restore the collections.

Marked 2 when the 4 pipelines are correct and the restore has been tested.

Group project: report generation, 3 pipelines and MongoDB backup. Milestone M3 closes at the end of this session.

## Challenge (obrigatório, em `challenge/`)

Build an incremental daily revenue report with `$merge`: each run processes only the days that changed since the last run (track a watermark in a separate document), and running it twice in a row produces exactly the same result. Prove both properties with a test that inserts new rentals between runs.

## Checklist

- [ ] Pipeline: revenue per category per month
- [ ] Pipeline: actor with most films in each category
- [ ] Pipeline: film length distribution with $bucket
- [ ] Pipeline: $facet with 3 summaries
- [ ] Script to back up and restore the collections (restore tested)
