

insert into publisher (name) values ('Editora Exemplo');

insert into book (title, isbn, publication_year, publisher_id) values ('Livro Exemplo', '1234567890123', 2020, 1);

insert into author (name, birth_year) values ('Autor Exemplo', 1980);

insert into author (name, birth_year) values ('Segundo Autor', 1975);

insert into book_author (book_id, author_id, author_order) values (1, 1, 1);

insert into copy (book_id, barcode, condition) values (1, 'BC-0001', 'good');

insert into reader (name, card_number, email) values ('Leitor Exemplo', 'CARD-0001', 'leitor@example.com');

insert into loan (copy_id, reader_id, loaned_at, due_on) values (1, 1, now(), current_date + 14);

-- INSERTs que têm de falhar

-- 1. Falha: book_title_not_null (NOT NULL): o livro não tem título.
insert into book (isbn, publication_year, publisher_id) values ('9999999999999', 2021, 1);

-- 2. Falha: book_isbn_key (UNIQUE): o ISBN já existe no livro 1.
insert into book (title, isbn, publication_year, publisher_id) values ('Outro Livro', '1234567890123', 2021, 1);

-- 3. Falha: unique_book_author_order (UNIQUE composto): o livro 1 já tem um autor na posição 1.
insert into book_author (book_id, author_id, author_order) values (1, 2, 1);

-- 4. Falha: fine_amount_check (CHECK): o valor da multa tem de ser maior que 0.
insert into fine (loan_id, amount, reason) values (1, -5.00, 'overdue');

-- 5. Falha: loan_copy_id_fkey (FOREIGN KEY): não existe nenhum exemplar com copy_id 9999.
insert into loan (copy_id, reader_id, loaned_at, due_on) values (9999, 1, now(), current_date + 14);