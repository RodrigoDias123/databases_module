# Exercício 02: Modelling, ER diagrams and normalisation

## Enunciado

Folder: `exercises/02-modelling/exercise/`

**Goal.** Turn written requirements into an ER diagram and a set of tables in 3NF.

**Starting point.** The requirements of a municipal library:

- A reader has a unique card number, a name, a unique email, a phone number, an address and a registration date.
- A book has a unique ISBN-13, a title, a publication year, exactly one publisher and one or more authors. An author can write many books. For each book, the order of its authors matters (first author, second author, ...).
- A publisher has a unique name and a country.
- The library owns one or more copies of each book. A copy has a unique barcode, an acquisition date and a condition: `new`, `good`, `worn` or `damaged`.
- A reader borrows a copy. A loan records the reader, the copy, the loan date, the due date (14 days after the loan date) and the return date, which stays empty until the copy is returned. A copy can be in at most one open loan at a time. A reader can have at most 5 open loans.
- A reader can reserve a book (not a specific copy) when no copy of it is available. Reservations for the same book are served in the order they were made. A reservation is `active`, `fulfilled` or `cancelled`.
- A late return creates a fine of 0.50 per day late. A fine belongs to exactly one loan and records its amount and the date it was paid, which stays empty until it is paid.

**Tasks.**

1. Draw an ER diagram in Mermaid (`erDiagram`, as in the tutorial) with every entity, its attributes, primary keys, foreign keys and the cardinality of every relationship.
2. List the tables in 3NF. For each table give its columns, its primary key, its foreign keys and its `UNIQUE` columns.
3. List the business rules from the requirements that a table structure alone cannot enforce (for example "at most 5 open loans") and say where you would enforce each one: a constraint, a trigger or the application.
4. Describe one denormalisation you would make and why, or explain why you would make none.

**Deliverables.** `model.md` with the diagram and the answers to tasks 2 to 4. Check on GitHub that the diagram renders.

**Done when.** Every requirement above appears in the model, the N:N relationship between books and authors has an association table that keeps the author order, the tables are in 3NF, and the diagram renders on GitHub.

## Challenge (obrigatório, em `challenge/`)

Enunciado completo em [challenge/README.md](challenge/README.md).
