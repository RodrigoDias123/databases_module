# Challenge 02: Modelling, ER diagrams and normalisation

Obrigatório.

## Enunciado

Folder: `exercises/02-modelling/challenge/`

**Goal.** Extend a model with history and check it against a stricter normal form.

**Starting point.** The requirements of the exercise above. You can start from your own model.

**Tasks.**

1. The library opens three branches. Each copy belongs to one home branch, can be transferred to another branch, and can be returned at any branch. Extend the model so that it records where each copy is at any moment and the full history of its transfers (from, to, date and who authorised it).
2. Write two queries in plain language that the new model must answer, for example "where is copy X now?" and "which copies left branch Y last month?", and show which tables answer each one.
3. Find a table in your model that is in 3NF but not in BCNF (Boyce-Codd normal form), or show that none exists. Explain the difference between the two forms with an example.

**Deliverables.** `model.md` with the extended Mermaid diagram, the new and changed tables, and the answers to tasks 2 and 3.

**Done when.** The current location of a copy can be found without reading its whole history (or the README explains why reading the history is acceptable), every transfer is kept, and the BCNF answer includes the functional dependencies that justify it.

## Resposta

A resposta está em [model.md](model.md).
