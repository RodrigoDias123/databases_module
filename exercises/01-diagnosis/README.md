# Exercício 01: Database engines and diagnosis

## Enunciado

Folder: `exercises/01-diagnosis/exercise/`

**Goal.** Diagnose the problems of a small shop that keeps its data in a JSON file, and decide which engine each kind of data belongs in.

**Starting point.** The module environment running (`docker compose up -d`). Save the following content as `shop.json` in your exercise folder, exactly as shown, so that line numbers match:

```json
{
  "customers": [
    {"id": 1, "name": "Ana Silva", "email": "ana@example.com", "city": "Porto"},
    {"id": 2, "name": "Rui Costa", "email": "rui@example.com", "city": "Lisboa"}
  ],
  "orders": [
    {"id": 1, "customer_id": 1, "customer_name": "Ana Silva", "customer_email": "ana@example.com",
     "items": "Keyboard x1; Mouse x2", "total": "59.90", "date": "07/10/2026"},
    {"id": 2, "customer_id": 3, "customer_name": "Marta Reis", "customer_email": "marta@example",
     "items": "Monitor x1", "total": "abc", "date": "2026-10-08"},
    {"id": 2, "customer_id": 1, "customer_name": "Ana Silva", "customer_email": "ana.silva@example.com",
     "items": "Mouse x-1", "total": 12.5, "date": "08/10/2026"}
  ],
  "products": [
    {"name": "Keyboard", "price": 29.90, "stock": 3},
    {"name": "Mouse", "price": "15", "stock": -2}
  ]
}
```

The shop's application reads the whole file, changes it in memory and writes the whole file back on every request.

**Tasks.**

1. Take a screenshot of `docker compose ps` with the three engines `healthy`.
2. Describe the data model of `shop.json`: the entities, their fields and the relationships between them.
3. Find at least 5 concrete problems in `shop.json`. For each one give the line number, the kind of problem (for example duplicated data, missing integrity rule, wrong type, a list stored in a single field, inconsistent format) and what can go wrong because of it.
4. Explain what happens to this design with 100,000 orders (finding the orders of one customer, adding one order) and when two requests add an order at the same time.
5. Say which engine (PostgreSQL, MongoDB or Redis) you would use for each of these and why: customers, orders, products, the last 10 products a customer viewed, the number of times each product page was opened today.

**Deliverables.**

- `README.md` with the screenshot and the answers to tasks 2 to 5.
- `shop.json`.

**Done when.** The screenshot shows the three services `healthy`, at least 5 problems of at least 3 different kinds are identified by line, and every engine choice in task 5 has a reason based on the theory of this session.

## Challenge (obrigatório, em `challenge/`)

Enunciado completo em [challenge/README.md](challenge/README.md).

## Checklist

- [ ] Screenshot of `docker compose ps` with the three engines `healthy`
- [ ] `shop.json` saved in the exercise folder
- [ ] Task 2: data model of `shop.json` (entities, fields, relationships)
- [ ] Task 3: at least 5 problems of at least 3 different kinds, each with line number, kind and consequence
- [ ] Task 4: 100,000 orders and two concurrent requests
- [ ] Task 5: engine for customers, orders, products, last 10 viewed products and page-view counts, with reasons

## Resposta

Resposta em [exercise/README.md](exercise/README.md).
