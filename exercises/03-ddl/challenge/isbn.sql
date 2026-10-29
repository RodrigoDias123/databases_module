-- Challenge 03: DOMAIN isbn13
--
-- Corre numa base vazia, a partir da root do repositório:
--   ./scripts/create-db.sh ch03
--   docker compose exec -T postgres psql -U postgres -d ch03 < exercises/03-ddl/challenge/isbn.sql

drop table if exists book;
drop domain if exists isbn13;

-- 1. Função de validação
--
-- Formato: só dígitos, com hífenes opcionais entre eles (nunca no início, no
-- fim ou dois seguidos), e exatamente 13 dígitos.
-- Dígito de controlo: os 12 primeiros dígitos, com pesos 1, 3, 1, 3, ...,
-- somam S, e o 13º dígito tem de ser (10 - S % 10) % 10.
--
-- O CASE garante que a soma só é calculada quando o formato está certo. Com um
-- AND, o PostgreSQL não promete a ordem de avaliação, e um '::int' sobre uma
-- letra dava erro em vez de devolver false.
create or replace function is_valid_isbn13(value text)
returns boolean
language sql
immutable
strict
return case
    when value !~ '^[0-9]+(-[0-9]+)*$' then false
    when length(replace(value, '-', '')) <> 13 then false
    else (
        select (10 - sum(substr(digits, i, 1)::int * case when i % 2 = 1 then 1 else 3 end) % 10) % 10
               = substr(digits, 13, 1)::int
        from (select replace(value, '-', '') as digits) as d,
             generate_series(1, 12) as i
        group by digits
    )
end;

-- 2. Domínio
create domain isbn13 as text
    constraint isbn13_valid check (is_valid_isbn13(value));

-- 3. Tabela que usa o domínio
create table book (
    book_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    isbn    isbn13 NOT NULL UNIQUE,
    title   text NOT NULL
);

-- 4. Prova: 3 ISBNs válidos são aceites
insert into book (isbn, title) values ('978-0-306-40615-7', 'Válido com hífenes');
insert into book (isbn, title) values ('9781402894626', 'Válido só com dígitos');
insert into book (isbn, title) values ('978-3-16-148410-0', 'Válido com dígito de controlo 0');

-- 5. Prova: 4 ISBNs inválidos são rejeitados pelo isbn13_valid
-- Dígito de controlo errado (8 em vez de 7).
insert into book (isbn, title) values ('978-0-306-40615-8', 'Dígito de controlo errado');
-- Demasiado curto (11 dígitos).
insert into book (isbn, title) values ('978-0-306-4061', 'Demasiado curto');
-- Hífen no início.
insert into book (isbn, title) values ('-9780306406157', 'Hífen no início');
-- Dois hífenes seguidos.
insert into book (isbn, title) values ('978--0306406157', 'Dois hífenes seguidos');

-- Só os 3 livros válidos ficam na tabela.
select book_id, isbn, title from book order by book_id;
