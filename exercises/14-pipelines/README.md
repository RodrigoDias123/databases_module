# Exercício 14: MongoDB II, aggregation pipelines and reports

## Enunciado

Folder: `exercises/14-pipelines/exercise/`

**Goal.** Build reports with aggregation pipelines, and back up and restore a MongoDB database.

**Starting point.** The collections `films` and `rentals` in `pagila_docs`, with the shapes given in the exercise of session 13, loaded from a fresh copy of Pagila and not changed afterwards. If you changed them, drop them and load them again.

**Tasks.** Write each pipeline in `pipelines.js` (for `mongosh`):

1. Revenue per category per month in 2025, by `rental_date`, from `rentals`. Output: `category`, `month`, `revenue`, sorted by category and month. Expected: 192 documents; `Action` in January 2025 has 333.87. In the README, explain why this value differs from question 2 of exercise 05 (314.94).
2. The actor with most films in each category, from `films`, including ties. Output: one document per category with `category`, `films` and an array `actors`. Expected: 16 documents with 30 actors in total.
3. The distribution of film lengths with `$bucket` and boundaries `[0, 60, 90, 120, 150, 186]`. Expected counts: 96, 224, 214, 216 and 250.
4. One `$facet` over `films` with three summaries: the total number of films and the average rental rate; the number of films per rating; the 5 longest films (`title`, `length`), ties broken by title. Expected: 1,000 films with an average rate of 2.98; G 178, PG 194, PG-13 223, R 195, NC-17 210; the 5 longest are `CHICAGO NORTH`, `CONTROL ANTHEM`, `DARN FORRESTER`, `GANGS PRIDE` and `HOME PITY`, all with 185 minutes.
5. `backup_mongo.sh` dumps `pagila_docs` to `backups/` as a compressed archive with a dated name (as in the tutorial). `restore_mongo.sh` restores the latest archive into a database called `pagila_docs_restored` (use `--nsFrom 'pagila_docs.*' --nsTo 'pagila_docs_restored.*'`) and prints the document count of each collection in both databases.

**Deliverables.**

- `pipelines.js`, `backup_mongo.sh`, `restore_mongo.sh`.
- `README.md` with the commands, the first documents of each pipeline result with its document count, the explanation asked in task 1, and the output of `restore_mongo.sh`.

**Done when.** Each pipeline returns the expected result, and the restored database has the same document count as the original in every collection.

## Challenge (opcional, em `challenge/`)

Enunciado completo em [challenge/README.md](challenge/README.md).

## Checklist

- [ ] Pipeline 1: revenue per category per month (192 docs) + explanation vs exercise 05
- [ ] Pipeline 2: actor with most films per category (16 docs, 30 actors)
- [ ] Pipeline 3: `$bucket` of film lengths
- [ ] Pipeline 4: `$facet` with 3 summaries
- [ ] `backup_mongo.sh` and `restore_mongo.sh` (restore tested, counts match)
