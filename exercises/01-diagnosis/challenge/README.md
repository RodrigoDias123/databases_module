# Challenge 01: Database engines and diagnosis

Obrigatório.

## Enunciado

Folder: `exercises/01-diagnosis/challenge/`

**Goal.** Show with numbers why a database engine handles concurrent writes and a JSON file does not.

**Starting point.** Create an empty database and a uv project:

```bash
./scripts/create-db.sh ch01
uv init --bare
uv add "psycopg[binary]"
```

Use this table in `ch01` database (create if it doesn't exist):

```sql
CREATE TABLE record (worker integer NOT NULL, n integer NOT NULL);
```

**Tasks.**

1. `json_race.py`: create `records.json` containing `[]`. Start 10 processes with `multiprocessing`. Each process appends 1,000 records of the form `{"worker": <process number>, "n": <0 to 999>}`, one at a time: read the whole file, append one record, write the whole file back. Do not use any file lock. A process may read a half-written file that is not valid JSON: catch that error, count it as a failed write and carry on. At the end, print how many records the file holds and how many writes failed.
2. `pg_race.py`: start 10 processes, each with its own connection, each inserting the same 1,000 records into `record` with one `INSERT` per record. At the end, print `SELECT count(*) FROM record`.
3. Run each script 3 times (empty the file and the table before each run).

**Deliverables.**

- `json_race.py`, `pg_race.py`, `pyproject.toml`.
- `README.md` with the commands to run both scripts, the count of each of the 3 runs of each script, and an explanation of a few sentences of why the numbers differ.

**Done when.** The JSON count is below 10,000 and changes between runs, the PostgreSQL count is exactly 10,000 in every run, and the explanation names the cause (lost updates from concurrent read-modify-write, and how the engine avoids them).

## Resposta

Ficheiros entregues: [json_race.py](json_race.py), [pg_race.py](pg_race.py) e [pyproject.toml](pyproject.toml).

A partir da raiz do repositório, cria a base de dados e corre cada script três vezes:

```bash
./scripts/create-db.sh ch01
cd exercises/01-diagnosis/challenge
uv run json_race.py   # recria records.json com [] antes de começar
uv run pg_race.py     # cria a tabela record se não existir e faz TRUNCATE antes de começar
```

Cada script esvazia o ficheiro ou a tabela no início, por isso basta corrê-lo outra vez para repetir a medição. O `pg_race.py` liga-se a `host=$PGHOST dbname=ch01` (com `PGUSER` e `PGPASSWORD` do ambiente), ou a `DATABASE_URL` se estiver definida.

Output de `json_race.py`:

```
== execução 1
records in file: 999 / 10000
failed writes:   12
== execução 2
records in file: 1010 / 10000
failed writes:   38
== execução 3
records in file: 1018 / 10000
failed writes:   15
```

Output de `pg_race.py`:

```
== execução 1
SELECT count(*) FROM record: 10000 / 10000
== execução 2
SELECT count(*) FROM record: 10000 / 10000
== execução 3
SELECT count(*) FROM record: 10000 / 10000
```

| Execução | JSON: registos no ficheiro | JSON: escritas falhadas | PostgreSQL: `count(*)` |
|----------|---------------------------:|------------------------:|-----------------------:|
| 1 | 999 | 12 | 10 000 |
| 2 | 1 010 | 38 | 10 000 |
| 3 | 1 018 | 15 | 10 000 |

O ficheiro JSON fica com cerca de 10 % dos registos, e o número muda de execução para execução. O PostgreSQL grava os 10 000 todas as vezes, e ainda é cerca de 5 vezes mais rápido (0,6 a 1 s contra 5 s).

### Porque é que os números são diferentes

No JSON, cada escrita é um ciclo de ler, modificar e escrever o ficheiro inteiro, sem nenhum controlo de concorrência. Quando dois processos leem a mesma versão do ficheiro, cada um acrescenta o seu registo à sua cópia em memória, e o que escreve em último lugar apaga o registo do outro (*lost update*). Com 10 processos a fazê-lo ao mesmo tempo, perdem-se cerca de 9 em cada 10 registos. As escritas falhadas são leituras que apanharam o ficheiro a meio de ser substituído e não eram JSON válido.

O PostgreSQL não tem este problema porque nenhum processo reescreve a tabela. Cada `INSERT` é uma transação que acrescenta só a sua linha: o motor trata da concorrência (cada transação escreve a sua versão da linha, com MVCC, e os locks internos protegem as páginas enquanto são alteradas), e o WAL garante que um commit não se perde. Dez ligações a inserir ao mesmo tempo não se apagam umas às outras, por isso as 10 000 linhas ficam todas gravadas.

### Nota sobre a escrita do ficheiro

A primeira versão escrevia o ficheiro no próprio sítio, com `write_text`. Isso trunca o ficheiro e só depois escreve. Quando duas escritas se sobrepunham, a mais curta deixava o fim da mais longa no ficheiro (`Extra data`). A partir desse momento o ficheiro nunca mais era JSON válido, todas as escritas seguintes falhavam (cerca de 9 960 em 10 000), e no fim não havia registos para contar.

Por isso, cada processo escreve agora para um ficheiro temporário próprio e substitui o original com `os.replace`. Isto não é um lock: o ciclo de ler, modificar e escrever continua a competir, e os *lost updates* continuam lá. Só deixa de haver um ficheiro destruído para sempre. Mesmo assim ainda aparecem algumas escritas falhadas, porque a pasta está num volume FUSE (`fuseblk`) do devcontainer, onde um leitor pode ver o ficheiro a meio da troca.
