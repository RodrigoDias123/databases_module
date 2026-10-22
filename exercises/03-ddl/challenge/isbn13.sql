-- Challenge 03: DOMAIN isbn13
--
-- Corre depois do ../schema.sql, numa base sem livros:
--   psql -v ON_ERROR_STOP=1 -f ../schema.sql
--   psql -f isbn13.sql

-- Sem CASCADE: se alguma tabela ainda usar o domínio, dá erro em vez de
-- apagar a coluna. Corre primeiro o ../schema.sql, que apaga as tabelas.
drop domain if exists isbn13;

-- 1. Função de validação
--
-- Formato: só dígitos, com hífenes opcionais entre eles (nunca no início, no
-- fim ou dois seguidos), e exatamente 13 dígitos.
-- Dígito de controlo: os 13 dígitos, com pesos 1, 3, 1, 3, ..., têm de somar
-- um múltiplo de 10.
--
-- O CASE garante que a soma só é calculada quando o formato está certo. Com um
-- AND, o PostgreSQL não promete a ordem de avaliação, e um '::int' sobre uma
-- letra dava erro em vez de devolver false.
create or replace function isbn13_is_valid(value text)
returns boolean
language sql
immutable
strict
return case
    when value !~ '^[0-9]+(-[0-9]+)*$' then false
    when length(replace(value, '-', '')) <> 13 then false
    else (
        select sum(substr(replace(value, '-', ''), i, 1)::int * case when i % 2 = 1 then 1 else 3 end) % 10 = 0
        from generate_series(1, 13) as i
    )
end;

-- 2. Domínio
create domain isbn13 as text
    constraint isbn13_valid check (isbn13_is_valid(value));

-- 3. Usar o domínio na tabela book
alter table book alter column isbn type isbn13;

-- 4. Prova
insert into publisher (name) values ('Editora Exemplo');

-- Aceite: ISBN válido, com hífenes (o dígito de controlo certo é 7).
insert into book (title, isbn, publication_year, publisher_id)
values ('Livro Válido', '978-0-306-40615-7', 2020, 1);

-- Aceite: ISBN válido, só com dígitos.
insert into book (title, isbn, publication_year, publisher_id)
values ('Outro Livro Válido', '9781861972712', 2021, 1);

-- Falha: isbn13_valid (dígito de controlo errado: 8 em vez de 7).
insert into book (title, isbn, publication_year, publisher_id)
values ('Livro Inválido', '978-0-306-40615-8', 2020, 1);

-- Falha: isbn13_valid (formato: só 12 dígitos).
insert into book (title, isbn, publication_year, publisher_id)
values ('Livro Curto', '978030640615', 2020, 1);

-- Falha: isbn13_valid (formato: tem uma letra).
insert into book (title, isbn, publication_year, publisher_id)
values ('Livro com Letra', '978-0-306-4061X-7', 2020, 1);

-- Só os dois livros válidos ficam na tabela.
select book_id, title, isbn from book order by book_id;
