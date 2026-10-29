# Challenge 03: SQL DDL, data types and constraints

Obrigatório.

## Enunciado

Folder: `exercises/03-ddl/challenge/`

**Goal.** Make the database itself reject invalid ISBNs.

**Starting point.** An empty database (`./scripts/create-db.sh ch03`). You may add the domain to your library schema; if you do not, use this table:

```sql
CREATE TABLE book (
    book_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    isbn    isbn13 NOT NULL UNIQUE,
    title   text NOT NULL
);
```

An ISBN-13 has 13 digits. Hyphens may appear between digits, never at the start or the end and never two in a row. The last digit is a check digit: multiply the first 12 digits alternately by 1 and 3, add the results, and the check digit is `(10 - sum % 10) % 10`.

**Tasks.**

1. Write an `IMMUTABLE` SQL function `is_valid_isbn13(text) RETURNS boolean` that checks the format and the check digit.
2. Create `DOMAIN isbn13 AS text CHECK (is_valid_isbn13(VALUE))` and use it in the `book` table.
3. Prove that these values are accepted: `978-0-306-40615-7`, `9781402894626`, `978-3-16-148410-0`. Prove that these are rejected: `978-0-306-40615-8` (wrong check digit), `978-0-306-4061` (too short), `-9780306406157` (leading hyphen), `978--0306406157` (two hyphens in a row).
4. Explain why the function must be `IMMUTABLE`.

**Deliverables.**

- `isbn.sql` with the function, the domain, the table and the 7 test inserts.
- `README.md` with the output of `isbn.sql` and the explanation of task 4.

**Done when.** The 3 valid values are inserted, the 4 invalid ones fail with a domain check error, and the explanation is correct.

## Resposta

Ficheiro: [isbn.sql](isbn.sql). Não depende do `schema.sql` do exercício: cria a sua própria tabela `book` (a do enunciado) numa base vazia. A partir da root do repositório:

```bash
./scripts/create-db.sh ch03
docker compose exec -T postgres psql -U postgres -d ch03 < exercises/03-ddl/challenge/isbn.sql
```

Não uso `ON_ERROR_STOP`, porque 4 dos inserts têm de falhar. O script começa com `drop table if exists book` e `drop domain if exists isbn13`, por isso pode ser corrido outra vez.

O domínio fica fora do `schema.sql` do exercício por uma razão simples: assim cada script corre sozinho na sua base (`ex03` e `ch03`), como pedem os enunciados.

### O que o script faz

1. **`is_valid_isbn13(text)`**: uma função SQL `IMMUTABLE` (e `STRICT`, por isso `NULL` dá `NULL`) que devolve `true` só quando:
   - o formato está certo (`^[0-9]+(-[0-9]+)*$`): só dígitos, com hífenes opcionais entre eles, nunca no início, no fim, nem dois seguidos;
   - há exatamente 13 dígitos, sem contar os hífenes;
   - o dígito de controlo está certo: os 12 primeiros dígitos, multiplicados alternadamente por 1 e 3, somam `S`, e o 13º dígito é `(10 - S % 10) % 10`.

   O `CASE` só faz a soma quando o formato já está validado. Com `AND`, o PostgreSQL não garante a ordem de avaliação, e converter uma letra para `int` dava um erro em vez de `false`.
2. **`DOMAIN isbn13`**: é um `text` com `CONSTRAINT isbn13_valid CHECK (is_valid_isbn13(VALUE))`.
3. **`book`**: a tabela do enunciado, com `isbn isbn13 NOT NULL UNIQUE`.
4. **Os 7 inserts de teste**: 3 válidos e 4 inválidos, e no fim um `SELECT` que mostra os livros que ficaram.

### Output do `isbn.sql`

| ISBN | Esperado | Resultado |
|------|----------|-----------|
| `978-0-306-40615-7` | aceite | `INSERT 0 1` |
| `9781402894626` | aceite | `INSERT 0 1` |
| `978-3-16-148410-0` | aceite | `INSERT 0 1` |
| `978-0-306-40615-8` (dígito de controlo errado) | rejeitado | `ERROR: ... "isbn13_valid"` |
| `978-0-306-4061` (demasiado curto) | rejeitado | `ERROR: ... "isbn13_valid"` |
| `-9780306406157` (hífen no início) | rejeitado | `ERROR: ... "isbn13_valid"` |
| `978--0306406157` (dois hífenes seguidos) | rejeitado | `ERROR: ... "isbn13_valid"` |

```
$ docker compose exec -T postgres psql -U postgres -d ch03 < exercises/03-ddl/challenge/isbn.sql
DROP TABLE
DROP DOMAIN
CREATE FUNCTION
CREATE DOMAIN
CREATE TABLE
INSERT 0 1
INSERT 0 1
INSERT 0 1
ERROR:  value for domain isbn13 violates check constraint "isbn13_valid"
ERROR:  value for domain isbn13 violates check constraint "isbn13_valid"
ERROR:  value for domain isbn13 violates check constraint "isbn13_valid"
ERROR:  value for domain isbn13 violates check constraint "isbn13_valid"
 book_id |       isbn        |              title              
---------+-------------------+---------------------------------
       1 | 978-0-306-40615-7 | Válido com hífenes
       2 | 9781402894626     | Válido só com dígitos
       3 | 978-3-16-148410-0 | Válido com dígito de controlo 0
(3 rows)
```

Os 4 inválidos falham com o erro de check do domínio (`value for domain isbn13 violates check constraint "isbn13_valid"`), e o `SELECT` final mostra só os 3 válidos.

### Porque é que a função deve ser `IMMUTABLE`

`IMMUTABLE` é uma promessa ao PostgreSQL: com os mesmos argumentos, a função devolve sempre o mesmo resultado. Não lê tabelas, não depende da data, da hora, do fuso horário nem de outras configurações.

Para um `CHECK`, isto é importante, porque o PostgreSQL só verifica a constraint quando uma linha é inserida ou alterada. Nunca volta a verificar as linhas que já estão guardadas. Se o resultado da função pudesse mudar com o tempo:

- Linhas que foram aceites podiam passar a ser inválidas sem ninguém dar por isso, e a constraint deixava de garantir o que diz.
- Um `pg_dump` seguido de restore podia falhar, porque o restore volta a verificar todas as linhas com o resultado de hoje.

A validação de um ISBN só depende do próprio texto, por isso a função é mesmo `IMMUTABLE`. Isto traz duas vantagens:

- Pode ser usada num índice, por exemplo `CREATE INDEX ... ON book (is_valid_isbn13(isbn))`. Os índices só aceitam funções `IMMUTABLE`.
- O planner pode calcular o resultado de antemão quando o argumento é uma constante.

O PostgreSQL não verifica se a promessa é verdadeira. Se uma função que consulta uma tabela for marcada como `IMMUTABLE`, cria precisamente os problemas acima.
