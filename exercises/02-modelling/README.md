# Exercício 02: Modelling, ER diagrams and normalisation

## Enunciado

Folder: `exercises/02-modelling/model.md`

The requirements for a municipal library are in the exercise folder: readers, books, copies, authors, publishers, loans, reservations and fines.

1. An ER diagram in Mermaid, with cardinalities.
2. A list of tables in 3NF, with primary and foreign keys.
3. One denormalisation you would make and why, or why you would make none.

You will implement this model in exercise 03.

## Challenge (obrigatório, em `challenge/`)

The library opens three branches, and copies can be transferred between them. Readers can return a copy at any branch. Extend your model to record where each copy is at any moment and the full history of its transfers. Then find a table in your model that is in 3NF but not in BCNF (Boyce-Codd normal form), or show that none exists, and explain the difference.
