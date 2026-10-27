# Exercício da aula: Data ingestion com duas bases PostgreSQL

## Enunciado

Construir em **Python** um pipeline de dados com **duas bases de dados PostgreSQL** e um **Generator Service** entre elas (a parte rodeada a amarelo no quadro):

```
JSON ──> [PG1] ──read──> Generator Service ──JSON──> [PG2]
```

1. **Data ingestion**: ler dados em JSON e inseri-los na **PG1**.
2. **Generator Service**: ler os dados da PG1, processar cada pedido (`TasksReq`) e gerar um relatório em JSON.
3. **Escrita do resultado**: guardar o relatório na **PG2** (`InsightReport` + `ReportContent`) e atualizar o estado do pedido na PG1.

A API, o Redis e a Webapp que aparecem no quadro ficam **fora do âmbito** deste exercício.

## O que cada base de dados contém

### PG1: dados de origem

**Participant** (dados de saúde de cada pessoa):

| Coluna | Descrição |
|---|---|
| `id` | PK |
| `nome` | nome da pessoa |
| `localidade` | localidade (distrito) |
| `dnasc` | data de nascimento |
| `alt` | altura |
| `peso` | peso |
| `bp_sys` | pressão arterial sistólica |
| `bp_dia` | pressão arterial diastólica |
| `hr` | frequência cardíaca (heart rate) |
| `task_id` | FK → `tasks_req.id` |

**`tasks_req`** (pedidos de processamento):

| Coluna | Descrição |
|---|---|
| `id` | PK |
| `dt` | data do pedido |
| `nome` | nome do pedido |
| `outcome` | resultado do processamento |
| `finished` | data/hora de conclusão |
| `status` | estado do pedido (ex.: pendente, em curso, concluído, erro) |

### PG2: relatórios gerados

**`insight_report`**:

| Coluna | Descrição |
|---|---|
| `id_ppt` | PK |
| `dt` | data do relatório |
| `report_content_id` | FK → `report_content.id` |

**`report_content`**:

| Coluna | Descrição |
|---|---|
| `id` | PK |
| `content` | conteúdo do relatório (JSON) |

## Infraestrutura (Docker)

Os três serviços correm na mesma rede Docker:

```
Host
└── Docker network
    ├── pg1  (5432 dentro da rede, 5434 no host)
    ├── pg2  (5432 dentro da rede, 5433 no host)
    └── app  (Python, liga-se a pg1:5432 e pg2:5432)
```

- Dentro da rede, a app liga-se às duas bases pelo nome do serviço, ambas na porta **5432**.
- No host, as portas são diferentes para não colidirem: **5434** para a PG1 e **5433** para a PG2.

> **Nota:** o enunciado original usa a **5432** no host para a PG1. Mudei para a **5434** porque a 5432
> já está ocupada pelo Postgres do curso (`docker-compose.yml` da raiz). A porta pode ser alterada
> em `PG1_HOST_PORT` no `.env`.

## Como correr

Todos os comandos correm a partir desta pasta (o nome termina com um espaço, por isso leva aspas):

```bash
cd "exercises/08-transactions/Exercise aula "
export COMPOSE_PROJECT_NAME=exercise-aula-08   # só no devcontainer, ver nota abaixo
```

> **Nota (devcontainer):** o devcontainer define `COMPOSE_PROJECT_NAME=databases-module`, que se sobrepõe ao
> `name:` do `docker-compose.yml`. Sem o `export`, a pg1, a pg2 e a app entram no projeto do curso: o
> `docker compose ps` mostra também o Postgres, o Mongo e o Redis do curso, e um `down --remove-orphans`
> apagava-os. O `export` só vale para esse terminal; num terminal novo é preciso repeti-lo.

### 1. Configurar

```bash
cp .env.example .env    # e muda a POSTGRES_PASSWORD
```

### 1.1. Gerar os dados (opcional)

O `data/participants.json` é gerado com o [Faker](https://faker.readthedocs.io/) (locale `pt_PT`): cada pedido
é um rastreio num distrito, com nomes, datas de nascimento e valores de saúde plausíveis. Os distritos só se
repetem depois de usados os 18. O Faker é dependência de desenvolvimento e corre fora do container, com o uv:

```bash
uv run python -m app.fake_data                       # 5 pedidos, 3 a 10 participantes cada
uv run python -m app.fake_data --tasks 20 --seed 42  # mais pedidos, sempre os mesmos dados
uv run python -m app.fake_data --help                # todas as opções (--min, --max, --output)
```

### 2. Arrancar as bases

```bash
docker compose up -d pg1 pg2
docker compose ps       # esperar até as duas estarem "healthy"
```

As tabelas estão definidas em Python, com SQLAlchemy, em `app/models/` (`pg1.py` e `pg2.py`). A app cria-as
(`create_all`) quando arranca, se ainda não existirem.

### 3. Correr o pipeline

```bash
docker compose run --rm --build app                              # tabelas + ingestão + Generator Service
```

Ou cada passo em separado:

```bash
docker compose run --rm --build app python -m app.schema         # cria as tabelas nas duas bases
docker compose run --rm --build app python -m app.ingestion      # JSON -> PG1
docker compose run --rm --build app python -m app.generator      # PG1 -> PG2
```

O `--build` reconstrói a imagem, para apanhar as alterações ao código e ao `data/` (o JSON é copiado para a
imagem, não montado). A ingestão volta a inserir o ficheiro todo de cada vez que corre. O generator só
processa as tasks com `status = 'pendente'`.

### 4. Ver os resultados

```bash
# PG1: estado dos pedidos
docker compose exec pg1 psql -U postgres -d ingestion \
  -c "select id, nome, status, outcome, finished from tasks_req order by id"

# PG2: relatórios gerados
docker compose exec pg2 psql -U postgres -d reports \
  -c "select r.id_ppt, r.dt, c.content from insight_report r join report_content c on c.id = r.report_content_id"
```

A partir do host também dá para ligar com um cliente qualquer: `localhost:5434` (PG1) e `localhost:5433` (PG2).
Dentro do devcontainer estas portas não estão acessíveis (só escutam no `127.0.0.1` do host); aí usa o
`docker compose exec` acima.

### 5. Parar / recomeçar do zero

```bash
docker compose down      # pára os containers e mantém os dados
docker compose down -v   # apaga também os volumes; necessário se mudares os modelos em app/models/
```

O `create_all` só cria as tabelas que faltam e não altera as que já existem. Se mudares uma coluna
em `app/models/` (`pg1.py` e `pg2.py`), tens de apagar os volumes (`down -v`) para as tabelas serem recriadas.

