# Deadlock

Base `ex08`, duas sessões `psql -d ex08`. Saldos iniciais: clientes 1 e 2 com 100. A sessão A transfere 10 do cliente 1 para o 2, a sessão B transfere 10 do cliente 2 para o 1. Cada uma atualiza primeiro a sua conta de origem, por isso fazem lock das linhas por ordem inversa.

## Reprodução

| Sessão A (pid 2276) | Sessão B (pid 2275) |
|---------------------|---------------------|
| `BEGIN;` | |
| `UPDATE customer SET balance = balance - 10 WHERE customer_id = 1;` → `UPDATE 1` (lock da linha 1) | |
| | `BEGIN;` |
| | `UPDATE customer SET balance = balance - 10 WHERE customer_id = 2;` → `UPDATE 1` (lock da linha 2) |
| `UPDATE customer SET balance = balance + 10 WHERE customer_id = 2;` → **fica à espera de B** | |
| | `UPDATE customer SET balance = balance + 10 WHERE customer_id = 1;` → **fica à espera de A** |
| (≈1 s depois) `ERROR:  deadlock detected` | |
| | (o `UPDATE` desbloqueia) → `UPDATE 1` |
| `COMMIT;` → `ROLLBACK` | |
| | `COMMIT;` → `COMMIT` |
| `SELECT customer_id, balance FROM customer WHERE customer_id IN (1, 2) ORDER BY customer_id;` → 1: **110.00**, 2: **90.00** | |

Os pids foram obtidos com `SELECT pg_backend_pid();` em cada sessão.

Mensagem completa recebida pela sessão A:

```
ERROR:  deadlock detected
DETAIL:  Process 2276 waits for ShareLock on transaction 61845; blocked by process 2275.
Process 2275 waits for ShareLock on transaction 61844; blocked by process 2276.
HINT:  See server log for query details.
CONTEXT:  while locking tuple (2,20) in relation "customer"
```

## A mensagem, linha a linha

- **`ERROR:  deadlock detected`**. O Postgres encontrou um ciclo de esperas e cancelou uma das transações para o desfazer. A vítima foi A: a instrução falhou e a transação ficou abortada. Por isso o `COMMIT` seguinte respondeu `ROLLBACK` e o `-10` que A já tinha feito ao cliente 1 também foi desfeito. A vítima é o processo que corre o detetor: cada processo que espera por um lock há mais de `deadlock_timeout` (1 s por omissão) procura um ciclo. A começou a esperar primeiro, por isso o seu temporizador acabou primeiro.
- **`DETAIL:  Process 2276 waits for ShareLock on transaction 61845; blocked by process 2275.`** A (2276) espera por B (2275). O Postgres não guarda os locks de linha numa tabela de locks: marca a linha com o id da transação que a alterou (`xmax`). Quem quer essa linha espera que essa transação termine, e fá-lo pedindo um `ShareLock` sobre o id da transação (61845 é a transação de B). Cada transação tem um `ExclusiveLock` sobre o seu próprio id até fazer commit ou rollback, por isso o `ShareLock` só é concedido quando B terminar.
- **`Process 2275 waits for ShareLock on transaction 61844; blocked by process 2276.`** A segunda aresta do ciclo: B (2275) espera pelo fim da transação 61844, que é a de A. Juntas, as duas linhas mostram o ciclo A → B → A: nenhuma pode avançar sem a outra terminar.
- **`HINT:  See server log for query details.`** O cliente não recebe o texto das instruções da outra sessão (pode ter dados de outro utilizador). O log do servidor tem as instruções dos dois processos:

  ```
  ERROR:  deadlock detected
  DETAIL:  Process 2276 waits for ShareLock on transaction 61845; blocked by process 2275.
          Process 2275 waits for ShareLock on transaction 61844; blocked by process 2276.
          Process 2276: UPDATE customer SET balance = balance + 10 WHERE customer_id = 2;
          Process 2275: UPDATE customer SET balance = balance + 10 WHERE customer_id = 1;
  HINT:  See server log for query details.
  CONTEXT:  while locking tuple (2,20) in relation "customer"
  STATEMENT:  UPDATE customer SET balance = balance + 10 WHERE customer_id = 2;
  ```

  (obtido com `docker compose logs postgres`).
- **`CONTEXT:  while locking tuple (2,20) in relation "customer"`**. O que A estava a fazer quando foi cancelada: a tentar o lock do tuplo `(2,20)` da tabela `customer`, ou seja, a página 2, posição 20 (o `ctid`). É a versão da linha do cliente 2 que B tinha alterado.

O resultado final (110 / 90) mostra que só a transferência de B foi aplicada. A transferência de A foi toda desfeita: nunca fica aplicada só metade de uma transferência. A aplicação tem de apanhar o erro (SQLSTATE `40P01`) e repetir a transação.

## Como prevenir

1. **Fazer lock das linhas sempre pela mesma ordem.** Por exemplo, por `customer_id` crescente, seja qual for o sentido da transferência. Com a mesma ordem, a segunda transação fica à espera logo na primeira linha e não chega a ter um lock de que a outra precise. Pode ser feito com um lock prévio ordenado:

   ```sql
   BEGIN;
   SELECT 1 FROM customer WHERE customer_id IN (1, 2) ORDER BY customer_id FOR UPDATE;
   UPDATE customer SET balance = balance - 10 WHERE customer_id = 2;
   UPDATE customer SET balance = balance + 10 WHERE customer_id = 1;
   COMMIT;
   ```

   Verificação com as duas sessões a atualizar o cliente 1 primeiro e depois o 2:

   | Sessão A | Sessão B |
   |----------|----------|
   | `BEGIN;` | |
   | `UPDATE customer SET balance = balance - 10 WHERE customer_id = 1;` → `UPDATE 1` | |
   | | `BEGIN;` |
   | | `UPDATE customer SET balance = balance + 10 WHERE customer_id = 1;` → **fica à espera de A** |
   | `UPDATE customer SET balance = balance + 10 WHERE customer_id = 2;` → `UPDATE 1` | |
   | `COMMIT;` | |
   | | (desbloqueia) → `UPDATE 1` |
   | | `UPDATE customer SET balance = balance - 10 WHERE customer_id = 2;` → `UPDATE 1` |
   | | `COMMIT;` |
   | Saldos finais: 1 → 100.00, 2 → 100.00 | |

   Sem deadlock: B só espera, e as duas transferências são aplicadas.
2. **Transações curtas.** Nada de esperas pelo utilizador ou chamadas a outros serviços com locks na mão. Quanto menos tempo os locks durarem, menos provável é haver um ciclo.
3. **Repetir em caso de erro.** Mesmo com cuidado, um deadlock pode acontecer (por exemplo, com foreign keys ou triggers). A aplicação deve apanhar o `40P01` e repetir a transação do início, como faz com o `40001`.
4. Opcionalmente, `SET lock_timeout = '2s'` para que uma espera longa falhe cedo em vez de bloquear o pedido.
