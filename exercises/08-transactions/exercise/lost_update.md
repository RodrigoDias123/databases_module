# Lost update

Base `ex08` (cópia da Pagila com a coluna `customer.balance`, ver [README.md](README.md)). Duas sessões `psql` abertas na root do repositório com `psql -d ex08`. Antes de cada cenário: `UPDATE customer SET balance = 100 WHERE customer_id = 1;`.

Cada sessão quer levantar 10 ao cliente 1. Com 100 de saldo inicial, o saldo final correto é **80**.

## 1. Reprodução: ler e depois escrever o valor calculado

| Sessão A | Sessão B |
|----------|----------|
| `BEGIN;` | |
| `SELECT balance FROM customer WHERE customer_id = 1;` → 100.00 | |
| | `BEGIN;` |
| | `SELECT balance FROM customer WHERE customer_id = 1;` → 100.00 |
| `UPDATE customer SET balance = 90 WHERE customer_id = 1;` → `UPDATE 1` | |
| `COMMIT;` | |
| | `UPDATE customer SET balance = 90 WHERE customer_id = 1;` → `UPDATE 1` |
| | `COMMIT;` |
| `SELECT balance FROM customer WHERE customer_id = 1;` → **90.00** | |

Resultado: **90**. Saíram 20, mas o saldo só desceu 10. O levantamento de A perdeu-se.

**Porquê.** Em `READ COMMITTED` (o nível por omissão) as duas sessões leem 100, porque nenhuma escreveu ainda. Cada uma calcula `100 - 10 = 90` na aplicação (aqui, de cabeça) e escreve um valor fixo. O `UPDATE` de B não espera por nada (A já fez commit) e escreve `90` por cima do `90` de A. A base de dados não sabe que o `90` de B foi calculado a partir de um valor que entretanto mudou. O `CHECK (balance >= 0)` também não ajuda: 90 é um valor válido.

Reset: `UPDATE customer SET balance = 100 WHERE customer_id = 1;`

## 2. Correção 1: `UPDATE` atómico

Mesma intercalação, mas o cálculo passa para dentro do `UPDATE`:

| Sessão A | Sessão B |
|----------|----------|
| `BEGIN;` | |
| `SELECT balance FROM customer WHERE customer_id = 1;` → 100.00 | |
| | `BEGIN;` |
| | `SELECT balance FROM customer WHERE customer_id = 1;` → 100.00 |
| `UPDATE customer SET balance = balance - 10 WHERE customer_id = 1 AND balance >= 10 RETURNING balance;` → 90.00 | |
| | `UPDATE customer SET balance = balance - 10 WHERE customer_id = 1 AND balance >= 10 RETURNING balance;` → **fica à espera** |
| `COMMIT;` | |
| | (o `UPDATE` desbloqueia) → 80.00, `UPDATE 1` |
| | `COMMIT;` |
| `SELECT balance FROM customer WHERE customer_id = 1;` → **80.00** | |

Resultado: **80**.

**Porquê.** O `UPDATE` de A fica com o lock da linha até ao fim da transação, por isso o `UPDATE` de B espera. Quando A faz commit, o Postgres volta a ler a versão nova da linha (90), volta a avaliar o `WHERE` (`90 >= 10`, verdadeiro) e calcula `balance - 10` a partir de 90. O `SELECT` inicial de B viu 100, mas o valor não é usado. A condição `balance >= 10` faz com que um levantamento sem saldo atualize 0 linhas, em vez de violar o `CHECK`.

Reset: `UPDATE customer SET balance = 100 WHERE customer_id = 1;`

## 3. Correção 2: `SELECT ... FOR UPDATE`

Mesma intercalação, mantendo o padrão "ler e depois escrever", mas a leitura faz lock da linha:

| Sessão A | Sessão B |
|----------|----------|
| `BEGIN;` | |
| `SELECT balance FROM customer WHERE customer_id = 1 FOR UPDATE;` → 100.00 | |
| | `BEGIN;` |
| | `SELECT balance FROM customer WHERE customer_id = 1 FOR UPDATE;` → **fica à espera** |
| `UPDATE customer SET balance = 90 WHERE customer_id = 1;` → `UPDATE 1` | |
| `COMMIT;` | |
| | (o `SELECT` desbloqueia) → **90.00** |
| | `UPDATE customer SET balance = 80 WHERE customer_id = 1;` → `UPDATE 1` |
| | `COMMIT;` |
| `SELECT balance FROM customer WHERE customer_id = 1;` → **80.00** | |

Resultado: **80**.

**Porquê.** `FOR UPDATE` pede o mesmo lock de linha que um `UPDATE`. O `SELECT` de B não pode ler a linha até A terminar. Depois do commit de A, B lê a versão nova (90) e calcula `90 - 10 = 80`. A leitura e a escrita de cada sessão passam a ser feitas uma de cada vez.

Reset: `UPDATE customer SET balance = 100 WHERE customer_id = 1;`

## Comparação

| Cenário | Saldo final | B espera? |
|---------|------------:|-----------|
| Ler e escrever valor calculado | 90 | não |
| `UPDATE ... SET balance = balance - 10 ... AND balance >= 10` | 80 | sim, no `UPDATE` |
| `SELECT ... FOR UPDATE` + `UPDATE` | 80 | sim, no `SELECT` |

O `UPDATE` atómico é a melhor opção quando a regra cabe numa só instrução: uma ida à base de dados, e o lock dura o mínimo. O `FOR UPDATE` serve quando a aplicação tem de decidir algo com o valor lido antes de escrever (por exemplo, recusar com uma mensagem própria).
