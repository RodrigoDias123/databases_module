# Challenge 13: MongoDB I, documents, CRUD and validation

Opcional.

## Enunciado

Folder: `exercises/13-mongo/challenge/`

**Goal.** Store a history that grows without limit with the bucket pattern, and measure the difference.

**Starting point.** The `rentals` collection of the exercise above (or `load.py` run again).

**Tasks.**

1. Design the collection `rental_buckets`: each document holds at most 50 rentals of one customer, with `customer_id`, a sequence number `seq`, a `count` and an array `rentals`.
2. Write `add_rental(customer_id, rental)` that adds a rental to the customer's open bucket, or opens a new one, with a single `updateOne` with `upsert: true` and a filter on `count`. Explain what makes it safe when two calls for the same customer run at the same time, and what you need (for example a unique index) to keep it safe.
3. Fill `rental_buckets` from `rentals` with `add_rental`, in `rental_date` order.
4. Build a second collection `rental_history` with one document per customer embedding every rental.
5. For customer 380 (97 rentals, the most in Pagila), compare the document sizes (`Object.bsonsize`) and the time to read the 20 most recent rentals from each collection.

**Deliverables.**

- `buckets.py` (or `.js`) with the functions and the loading code.
- `README.md` with the design, the explanation of task 2, and the sizes and times of task 5.

**Done when.** No bucket has more than 50 rentals, customer 380 has two buckets (50 and 47 rentals), and the README explains when the bucket pattern pays off.

## Checklist

- [x] `rental_buckets`: no máximo 50 alugueres por bucket
- [x] `add_rental`: um único `updateOne` com `upsert: true` e filtro em `count`
- [x] `rental_buckets` cheia a partir de `rentals`, por `rental_date`
- [x] `rental_history`: um documento por cliente
- [x] Cliente 380: dois buckets (50 e 47 alugueres), tamanhos e tempos comparados
- [x] README explica quando compensa usar o bucket pattern

## Resolução

Ficheiros entregues:

- [buckets.py](buckets.py): as funções e o código de carregamento.
- [pyproject.toml](pyproject.toml) e `uv.lock`.

### Como correr

```bash
# a partir da raiz do repositório, com `rentals` já carregada (exercise/load.py)
cd exercises/13-mongo/challenge
uv sync
uv run --env-file ../../../.env python buckets.py
```

### Tarefa 1: desenho

Cada documento de `rental_buckets` guarda até 50 alugueres de um cliente:

```json
{
  "_id": { "$oid": "..." },
  "customer_id": 380,
  "seq": 1,
  "count": 47,
  "rentals": [
    { "_id": "...", "customer_id": 380, "film_id": "...", "title": "...", "rental_date": { "$date": "..." } }
  ]
}
```

(O aluguer do exemplo está encurtado: cada elemento de `rentals` é o documento completo de `rentals`.)

- `customer_id`: o dono do bucket, e o campo por onde se procura.
- `seq`: a ordem do bucket dentro do cliente, a começar em 0. Permite ler primeiro o mais recente.
- `count`: quantos alugueres tem o bucket. É o que `add_rental` usa para saber se ainda há espaço, sem ter de calcular o tamanho do array.
- `rentals`: os alugueres, do mais antigo para o mais recente, porque são acrescentados por ordem de `rental_date`.

O índice único `{customer_id: 1, seq: 1}` serve as leituras por cliente e por `seq`, e protege a abertura de buckets (ver a tarefa 2).

### Tarefa 2: `add_rental`

```python
db.rental_buckets.update_one(
    {"customer_id": customer_id, "count": {"$lt": 50}},
    {"$push": {"rentals": rental}, "$inc": {"count": 1}, "$setOnInsert": {"seq": seq}},
    upsert=True,
)
```

**O que torna o limite de 50 seguro.** Um `updateOne` é atómico ao nível do documento: o filtro e as alterações acontecem como uma só operação. Se duas chamadas disputam um bucket com 49 alugueres, só uma o apanha com `count` 49. A outra volta a avaliar o filtro, vê `count` 50, já não encontra bucket aberto e faz o upsert de um novo. Por isso, verificar o limite no filtro é seguro, e ler o bucket antes e só depois escrever não seria: duas chamadas podiam ler 49 e fazer ambas `$push`, deixando o bucket com 51.

**O que é preciso para continuar seguro.** A atomicidade cobre um documento, não a abertura de um documento novo. Se não houver bucket aberto, duas chamadas podem fazer upsert ao mesmo tempo e, sem mais nada, criar dois buckets abertos para o mesmo cliente. É para isso que serve o índice único `{customer_id: 1, seq: 1}`:

1. Antes do update, `add_rental` conta os buckets do cliente para saber o `seq` de um eventual bucket novo.
2. As duas chamadas tentam inserir com o mesmo `seq`, e o índice só aceita uma.
3. A outra recebe `DuplicateKeyError`, tenta de novo e entra no bucket acabado de criar.

Essa contagem é uma leitura à parte, mas a segurança não depende dela: se estiver desatualizada, o pior que acontece é o índice rejeitar o insert e a chamada repetir-se. O custo é uma ida extra à base de dados por cada aluguer.

**Limitação.** Com chamadas em simultâneo, dois alugueres quase ao mesmo tempo podem ficar no array por uma ordem diferente da de `rental_date`. No carregamento isto não acontece, porque as chamadas são feitas uma a uma e por ordem.

**Teste.** 1030 chamadas a `add_rental` em 32 threads, para o mesmo cliente, numa base temporária:

```
seqs: [0, 1, 2, ..., 20]
counts: [50, 50, ..., 50, 30]
count == len(rentals): True
nada perdido nem duplicado: True
máximo: 50
```

### Tarefas 3 e 4: carregamento

`rental_buckets` é cheia com `add_rental`, percorrendo `rentals` por `rental_date` (e `_id` em caso de empate). `rental_history` é criada com uma agregação (`$sort`, `$group`, `$out`) em que o `_id` é o `customer_id`.

```
rental_buckets: 1605 documentos
maior bucket: 50 alugueres
alugueres nos buckets: 51805 (rentals: 51805)
cliente 380: buckets com [50, 47] alugueres
rental_history: 997 documentos
```

`rental_history` tem 997 documentos, e não 999 como `customers`, porque 2 clientes não têm alugueres.

### Tarefa 5: cliente 380

| Coleção | Documentos | Tamanho (BSON) | Tempo a ler os 20 mais recentes |
|---------|------------|----------------|---------------------------------|
| `rental_buckets` | 2 (50 e 47 alugueres) | 10 418 e 9652 bytes | 0,210 ms |
| `rental_history` | 1 (97 alugueres) | 19 962 bytes | 0,148 ms |

Os tempos são a mediana de 500 leituras, numa base local, e por isso valem como comparação e não como valores absolutos. Os tamanhos deram o mesmo com `len(bson.encode(doc))` e com `$bsonSize` no servidor. No `mongosh` 2.13 usado aqui, `Object.bsonsize` não existe; a função disponível é `bsonsize`.

As duas leituras devolvem os mesmos 20 alugueres, e ambas usam `$slice` para só trazer esses 20. Em `rental_buckets` basta o último bucket, porque tem 47 alugueres.

**Leitura dos resultados.** Com 97 alugueres, o documento único foi um pouco mais rápido, e a diferença (0,06 ms) não tem importância prática. Com um histórico desta dimensão, os buckets não trazem ganho de velocidade. O ganho está no tamanho: cada bucket fica limitado a cerca de 10 KB, enquanto o documento de `rental_history` cresce com cada aluguer.

### Quando compensa o bucket pattern

**Compensa** quando o histórico cresce sem limite e o que se lê é sobretudo a parte recente:

- O tamanho de cada documento fica limitado. A cerca de 206 bytes por aluguer, um documento único chegaria ao limite de 16 MB perto dos 80 000 alugueres, e tornava-se cada vez mais pesado muito antes disso.
- Ler os mais recentes toca em poucos buckets, seja qual for o tamanho total do histórico.
- Acrescentar um aluguer altera um documento pequeno, em vez de um cada vez maior.

**Não compensa** quando o histórico é pequeno ou tem um limite conhecido, como em Pagila, onde o maior cliente tem 97 alugueres e 20 KB. Aí, o documento único é mais simples e foi até um pouco mais rápido. Também compensa menos quando se lê quase sempre o histórico inteiro, porque é preciso juntar vários documentos, ou quando se filtra e agrega por outros campos, caso em que uma coleção com um documento por aluguer, como `rentals`, serve melhor.

O preço do padrão é mais lógica na aplicação: manter `count` e `seq`, tratar o `DuplicateKeyError` e, na leitura, percorrer vários buckets.
