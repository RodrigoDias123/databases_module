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

## Resolução

### Como correr

A coleção `rentals` tem de estar carregada em `pagila_docs` (exercício da sessão 13). O relatório cria um índice em `rentals.rental_date` (se ainda não existir), para cada execução ler só os alugueres dos dias a recalcular.

```bash
# a partir da raiz do repositório
set -a; . ./.env; set +a
cd exercises/14-pipelines/challenge

# Atualiza o relatório. Sem alugueres novos, não escreve nada.
mongosh "$MONGO_URL" --quiet --file daily_revenue.js

# Corre o teste.
mongosh "$MONGO_URL" --quiet --file test_daily_revenue.js
```

O teste começa por apagar `daily_revenue` e `report_state`. No fim, mesmo que falhe, apaga os 5 alugueres de teste e volta a apagar essas duas coleções, porque ficariam com dados de alugueres que já não existem. Para voltar a ter o relatório depois do teste, corre outra vez o `daily_revenue.js`.

### Output do teste

```text
1. Primeira execução, sobre a coleção completa
daily_revenue: 1476 dia(s) recalculado(s), marca de água em 87559
ok: daily_revenue conta os 51805 alugueres
ok: 2026-07-28 já tem alugueres
ok: 2026-07-29 ainda não existe
ok: marca de água em 87559

2. Inserir 5 alugueres novos
ok: rentals tem mais 5 documentos

3. Segunda execução
daily_revenue: 2 dia(s) recalculado(s), marca de água em 87564
ok: só recalculou 2026-07-28 e 2026-07-29
ok: só esses 2 dias mudaram
ok: 2026-07-28 tem mais 3 alugueres
ok: 2026-07-28 tem mais 8.97 de receita
ok: 2026-07-29 tem 2 alugueres e 6.98 de receita
ok: marca de água em 87564

4. Comparar com um recálculo completo
ok: daily_revenue é igual ao recálculo completo (1477 dias)

5. Terceira execução
daily_revenue: sem alugueres novos, nada a fazer
ok: não recalculou nenhum dia
ok: daily_revenue não mudou
ok: marca de água não mudou

TESTE PASSOU
limpeza: 5 alugueres de teste apagados, rentals tem 51805 documentos
```

### Porque é que recalcular o dia inteiro é mais seguro do que somar os valores novos

Recalcular pode repetir-se sem estragar o total. Somar não pode.

Imagina que uma execução grava o resultado em `daily_revenue` e falha antes de mover a marca de água. A execução seguinte volta a processar os mesmos alugueres:

- **A somar:** os mesmos valores entram no total pela segunda vez, e a receita fica errada sem nenhum aviso.
- **A recalcular:** o total volta a ser calculado a partir de todos os alugueres do dia e substitui o anterior, por isso fica certo.
