# Exercício 16: Redis II, source of truth, rebuild and persistence

## Enunciado

Folder: `exercises/16-consistency/exercise/`

**Goal.** Treat Redis as derived data: rebuild it from PostgreSQL, verify it, and choose its persistence.

**Starting point.** A fresh copy of Pagila and a uv project:

```bash
./scripts/create-db.sh ex16 --pagila --reset
uv init --bare
uv add redis "psycopg[binary]"
```

Use Redis logical database 1 for this exercise (end `REDIS_URL` with `/1`), so that `FLUSHDB` there does not delete the keys of other exercises.

**Tasks.**

1. `rebuild.py` creates, for every customer with rentals, the set `customer:{customer_id}:categories` with the names of the categories of every film the customer has rented (a film can have several categories). It reads PostgreSQL with one query and writes Redis with one pipeline. Each set is built in a temporary key and renamed at the end, so that readers never see a half-built set. Expected: 997 sets (customers 647 and 978 have no rentals).
2. Run `FLUSHDB` on database 1, run `rebuild.py`, and count the keys with `SCAN` (not `KEYS`).
3. `verify.py` compares every set with PostgreSQL, size and members, and also reports any `customer:*:categories` key for a customer who should not have one. It prints every difference and exits with 1 if there is any, 0 otherwise. Show it exiting with 1 after `SREM customer:1:categories Action`, with 1 after `SADD customer:647:categories Fake`, and with 0 after running `rebuild.py` again.
4. Fill a table for every key pattern of exercises 15 and 16 (viewed films, film cache, lock, rate limit, categories) with: its class (source of truth, derived or ephemeral), what is lost if Redis loses it, and how it comes back.
5. Choose one configuration for the Redis instance (`appendonly`, `appendfsync`, `maxmemory`, `maxmemory-policy`) and justify it against the table of task 4. `maxmemory-policy` applies to the whole instance, not to one key, so explain the trade-off and when you would use two Redis instances instead. `docker-compose.redis-aof.yml` in this repository turns on AOF; read the warning in `sessions/16-redis-consistency/` before using it.

**Deliverables.**

- `rebuild.py`, `verify.py`, `pyproject.toml`.
- `README.md` with the commands, the output of tasks 2 and 3, the table of task 4, and the configuration and justification of task 5.

**Done when.** The rebuild creates 997 sets in one query and one pipeline, `verify.py` detects both changes and passes after the rebuild, and every choice in tasks 4 and 5 is justified.

## Challenge (opcional, em `challenge/`)

Enunciado completo em [challenge/README.md](../challenge/README.md).

## Checklist

- [x] `rebuild.py`: 997 sets, one query, one pipeline, temporary key + rename
- [x] `FLUSHDB` + rebuild + count with `SCAN`
- [x] `verify.py`: exits 1 after `SREM` and after `SADD` on customer 647, 0 after rebuild
- [x] Table of every key pattern of ex. 15 and 16: class, what is lost, how it comes back
- [x] Redis configuration (`appendonly`, `appendfsync`, `maxmemory`, `maxmemory-policy`) justified

## Resolução

Ficheiros entregues:

- [rebuild.py](rebuild.py): reconstrói os 997 sets `customer:{customer_id}:categories` com uma query e um pipeline.
- [verify.py](verify.py): compara cada set com o PostgreSQL e sai com 1 se houver diferenças.
- [categories.py](categories.py): o que os dois partilham (ligações, nome da chave, a query e o `SCAN`).
- [pyproject.toml](pyproject.toml) e `uv.lock`; [.env.example](.env.example) com `DATABASE_URL` para `ex16` e `REDIS_URL` a acabar em `/1`.

### Como correr

```bash
# a partir da raiz do repositório
./scripts/create-db.sh ex16 --pagila --reset
cd exercises/16-consistency/exercise
uv sync
cp .env.example .env   # e trocar as passwords pelas do .env da raiz
unset REDIS_URL DATABASE_URL   # o devcontainer exporta REDIS_URL para a base 0
uv run --env-file .env python rebuild.py
uv run --env-file .env python verify.py
```

O `--env-file` não substitui variáveis que já existam na shell. O devcontainer exporta `REDIS_URL=.../0`, por isso sem o `unset` os scripts escreveriam na base 0, a das outras sessões. Nos comandos `redis-cli` abaixo, `-n 1` escolhe a base 1 (a password vai em `REDISCLI_AUTH`).

### Tarefa 1: `rebuild.py`

A query junta `rental → inventory → film_category → category` e devolve um par `(customer_id, name)` por cliente e categoria (`DISTINCT`, porque o mesmo cliente aluga muitos filmes da mesma categoria). Um filme com várias categorias dá várias linhas, por isso todas entram no set. Os clientes sem alugueres não aparecem na query e por isso não têm set.

O pipeline (`transaction=False`, um só round trip) faz, para cada cliente:

```
DEL    customer:{id}:categories:tmp
SADD   customer:{id}:categories:tmp  Action Animation ...
RENAME customer:{id}:categories:tmp  customer:{id}:categories
```

O `RENAME` substitui o set antigo num só passo: quem lê vê o set antigo ou o novo, nunca um set a meio. A chave temporária acaba em `:tmp`, por isso não corresponde ao padrão `customer:*:categories` e o `verify.py` nunca a vê. O pipeline não precisa de `MULTI/EXEC`: cada `RENAME` já é atómico, e um `MULTI` com 3000 comandos bloquearia o Redis durante toda a reconstrução.

Antes do pipeline, um `SCAN` procura chaves `customer:*:categories` que a query não explica (como um set para o cliente 647); o mesmo pipeline apaga-as. Sem isto, a última verificação da tarefa 3 continuaria a falhar depois do rebuild.

### Tarefa 2: `FLUSHDB`, rebuild e contagem com `SCAN`

```
$ redis-cli -n 1 FLUSHDB
OK
$ redis-cli -n 1 DBSIZE
0
$ uv run --env-file .env python rebuild.py
rebuilt 997 sets, deleted 0 stale keys
$ redis-cli -n 1 --scan --pattern 'customer:*:categories' | wc -l
997
$ redis-cli -n 1 EXISTS customer:647:categories customer:978:categories
0
$ redis-cli -n 1 SCARD customer:1:categories
16
```

`--scan` percorre as chaves com `SCAN` aos bocados, sem bloquear o servidor; `KEYS` percorreria as chaves todas num só comando e bloquearia o Redis enquanto isso. Os clientes 647 e 978 não têm alugueres e não têm set.

### Tarefa 3: `verify.py`

O `verify.py` faz a mesma query, lê todos os sets esperados num pipeline (`SMEMBERS`), e encontra com `SCAN` as chaves existentes. Para cada set esperado reporta: chave em falta, tamanho diferente, membros em falta e membros a mais; e reporta cada chave existente que não devia existir.

```
$ uv run --env-file .env python verify.py
checked 997 sets, 997 keys in Redis: OK
exit code: 0
$ redis-cli -n 1 SREM customer:1:categories Action
1
$ uv run --env-file .env python verify.py
customer:1:categories: size 15, expected 16
customer:1:categories: missing members ['Action']
checked 997 sets, 997 keys in Redis: 2 differences
exit code: 1
$ redis-cli -n 1 SADD customer:647:categories Fake
1
$ uv run --env-file .env python verify.py
customer:1:categories: size 15, expected 16
customer:1:categories: missing members ['Action']
customer:647:categories: should not exist (1 members)
checked 997 sets, 998 keys in Redis: 3 differences
exit code: 1
$ uv run --env-file .env python rebuild.py
rebuilt 997 sets, deleted 1 stale keys
exit code: 0
$ uv run --env-file .env python verify.py
checked 997 sets, 997 keys in Redis: OK
exit code: 0
```

### Tarefa 4: classe de cada padrão de chave (exercícios 15 e 16)

- **Fonte de verdade**: o dado só existe no Redis; se se perder, não há de onde o recuperar.
- **Derivado**: é uma cópia ou um cálculo sobre o PostgreSQL; pode ser reconstruído.
- **Efémero**: só tem sentido durante pouco tempo (segundos ou minutos); perdê-lo tem um efeito passageiro.

| Padrão de chave | Classe | O que se perde se o Redis o perder | Como volta |
| --- | --- | --- | --- |
| `customer:{customer_id}:viewed` (ex. 15) | Fonte de verdade | O histórico dos 20 filmes vistos recentemente; o PostgreSQL não regista visualizações | Não volta: só se refaz com novas visualizações. O TTL de 30 dias torna a perda tolerável, mas não a recupera |
| `cache:film:{film_id}` (ex. 15) | Derivado | Nada; só o próximo `get_film` é mais lento e vai ao PostgreSQL | Sozinho: o próximo `get_film` é um miss e volta a guardar a cópia (cache-aside) |
| `lock:refresh:monthly_revenue`, `lock:demo` (ex. 15) | Efémero | A exclusão mútua: outro processo pode fazer o refresh ao mesmo tempo (trabalho a dobrar; o `REFRESH ... CONCURRENTLY` continua correto) | Sozinho: o próximo `refresh.py` volta a adquirir o lock |
| `ratelimit:{customer_id}:{minuto}` (ex. 15) | Efémero | Os contadores do minuto atual: um cliente pode fazer até mais 10 pedidos nesse minuto | Sozinho: o próximo `INCR` começa em 1, e no minuto seguinte a chave seria nova de qualquer forma |
| `ratelimit:fixed:…`, `ratelimit:sliding:{customer_id}` (challenge 15) | Efémero | Os pedidos dos últimos 60 s: o limite recomeça do zero | Sozinho: em 60 s a janela volta a estar completa |
| `customer:{customer_id}:categories` (ex. 16) | Derivado | As categorias de cada cliente até ao rebuild; quem lê vê sets vazios | `rebuild.py` (uma query, menos de 1 s), confirmado com `verify.py` |
| `customer:{customer_id}:categories:tmp` (ex. 16) | Efémero | Um rebuild interrompido a meio; o set real fica com a versão antiga | Correr `rebuild.py` outra vez (o `DEL` inicial limpa a temporária) |

### Tarefa 5: configuração do Redis

O servidor do curso usa hoje (`CONFIG GET`): `appendonly no`, `save 3600 1 300 100 60 10000` (só RDB), `maxmemory 0` (sem limite) e `maxmemory-policy noeviction`. A configuração que escolho:

```yaml
command: ["redis-server", "--requirepass", "${REDIS_PASSWORD}",
          "--appendonly", "yes", "--appendfsync", "everysec",
          "--maxmemory", "256mb", "--maxmemory-policy", "noeviction"]
```

- **`appendonly yes`.** A tabela tem uma fonte de verdade, `customer:{id}:viewed`. Com RDB só, um crash perde tudo o que mudou desde o último snapshot (até uma hora, com as regras `save` atuais), e esse histórico não volta de lado nenhum. Os derivados e os efémeros não precisariam de persistência.
- **`appendfsync everysec`.** Perde no máximo cerca de um segundo de escritas num crash. Para um histórico de visualizações isso chega; `always` faria um `fsync` por escrita, um custo grande para um dado que já expira sozinho ao fim de 30 dias. `no` deixaria o sistema operativo decidir quando escrever (cerca de 30 s no Linux).
- **`maxmemory 256mb`.** Os dados são pequenos: o Redis usa 2,3 MB, cada set de categorias ocupa cerca de 180 bytes (997 sets são cerca de 0,2 MB), e o histórico tem no máximo 20 filmes por cliente. 256 MB deixa folga e impede que o Redis use toda a memória da máquina e seja morto pelo OOM killer do sistema operativo.
- **`maxmemory-policy noeviction`.** Quando a memória enche, as escritas falham com um erro em vez de o Redis apagar chaves em silêncio. O ideal seria uma política por chave, mas a política é de toda a instância:
  - `allkeys-lru` serviria à cache, mas podia apagar um histórico (perdido para sempre) ou um set de categorias (o `verify.py` falharia sem ninguém o ter apagado, e os leitores veriam um set vazio).
  - `volatile-lru` só apaga chaves com TTL. Protege os sets de categorias, mas `customer:{id}:viewed` tem TTL de 30 dias e podia ser apagado; e apagar um `lock:` antes do tempo quebra a exclusão mútua.
  - Com `noeviction`, a aplicação tem de tratar o erro: um `SET` da cache que falha pode ser ignorado (o `get_film` devolve o valor lido do PostgreSQL); um `INCR` do rate limit que falha tem de decidir se deixa passar o pedido ou não.

**Quando usar duas instâncias.** Se a cache crescer até precisar de evição (muitos filmes, respostas maiores), a política única deixa de servir: ou se perde a cache por falta de memória (`noeviction`) ou se arrisca a fonte de verdade (`allkeys-lru`). Aí separava em duas instâncias:

| Instância | Chaves | Configuração |
| --- | --- | --- |
| Cache | `cache:film:*` | `allkeys-lru`, `maxmemory` à medida da cache, sem persistência (`appendonly no`, `save ""`): depois de um restart enche-se sozinha |
| Dados | `customer:*:viewed`, `customer:*:categories`, `lock:*`, `ratelimit:*` | `appendonly yes`, `appendfsync everysec`, `noeviction` |

Os sets de categorias são derivados e poderiam ir para a instância de cache, mas ficam na de dados: se fossem apagados por evição, os leitores veriam sets vazios até ao próximo rebuild. As bases lógicas (`/0`, `/1`) não resolvem isto, porque partilham a mesma memória, a mesma política e a mesma persistência.

Não liguei o `docker-compose.redis-aof.yml` neste exercício: recria o contentor Redis partilhado por todos os projetos do repositório, e a configuração acima é a recomendação para produção, não algo que o exercício precise para correr.
