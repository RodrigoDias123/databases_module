-- Exercício 03: biblioteca municipal (modelo do exercício 02)
--
-- Corre numa base vazia, a partir da root do repositório:
--   ./scripts/create-db.sh ex03
--   docker compose exec -T postgres psql -U postgres -d ex03 -v ON_ERROR_STOP=1 < exercises/03-ddl/exercise/schema.sql

drop table if exists fine, reservation, loan, copy, book_author, book, reader, author, publisher cascade;

create table publisher (
    publisher_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE,
    country text NOT NULL
);

create table author (
    author_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL
);

create table reader (
    reader_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    card_number text NOT NULL UNIQUE,
    name text NOT NULL,
    email text NOT NULL UNIQUE,
    phone text,
    address text NOT NULL,
    registered_on date NOT NULL DEFAULT CURRENT_DATE
);

create table book (
    book_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    isbn text NOT NULL UNIQUE CHECK (isbn ~ '^[0-9]{13}$'),
    title text NOT NULL,
    publication_year integer NOT NULL CHECK (publication_year BETWEEN 1000 AND 2100),
    -- RESTRICT: não se apaga uma editora que ainda tem livros no catálogo.
    publisher_id integer NOT NULL REFERENCES publisher(publisher_id) ON DELETE RESTRICT
);

create table book_author (
    -- CASCADE: a ligação livro–autor não faz sentido sem o livro.
    book_id integer NOT NULL REFERENCES book(book_id) ON DELETE CASCADE,
    -- RESTRICT: não se apaga um autor que ainda aparece em livros.
    author_id integer NOT NULL REFERENCES author(author_id) ON DELETE RESTRICT,
    author_order integer NOT NULL CHECK (author_order > 0),
    PRIMARY KEY (book_id, author_id),
    -- UNIQUE composto: dois autores não podem ter a mesma posição no mesmo livro.
    CONSTRAINT unique_book_author_order UNIQUE (book_id, author_order)
);

create table copy (
    copy_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- CASCADE: sem o livro, os exemplares deixam de existir. Mesmo assim, um
    -- exemplar com empréstimos não é apagado (a FK de loan é RESTRICT).
    book_id integer NOT NULL REFERENCES book(book_id) ON DELETE CASCADE,
    barcode text NOT NULL UNIQUE,
    acquired_on date NOT NULL,
    condition text NOT NULL CHECK (condition IN ('new', 'good', 'worn', 'damaged'))
);

create table loan (
    loan_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- RESTRICT: o histórico de empréstimos não se perde ao apagar um
    -- exemplar ou um leitor.
    reader_id integer NOT NULL REFERENCES reader(reader_id) ON DELETE RESTRICT,
    copy_id integer NOT NULL REFERENCES copy(copy_id) ON DELETE RESTRICT,
    loaned_at timestamptz NOT NULL DEFAULT now(),
    due_on date NOT NULL,
    returned_at timestamptz,
    CONSTRAINT loan_due_after_loan CHECK (due_on > loaned_at::date),
    CONSTRAINT loan_returned_after_loan CHECK (returned_at IS NULL OR returned_at >= loaned_at)
);

-- Um exemplar está no máximo num empréstimo aberto.
create unique index loan_one_open_per_copy on loan (copy_id) where returned_at IS NULL;

create table reservation (
    reservation_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- CASCADE: as reservas de um leitor não fazem sentido sem o leitor.
    reader_id integer NOT NULL REFERENCES reader(reader_id) ON DELETE CASCADE,
    -- RESTRICT: não se apaga um livro que ainda tem reservas.
    book_id integer NOT NULL REFERENCES book(book_id) ON DELETE RESTRICT,
    reserved_at timestamptz NOT NULL DEFAULT now(),
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'fulfilled', 'cancelled'))
);

create table fine (
    fine_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- RESTRICT: uma multa não pode ficar sem o empréstimo que a originou.
    -- UNIQUE: no máximo uma multa por empréstimo.
    loan_id integer NOT NULL UNIQUE REFERENCES loan(loan_id) ON DELETE RESTRICT,
    amount numeric(8,2) NOT NULL CHECK (amount > 0),
    paid_on date
);
