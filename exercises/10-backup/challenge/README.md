# Challenge 10: Backup and restore

Opcional.

## Enunciado

Folder: `exercises/10-backup/challenge/`

**Goal.** Automate backups with retention and check every backup by restoring it.

**Starting point.** The `pagila` database and the tutorial of this session.

**Tasks.**

1. `backup.sh` takes a custom-format dump of `pagila` named `pagila_YYYY-MM-DD_HHMM.dump` and, next to it, a file `pagila_YYYY-MM-DD_HHMM.counts` with the row count of every table at the time of the dump. It then applies a retention policy: keep the latest backup of each of the last 7 days, and the latest backup of each of the last 4 weeks; delete the rest. Accept an optional `--now YYYY-MM-DD` argument that replaces today's date, so that the retention can be tested without waiting weeks.
2. `verify.sh` restores the latest dump into a throwaway container (`docker run --rm ... postgres:18`), counts the rows of every table, compares them with the `.counts` file of that dump, prints every difference and exits with a non-zero code if there is any.
3. Test the retention: create backups for 40 simulated days with `--now` and show which files remain.
4. Schedule both scripts (cron on Linux and macOS, Task Scheduler or a loop in WSL on Windows) and show the log of two scheduled runs.

**Deliverables.**

- `backup.sh`, `verify.sh`.
- `README.md` with the schedule configuration, the list of files left by task 3, the log of task 4, and the output of `verify.sh` for a good dump and for a dump you changed on purpose.

**Done when.** After task 3 exactly the expected files remain (at most 7 daily and 4 weekly), `verify.sh` exits with 0 for a good dump and with a non-zero code for a changed one.

## Checklist

- [x] `backup.sh`: dump `pagila_YYYY-MM-DD_HHMM.dump` + `.counts` do mesmo snapshot, retenção 7 diárias + 4 semanais, `--now`
- [x] `verify.sh`: restauro num container `postgres:18` descartável, compara com o `.counts`, exit ≠ 0 se houver diferenças
- [x] Tarefa 3: 40 dias simulados, ficam 9 backups (7 diárias + 2 semanais que não coincidem com as diárias)
- [x] Tarefa 4: agendamento com cron (`crontab`, `crontab.demo`) e log de duas execuções agendadas
- [x] `verify.sh` com exit 0 para uma dump boa e exit 1 para duas dumps alteradas

## Resolução

Ficheiros entregues:

- [backup.sh](backup.sh): tarefa 1.
- [verify.sh](verify.sh): tarefa 2.
- [counts.sql](counts.sql): contagem de linhas de todas as tabelas de `public` (70, incluindo `payment` e as suas partições). É usado pelos dois scripts, para que contem da mesma forma.
- [crontab](crontab) e [crontab.demo](crontab.demo): tarefa 4.

As backups ficam em `challenge/backups/` (ignorada pelo Git, como a `backups/` da root). `BACKUP_DIR` muda a pasta e `DB` muda a base de dados. Os scripts precisam de bash 4 e de GNU `date` (no macOS: `brew install bash coreutils`, e usar `gdate`).

### `backup.sh`

```bash
./backup.sh                          # hoje, hora atual
./backup.sh --now 2026-10-01         # finge que hoje é 2026-10-01 (hora atual)
./backup.sh --now 2026-10-01T0300    # finge que são 03:00 de 2026-10-01
```

**Dump e contagens do mesmo instante.** Se o `pg_dump` e as contagens corressem em separado, uma escrita entre os dois punha o `.counts` em desacordo com a dump, e o `verify.sh` acusava um erro que não existe. Por isso o script abre uma sessão `psql` (coprocess) com `BEGIN ISOLATION LEVEL REPEATABLE READ` e `SELECT pg_export_snapshot()`. O `pg_dump --snapshot=<id>` lê exatamente esse snapshot, e as contagens correm a seguir na mesma transação. A dump e o `.counts` são escritos como `.tmp` e só são renomeados no fim: uma execução que falhe não deixa uma backup a meio que a retenção tome como boa.

Formato do `.counts`, uma tabela por linha, separada por tab:

```text
actor	200
address	1003
category	16
...
```

**Retenção.** Em relação à data "agora" (hoje ou `--now`):

- **diárias:** a backup mais recente de cada um dos últimos 7 dias, hoje incluído (`agora - 6` a `agora`);
- **semanais:** a backup mais recente de cada uma das últimas 4 semanas ISO (segunda a domingo), a semana atual incluída;
- todas as outras com data até "agora" são apagadas (o `.dump` e o `.counts`). As que têm data posterior a "agora" nunca são apagadas.

A semana atual e a anterior já estão cobertas pelas diárias, por isso normalmente ficam 7 diárias + 2 semanais = 9 backups, e nunca mais de 7 + 4 = 11. Os nomes ordenam-se por ordem cronológica, por isso "a mais recente" é a última pela ordem do nome.

### Tarefa 3: 40 dias simulados

De 2026-09-21 a 2026-10-30, duas backups por dia (03:00 e 15:00), numa pasta à parte:

```bash
export BACKUP_DIR=backups/sim
for i in $(seq 39 -1 0); do
  d=$(date -d "2026-10-30 - $i days" +%F)
  ./backup.sh --now ${d}T0300
  ./backup.sh --now ${d}T1500
done > backups/sim.log 2>&1
ls backups/sim
```

Foram escritas 80 backups e apagadas 71. O fim do log:

```text
2026-10-30 21:10:16 backup: wrote pagila_2026-10-30_0300.dump (4.4M) and pagila_2026-10-30_0300.counts (70 tables)
2026-10-30 21:10:16 backup: deleted pagila_2026-10-23_1500
2026-10-30 21:10:16 backup: retention for 2026-10-30: 7 daily, 4 weekly, 9 backups kept
2026-10-30 21:10:16 backup: wrote pagila_2026-10-30_1500.dump (4.4M) and pagila_2026-10-30_1500.counts (70 tables)
2026-10-30 21:10:16 backup: deleted pagila_2026-10-30_0300
2026-10-30 21:10:16 backup: retention for 2026-10-30: 7 daily, 4 weekly, 9 backups kept
```

Ficheiros que restam (com o dia da semana e a semana ISO de cada um):

| Ficheiro (`.dump` + `.counts`) | Dia | Semana | Porque fica |
|---|---|---|---|
| `pagila_2026-10-11_1500` | dom | W41 | semanal (mais recente da W41) |
| `pagila_2026-10-18_1500` | dom | W42 | semanal (mais recente da W42) |
| `pagila_2026-10-24_1500` | sáb | W43 | diária |
| `pagila_2026-10-25_1500` | dom | W43 | diária e semanal (W43) |
| `pagila_2026-10-26_1500` | seg | W44 | diária |
| `pagila_2026-10-27_1500` | ter | W44 | diária |
| `pagila_2026-10-28_1500` | qua | W44 | diária |
| `pagila_2026-10-29_1500` | qui | W44 | diária |
| `pagila_2026-10-30_1500` | sex | W44 | diária e semanal (W44) |

São os 9 esperados: 7 diárias (24 a 30 de outubro) e as semanais das 4 semanas (W41 a W44), duas das quais coincidem com diárias. Para cada dia ficou só a backup das 15:00, a mais recente. As de 21/09 a 10/10 e as das 03:00 foram todas apagadas.

### `verify.sh`

```bash
./verify.sh                          # a dump mais recente de BACKUP_DIR
./verify.sh caminho/para/x.dump      # essa dump (com x.counts ao lado)
```

Inicia `docker run --rm -d postgres:18` com um nome único e espera que o servidor aceite ligações. Depois cria a base de dados e restaura com `pg_restore --no-owner --no-privileges --exit-on-error` (o container não tem os roles do servidor original). Corre o `counts.sql` e faz um *full outer join* (`join -a 1 -a 2`) com o `.counts`. Uma tabela que exista só de um dos lados aparece como `MISSING`. O container é sempre removido (`trap ... EXIT`), mesmo quando o script falha.

**Dump boa:**

```text
$ ./verify.sh; echo "exit $?"
2026-10-30 21:09:12 verify: checking pagila_2026-10-30_2108.dump
2026-10-30 21:09:14 verify: restored in 0.4 s
2026-10-30 21:09:14 verify: OK: all 70 tables have the expected row counts
exit 0
```

**Dump alterada de propósito (linhas em falta).** Numa cópia do Pagila apaguei 19 linhas de `film_actor` (`actor_id = 1`) e 3 pagamentos, fiz a dump e pus-lhe ao lado o `.counts` da dump boa. É o caso de uma backup que restaura sem erros mas não tem os dados que devia:

```text
$ ./verify.sh backups/tampered/pagila_2026-10-30_2108_rows.dump; echo "exit $?"
2026-10-30 21:09:25 verify: checking pagila_2026-10-30_2108_rows.dump
2026-10-30 21:09:27 verify: restored in 0.4 s
2026-10-30 21:09:27 verify: FAILED: 4 of 70 tables differ
  film_actor                   expected 5462     restored 5443
  payment                      expected 51061    restored 51058
  payment_p2022_01             expected 723      restored 722
  payment_p2022_06             expected 2654     restored 2652
exit 1
```

**Dump alterada de propósito (ficheiro truncado).** Os primeiros 2 MB da dump boa, como uma cópia interrompida:

```text
$ ./verify.sh backups/tampered/pagila_2026-10-30_2108_truncated.dump; echo "exit $?"
2026-10-30 21:09:27 verify: checking pagila_2026-10-30_2108_truncated.dump
pg_restore: error: could not read from input file: end of file
2026-10-30 21:09:28 verify: FAILED: pg_restore could not restore pagila_2026-10-30_2108_truncated.dump
exit 1
```

### Tarefa 4: agendamento

No devcontainer (Debian), o cron não vem instalado:

```bash
sudo apt-get update && sudo apt-get install -y cron
sudo service cron start
```

Agendamento real, em [crontab](crontab): backup todos os dias às 02:00 e verificação da dump mais recente às 02:30.

```cron
PATH=/usr/local/bin:/usr/bin:/bin
0 2 * * *  /workspaces/databases_module/exercises/10-backup/challenge/backup.sh >> /workspaces/databases_module/exercises/10-backup/challenge/backups/cron.log 2>&1
30 2 * * * /workspaces/databases_module/exercises/10-backup/challenge/verify.sh >> /workspaces/databases_module/exercises/10-backup/challenge/backups/cron.log 2>&1
```

O cron corre com um `PATH` mínimo e sem o diretório atual: por isso o `PATH` é definido no crontab, os caminhos são absolutos, e o `backup.sh` faz `cd` para a root do repositório para ler o `.env` (o `verify.sh` só usa `docker`). Toda a saída vai para `backups/cron.log`, e cada linha começa com a data e a hora.

Para ver duas execuções sem esperar dois dias, [crontab.demo](crontab.demo) corre os dois scripts a cada minuto (o verify 20 s depois do backup):

```bash
crontab exercises/10-backup/challenge/crontab.demo
# esperar 2 a 3 minutos
cat exercises/10-backup/challenge/backups/cron.log
crontab -r          # retirar: cada verify inicia um container
```

Log de duas execuções agendadas com `crontab.demo` (`backups/cron.log`, minutos 21:14 e 21:15):

```text
2026-10-30 21:14:01 backup: wrote pagila_2026-10-30_2114.dump (4.4M) and pagila_2026-10-30_2114.counts (70 tables)
2026-10-30 21:14:01 backup: deleted pagila_2026-10-30_2108
2026-10-30 21:14:01 backup: retention for 2026-10-30: 1 daily, 1 weekly, 1 backups kept
2026-10-30 21:14:21 verify: checking pagila_2026-10-30_2114.dump
2026-10-30 21:14:22 verify: restored in 0.4 s
2026-10-30 21:14:22 verify: OK: all 70 tables have the expected row counts
2026-10-30 21:15:01 backup: wrote pagila_2026-10-30_2115.dump (4.4M) and pagila_2026-10-30_2115.counts (70 tables)
2026-10-30 21:15:01 backup: deleted pagila_2026-10-30_2114
2026-10-30 21:15:01 backup: retention for 2026-10-30: 1 daily, 1 weekly, 1 backups kept
2026-10-30 21:15:21 verify: checking pagila_2026-10-30_2115.dump
2026-10-30 21:15:22 verify: restored in 0.4 s
2026-10-30 21:15:22 verify: OK: all 70 tables have the expected row counts
```

Em cada minuto, o cron correu o `backup.sh` às :01 e o `verify.sh` às :21. A retenção apagou a backup do minuto anterior, porque no mesmo dia só fica a mais recente. O `verify.sh` restaurou a dump nova e confirmou as 70 contagens. Depois das duas execuções retirei o crontab de demonstração (`crontab -r`).
