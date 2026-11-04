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

Enunciado completo em [challenge/README.md](../challenge/README.md).

## Checklist

- [x] Pipeline 1: revenue per category per month (192 docs) + explanation vs exercise 05
- [x] Pipeline 2: actor with most films per category (16 docs, 30 actors)
- [x] Pipeline 3: `$bucket` of film lengths
- [x] Pipeline 4: `$facet` with 3 summaries
- [x] `backup_mongo.sh` and `restore_mongo.sh` (restore tested, counts match)

## Resolução

Ficheiros entregues:

- [pipelines.js](pipelines.js): as 4 pipelines das tarefas 1 a 4.
- [backup_mongo.sh](backup_mongo.sh): faz o dump de `pagila_docs` para `backups/`.
- [restore_mongo.sh](restore_mongo.sh): restaura o arquivo mais recente para `pagila_docs_restored` e mostra as contagens.

### Antes de começar

As coleções têm de estar acabadas de carregar. O `load.py` faz upserts e não apaga documentos a mais, como o filme 1001 do exercício 13, por isso `films` e `rentals` são apagadas primeiro. `DATABASE_URL` tem de apontar para a base `ex13`.

```bash
# a partir da raiz do repositório
set -a; . ./.env; set +a
mongosh "$MONGO_URL" --quiet --eval 'const d = db.getSiblingDB("pagila_docs"); d.films.drop(); d.rentals.drop();'
(cd exercises/13-mongo/exercise && uv run --env-file ../../../.env python load.py)
```

```
films: 1000
customers: 999
rentals: 51805
```

### Como correr

```bash
# a partir da raiz do repositório
set -a; . ./.env; set +a
cd exercises/14-pipelines/exercise
mongosh "$MONGO_URL" --quiet --file pipelines.js
./backup_mongo.sh
./restore_mongo.sh
```

### Resumo dos resultados

| Pipeline | Esperado | Obtido |
|----------|----------|--------|
| 1. Receita por categoria e mês | 192 documentos; `Action` em janeiro de 2025 com 333.87 | 192 documentos; 333.87 |
| 2. Ator com mais filmes por categoria | 16 documentos, 30 atores | 16 documentos, 30 atores |
| 3. Distribuição das durações | 96, 224, 214, 216, 250 | 96, 224, 214, 216, 250 |
| 4. Resumo com `$facet` | 1000 filmes, média de 2.98, ratings e top 5 do enunciado | iguais |

### Pipeline 1: receita por categoria e mês

192 documentos. Os primeiros:

```
{ revenue: Decimal128('333.87'), category: 'Action', month: 1 }
{ revenue: Decimal128('342.98'), category: 'Action', month: 2 }
{ revenue: Decimal128('385.83'), category: 'Action', month: 3 }
```

**Porque é que 333.87 difere de 314.94 (pergunta 2 do exercício 05)?**

As duas consultas somam os mesmos pagamentos, mas atribuem-nos a meses diferentes. A pipeline usa a data do aluguer (`rental_date`) e soma o `amount` de cada aluguer, enquanto a query do exercício 05 usa a data do pagamento (`payment_date`). Um aluguer pago noutro mês conta em janeiro numa consulta e não na outra.

Comparando as duas datas no PostgreSQL, para `Action` em janeiro de 2025:

| | Pagamentos | Valor |
|---|-----------|-------|
| Por `payment_date` (exercício 05) | | 314.94 |
| Alugados em janeiro e pagos noutro mês (entram só na pipeline) | 17 | + 46.83 |
| Pagos em janeiro e alugados noutro mês (entram só no exercício 05) | 10 | − 27.90 |
| **Por `rental_date` (esta pipeline)** | | **333.87** |

Nenhum dos valores está errado, porque respondem a perguntas diferentes: a receita gerada pelos alugueres de janeiro e o dinheiro recebido em janeiro.

### Pipeline 2: ator com mais filmes por categoria

16 documentos com 30 atores no total. Os primeiros:

```
{ category: 'Action', films: 10, actors: [ 'ANGELA HUDSON', 'MATTHEW CARREY' ] }
{ category: 'Animation', films: 10, actors: [ 'JAYNE NOLTE', 'UMA WOOD' ] }
{ category: 'Children', films: 9, actors: [ 'EWAN GOODING', 'RICHARD PENN', 'SIDNEY CROWE' ] }
```

A contagem agrupa por `actor_id` e não só pelo nome, porque há dois atores diferentes chamados `SUSAN DAVIS` (101 e 110). Agrupar só pelo nome somava os filmes dos dois e dava 26 atores em vez de 30.

### Pipeline 3: distribuição das durações

5 documentos. `_id` é o limite inferior de cada intervalo:

```
{ _id: 0, count: 96 }
{ _id: 60, count: 224 }
{ _id: 90, count: 214 }
{ _id: 120, count: 216 }
{ _id: 150, count: 250 }
```

### Pipeline 4: resumo com `$facet`

1 documento, com um campo por cada resumo:

```
{
  total_and_avg: [ { total_films: 1000, avg_rental_rate: Decimal128('2.98') } ],
  count_by_rating: [
    { count: 178, rating: 'G' },
    { count: 210, rating: 'NC-17' },
    { count: 194, rating: 'PG' },
    { count: 223, rating: 'PG-13' },
    { count: 195, rating: 'R' }
  ],
  top_5_longest_films: [
    { title: 'CHICAGO NORTH', length: 185 },
    { title: 'CONTROL ANTHEM', length: 185 },
    { title: 'DARN FORRESTER', length: 185 },
    { title: 'GANGS PRIDE', length: 185 },
    { title: 'HOME PITY', length: 185 }
  ]
}
```

### Backup e restore

Output de `restore_mongo.sh`, sem as linhas de progresso do `mongorestore`. Cada linha da contagem mostra `pagila_docs / pagila_docs_restored`:

```
A restaurar mongo_pagila_docs_2026-11-03_214235.archive.gz para pagila_docs_restored
56406 document(s) restored successfully. 0 document(s) failed to restore.
coleção: pagila_docs / pagila_docs_restored
customers: 999 / 999
films: 1000 / 1000
rental_buckets: 1605 / 1605
rental_history: 997 / 997
rentals: 51805 / 51805
```

As contagens são iguais em todas as coleções. `rental_buckets` e `rental_history` aparecem porque também estão em `pagila_docs` e o backup copia a base inteira.
