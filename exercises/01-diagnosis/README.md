# Exercício 01: Database engines and diagnosis

## Enunciado

Folder: `exercises/01-diagnosis/README.md`

1. A screenshot of `docker compose ps` with the three engines healthy.
2. The data model of your Project I: list of tables and relationships.
3. Three concrete problems in that model (for example duplicated data, a missing constraint, a field that should be a table, a price calculated on read), with the file and line where each one is.
4. What would happen with 100,000 records, or with two users writing at the same time.
5. Would any of the data be better in MongoDB or Redis? Why?

If you do not have a Project I, use booking-lite or, with permission, a colleague's project.

Marked 2 when all five points are answered with examples from the actual code.

## Challenge (opcional, em `challenge/`)

Write a Python script that starts 10 processes, each appending 1,000 records to the same JSON file (read, append, write back). Count how many records end up in the file. Then do the same against a PostgreSQL table with 10 concurrent connections and compare. Explain in a few sentences why the numbers differ.

## Checklist

- [ ] Screenshot of `docker compose ps` with the three engines healthy
- [ ] Data model of Project I: list of tables and relationships
- [ ] Three concrete problems in that model, with file and line for each
- [ ] What would happen with 100,000 records, or two users writing at the same time
- [ ] Would any of the data be better in MongoDB or Redis? Why?
