# Challenge 04: CRUD, upsert and bulk data

Obrigatório.

## Enunciado

Write a Python seed script that adds 1 million rentals to Pagila in under 30 seconds, using `COPY`. Every row must be valid: existing inventory, customer and staff IDs, and a return date after the rental date. Run it twice on fresh copies of Pagila and prove the data is identical both times (for example, compare `md5(string_agg(...))` over the table ordered by primary key). Make the script idempotent: running it again on a database that already has the data must not create duplicates.

## Resposta

Script: [seed.py](seed.py). A partir da raiz do repositório, cria duas cópias limpas da Pagila e corre o script em cada uma:

```bash
./scripts/create-db.sh ex04_a --pagila --reset
./scripts/create-db.sh ex04_b --pagila --reset
cd exercises/04-crud/challenge
uv run seed.py ex04_a
uv run seed.py ex04_b
uv run seed.py ex04_a   # segunda vez: não insere nada
```

Resultado:

```
ex04_a: inserted 1,000,000 rentals
ex04_a: md5 of the seeded rows = e7893f4da44219cb924b18f0962fab3d
ex04_a: 13.5 s
ex04_b: inserted 1,000,000 rentals
ex04_b: md5 of the seeded rows = e7893f4da44219cb924b18f0962fab3d
ex04_b: 13.5 s
ex04_a: the 1,000,000 rentals are already there, nothing to do
ex04_a: md5 of the seeded rows = e7893f4da44219cb924b18f0962fab3d
ex04_a: 1.1 s
```

### Menos de 30 segundos com `COPY`

Os 13,5 s incluem gerar as linhas em Python, o `COPY`, as verificações das 3 FK e dos índices, e o cálculo do md5 no fim. As linhas são enviadas em blocos de 50 000 num único `COPY ... FROM STDIN`. Com `INSERT` linha a linha, cada linha seria uma ida e volta ao servidor.

### Todas as linhas são válidas

- `inventory_id`, `customer_id` e `staff_id` são escolhidos das listas de IDs lidas da própria base de dados.
- `return_date` fica entre 1 hora e 10 dias depois de `rental_date`.
- Cada `rental_date` é maior do que a anterior (passos de 120 s mais um valor aleatório menor do que 120 s), por isso o índice único `(rental_date, inventory_id, customer_id)` nunca é violado.

Verificação em `ex04_a`:

```sql
SELECT
  count(*) FILTER (WHERE return_date <= rental_date) AS return_antes_ou_igual,
  count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM inventory i WHERE i.inventory_id = r.inventory_id)) AS inventory_invalido,
  count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM customer c WHERE c.customer_id = r.customer_id)) AS customer_invalido,
  count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM staff s WHERE s.staff_id = r.staff_id)) AS staff_invalido
FROM rental r WHERE rental_id >= 1000001;
-- 0 | 0 | 0 | 0
```

As FK também já o garantem: se um ID não existisse, o `COPY` falhava e não ficava nada inserido.

### Os dados são idênticos nas duas execuções

O gerador aleatório usa uma seed fixa (`random.Random(42)`) e as listas de IDs são lidas com `ORDER BY`, por isso as escolhas são sempre as mesmas. As colunas que o PostgreSQL preencheria com valores diferentes em cada execução também são definidas pelo script:

- `rental_id`: de 1 000 001 a 2 000 000, em vez de usar a sequence;
- `uuid`: gerado a partir do mesmo gerador, em vez de `uuidv7()`;
- `last_update`: data fixa, em vez de `now()`.

Comparação da tabela inteira (as linhas originais mais o seed):

```sql
SELECT count(*), md5(string_agg(r::text, ',' ORDER BY rental_id)) FROM rental r;
-- ex04_a: 1051805 | 679918c2c9ce0ed1c9d413d5fdb05814
-- ex04_b: 1051805 | 679918c2c9ce0ed1c9d413d5fdb05814
```

### Idempotente

Tudo corre numa só transação. Antes de inserir, o script conta as linhas no intervalo de IDs do seed:

- 0 linhas: insere as 1 000 000;
- 1 000 000 linhas: não faz nada;
- outro número qualquer: para com erro (alguém mexeu nos dados à mão).

Como a transação é tudo ou nada, um seed interrompido a meio não deixa linhas para trás. O `LOCK TABLE rental IN SHARE ROW EXCLUSIVE MODE` impede que duas execuções ao mesmo tempo vejam as duas 0 linhas e insiram as duas. A segunda espera pela primeira e depois já encontra os dados. Se o seed fosse repetido sem esta verificação, a PK `rental_id` rejeitava o `COPY` inteiro, mas o script terminaria com erro em vez de sair limpo.
