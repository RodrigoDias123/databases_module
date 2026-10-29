-- Exercício 03: 5 statements que têm de falhar
--
-- Corre depois do schema.sql, sem ON_ERROR_STOP, para ver os 5 erros:
--   docker compose exec -T postgres psql -U postgres -d ex03 < exercises/03-ddl/exercise/invalid.sql

-- Dados válidos, para os statements abaixo terem linhas a que se referir.
insert into publisher (name, country) values ('Editora Exemplo', 'Portugal');
insert into author (name) values ('Autor Exemplo'), ('Segundo Autor');
insert into book (isbn, title, publication_year, publisher_id) values ('9780306406157', 'Livro Exemplo', 2020, 1);
insert into book_author (book_id, author_id, author_order) values (1, 1, 1);
insert into copy (book_id, barcode, acquired_on, condition) values (1, 'BC-0001', '2026-01-15', 'good'), (1, 'BC-0002', '2026-01-15', 'new');
insert into reader (card_number, name, email, address) values ('CARD-0001', 'Leitor Exemplo', 'leitor@example.com', 'Rua Exemplo, 1, Faro');
insert into loan (reader_id, copy_id, due_on) values (1, 1, current_date + 14);

-- 1. Falha: book_publisher_id_fkey (FOREIGN KEY com ON DELETE RESTRICT):
--    a editora 1 ainda tem o livro 1.
delete from publisher where publisher_id = 1;

-- 2. Falha: book_isbn_key (UNIQUE): o ISBN já existe no livro 1.
insert into book (isbn, title, publication_year, publisher_id) values ('9780306406157', 'Outro Livro', 2021, 1);

-- 3. Falha: unique_book_author_order (UNIQUE composto): o livro 1 já tem um autor na posição 1.
insert into book_author (book_id, author_id, author_order) values (1, 2, 1);

-- 4. Falha: copy_condition_check (CHECK): 'broken' não é um estado válido.
insert into copy (book_id, barcode, acquired_on, condition) values (1, 'BC-0003', '2026-01-15', 'broken');

-- 5. Falha: loan_due_after_loan (CHECK): a data limite é antes da data do empréstimo.
insert into loan (reader_id, copy_id, loaned_at, due_on) values (1, 2, '2026-10-10', '2026-10-01');
