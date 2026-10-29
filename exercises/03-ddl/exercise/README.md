# Exercício 03: SQL DDL, data types and constraints

Ficheiros entregues:

- `README.md`: este ficheiro, com o output do `invalid.sql`.
- [schema.sql](schema.sql): cria todas as tabelas da biblioteca.
- [invalid.sql](invalid.sql): insere alguns dados válidos e depois 5 statements que têm de falhar.

## Como correr

A partir da root do repositório:

```bash
./scripts/create-db.sh ex03
docker compose exec -T postgres psql -U postgres -d ex03 -v ON_ERROR_STOP=1 < exercises/03-ddl/exercise/schema.sql
docker compose exec -T postgres psql -U postgres -d ex03 < exercises/03-ddl/exercise/invalid.sql
```

O `schema.sql` começa com `drop table if exists ...`, por isso também pode ser corrido outra vez na mesma base.

## Modelo implementado

O `schema.sql` implementa o modelo de [../../02-modelling/exercise/model.md](../../02-modelling/exercise/model.md). As filiais e as transferências do challenge 02 ficam de fora.

| Tabela | PK | FKs (`ON DELETE`) | UNIQUE | Restantes colunas |
|--------|----|-------------------|--------|-------------------|
| `publisher` | `publisher_id` | — | `name` | `country` |
| `author` | `author_id` | — | — | `name` |
| `reader` | `reader_id` | — | `card_number`, `email` | `name`, `phone`, `address`, `registered_on` |
| `book` | `book_id` | `publisher_id → publisher` (RESTRICT) | `isbn` | `title`, `publication_year` |
| `book_author` | `(book_id, author_id)` | `book_id → book` (CASCADE), `author_id → author` (RESTRICT) | `(book_id, author_order)` | `author_order` |
| `copy` | `copy_id` | `book_id → book` (CASCADE) | `barcode` | `acquired_on`, `condition` |
| `loan` | `loan_id` | `reader_id → reader` (RESTRICT), `copy_id → copy` (RESTRICT) | `copy_id` com `returned_at` vazio (índice parcial) | `loaned_at`, `due_on`, `returned_at` |
| `reservation` | `reservation_id` | `reader_id → reader` (CASCADE), `book_id → book` (RESTRICT) | — | `reserved_at`, `status` |
| `fine` | `fine_id` | `loan_id → loan` (RESTRICT) | `loan_id` | `amount`, `paid_on` |

Tipos de dados:

- Chaves substitutas: `integer GENERATED ALWAYS AS IDENTITY`. As chaves naturais (ISBN, código de barras, cartão de leitor) ficam como `UNIQUE`.
- Dinheiro: `fine.amount numeric(8,2)`.
- Momentos no tempo: `loaned_at`, `returned_at` e `reserved_at` são `timestamptz`. Dias sem hora (`due_on`, `acquired_on`, `registered_on`, `paid_on`) são `date`.

Constraints:

| Tipo | Onde |
|------|------|
| `CHECK` | `book.isbn` (13 dígitos), `book.publication_year`, `book_author.author_order > 0`, `copy.condition IN ('new', 'good', 'worn', 'damaged')`, `loan_due_after_loan` (`due_on > loaned_at::date`), `loan_returned_after_loan`, `reservation.status`, `fine.amount > 0` |
| `UNIQUE` composto | `unique_book_author_order (book_id, author_order)`: dois autores não podem estar na mesma posição do mesmo livro |
| `ON DELETE RESTRICT` | `book.publisher_id`: não se apaga uma editora que ainda tem livros. `loan.copy_id`/`loan.reader_id`: o histórico de empréstimos não se perde. |
| `ON DELETE CASCADE` | `book_author.book_id`: a ligação livro–autor não faz sentido sem o livro. `copy.book_id`: sem o livro, os exemplares deixam de existir. |

A justificação de cada `ON DELETE` está num comentário no `schema.sql`.

As regras que precisam de ler outras linhas (no máximo 5 empréstimos abertos por leitor, multa criada numa devolução atrasada, etc.) ficam para triggers ou para a aplicação, como está explicado na secção 3 do modelo do exercício 02.

## Output do `invalid.sql`

Cada statement falha com a constraint indicada no comentário por cima dele:

| # | Statement | Constraint |
|---|-----------|------------|
| 1 | `DELETE` da editora 1, que ainda tem livros | `book_publisher_id_fkey` (FK com `ON DELETE RESTRICT`) |
| 2 | `INSERT` de um livro com um ISBN repetido | `book_isbn_key` (`UNIQUE`) |
| 3 | `INSERT` de um segundo autor na posição 1 do livro 1 | `unique_book_author_order` (`UNIQUE` composto) |
| 4 | `INSERT` de um exemplar com `condition = 'broken'` | `copy_condition_check` (`CHECK`) |
| 5 | `INSERT` de um empréstimo com a data limite antes da data do empréstimo | `loan_due_after_loan` (`CHECK`) |

```
$ docker compose exec -T postgres psql -U postgres -d ex03 < exercises/03-ddl/exercise/invalid.sql
INSERT 0 1
INSERT 0 2
INSERT 0 1
INSERT 0 1
INSERT 0 2
INSERT 0 1
INSERT 0 1
ERROR:  update or delete on table "publisher" violates RESTRICT setting of foreign key constraint "book_publisher_id_fkey" on table "book"
DETAIL:  Key (publisher_id)=(1) is referenced from table "book".
ERROR:  duplicate key value violates unique constraint "book_isbn_key"
DETAIL:  Key (isbn)=(9780306406157) already exists.
ERROR:  duplicate key value violates unique constraint "unique_book_author_order"
DETAIL:  Key (book_id, author_order)=(1, 1) already exists.
ERROR:  new row for relation "copy" violates check constraint "copy_condition_check"
DETAIL:  Failing row contains (3, 1, BC-0003, 2026-01-15, broken).
ERROR:  new row for relation "loan" violates check constraint "loan_due_after_loan"
DETAIL:  Failing row contains (2, 1, 2, 2026-10-10 00:00:00+00, 2026-10-01, null).
```

Os 7 `INSERT` iniciais são os dados válidos de que os 5 statements precisam (editora, autores, livro, autor do livro, 2 exemplares, leitor e empréstimo).
