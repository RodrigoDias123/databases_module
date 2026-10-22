# Exercício 03: SQL DDL, data types and constraints

## Enunciado

Folder: `exercises/03-ddl/`

1. `schema.sql`, runnable on an empty PostgreSQL database, implementing your library model from exercise 02. Include at least one `CHECK`, one composite `UNIQUE`, and one foreign key whose `ON DELETE` is justified in a comment.
2. `invalid.sql` with 5 `INSERT` statements that must fail, each with a comment naming the constraint that rejects it.

## Modelo a implementar (do exercício 02)

Confirmado em [../02-modelling/model.md](../02-modelling/model.md): o exercício 02 está completo (diagrama ER, tabelas em 3NF e denormalização). O `schema.sql` implementa esse modelo **base**. As filiais e as transferências do challenge 02 ficam de fora.

Todas as tabelas têm uma chave substituta `*_id`, gerada pela base de dados. As chaves naturais ficam como `UNIQUE`.

| Tabela | PK | FKs | UNIQUE | Restantes colunas |
|--------|----|-----|--------|-------------------|
| `publisher` | `publisher_id` | — | `name` | `country` |
| `author` | `author_id` | — | — | `name`, `birth_year` |
| `book` | `book_id` | `publisher_id → publisher` | `isbn` | `title`, `publication_year` |
| `book_author` | `(book_id, author_id)` | `book_id → book`, `author_id → author` | `(book_id, author_order)` | `author_order` |
| `copy` | `copy_id` | `book_id → book` | `barcode` | `acquired_on`, `condition` |
| `reader` | `reader_id` | — | `card_number`, `email` | `name`, `phone`, `registered_on` |
| `loan` | `loan_id` | `copy_id → copy`, `reader_id → reader` | — | `loaned_at`, `due_on`, `returned_at` |
| `reservation` | `reservation_id` | `book_id → book`, `reader_id → reader`, `copy_id → copy` (pode ser vazio) | — | `reserved_at`, `status`, `expires_on` |
| `fine` | `fine_id` | `loan_id → loan` | — | `reason`, `amount`, `issued_at`, `paid_at` |

Regras do modelo que o schema tem de respeitar:

- Um livro (a obra, pelo ISBN) tem 0 ou mais exemplares, e cada exemplar é de um só livro.
- Um livro tem 1 ou mais autores, e a ordem dos autores importa (`author_order`). Por isso, o `UNIQUE (book_id, author_order)` é o `UNIQUE` composto pedido no enunciado.
- `loan.returned_at` fica vazio enquanto o exemplar não é devolvido. O estado "emprestado / disponível" não é guardado em `copy`: deduz-se de `loan`.
- Uma reserva é de um livro, não de um exemplar. `reservation.copy_id` só é preenchido quando um exemplar é guardado para ela.
- `fine` não tem `reader_id`: o leitor obtém-se pelo empréstimo (`fine → loan → reader`).
- `fine.amount` é guardado de propósito (é a denormalização do exercício 02), para as multas antigas não mudarem quando o valor por dia mudar.
- Ordem de criação, por causa das FKs: `publisher`, `author`, `reader` → `book` → `book_author`, `copy` → `loan` → `reservation` → `fine`.

## Challenge (obrigatório, em `challenge/`)

Make the database reject invalid ISBNs. Create a `DOMAIN isbn13` over `text` whose `CHECK` validates both the format (13 digits, optional hyphens) and the check digit, using an `IMMUTABLE` SQL function. Use the domain in your `book` table. Prove that a valid ISBN is accepted, and that one with a wrong check digit is rejected. Explain why the function should be `IMMUTABLE`.
