

drop table if exists fine, reservation, loan, copy, book_author, book, reader, author, publisher cascade;

create table publisher (
    publisher_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE,
    country text
);

create table author (
    author_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL,
    birth_year integer CHECK (birth_year >= 1000 AND birth_year <= EXTRACT(YEAR FROM CURRENT_DATE))
);

create table reader (
    reader_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL,
    card_number text NOT NULL UNIQUE,
    email text UNIQUE,
    phone text,
    registered_on date NOT NULL DEFAULT CURRENT_DATE
);

create table book (
    book_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title text NOT NULL,
    isbn text NOT NULL UNIQUE,
    publication_year integer CHECK (publication_year >= 1000 AND publication_year <= EXTRACT(YEAR FROM CURRENT_DATE)),
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
    CONSTRAINT unique_book_author_order UNIQUE (book_id, author_order)
);

create table copy (
    copy_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- CASCADE: sem o livro, os exemplares deixam de existir. Mesmo assim, um
    -- exemplar com empréstimos não é apagado (a FK de loan é RESTRICT).
    book_id integer NOT NULL REFERENCES book(book_id) ON DELETE CASCADE,
    barcode text NOT NULL UNIQUE,
    acquired_on date,
    condition text CHECK (condition IN ('new', 'good', 'fair', 'poor'))
);

create table loan (
    loan_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- RESTRICT: o histórico de empréstimos não se perde ao apagar um
    -- exemplar ou um leitor.
    copy_id integer NOT NULL REFERENCES copy(copy_id) ON DELETE RESTRICT,
    reader_id integer NOT NULL REFERENCES reader(reader_id) ON DELETE RESTRICT,
    loaned_at timestamptz NOT NULL,
    due_on date NOT NULL CHECK (due_on >= loaned_at::date),
    returned_at timestamptz CHECK (returned_at IS NULL OR returned_at >= loaned_at)
);

create table reservation (
    reservation_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- RESTRICT: não se apaga um livro ou um leitor com reservas registadas.
    book_id integer NOT NULL REFERENCES book(book_id) ON DELETE RESTRICT,
    reader_id integer NOT NULL REFERENCES reader(reader_id) ON DELETE RESTRICT,
    -- SET NULL: se o exemplar guardado desaparecer, a reserva continua à
    -- espera de outro exemplar do mesmo livro.
    copy_id integer REFERENCES copy(copy_id) ON DELETE SET NULL,
    reserved_at timestamptz NOT NULL,
    status text NOT NULL CHECK (status IN ('active', 'fulfilled', 'cancelled')),
    expires_on date CHECK (expires_on IS NULL OR expires_on >= reserved_at::date)
);


create table fine (
    fine_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- RESTRICT: uma multa não pode ficar sem o empréstimo que a originou.
    loan_id integer NOT NULL REFERENCES loan(loan_id) ON DELETE RESTRICT,
    amount numeric(8,2) NOT NULL CHECK (amount > 0),
    reason text NOT NULL CHECK (reason IN ('overdue', 'damage', 'loss')),
    issued_at timestamptz NOT NULL DEFAULT now(),
    paid_at timestamptz CHECK (paid_at IS NULL OR paid_at >= issued_at)
);


