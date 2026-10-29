-- Exercício 04: 12 operações CRUD na Pagila
--
-- Corre numa cópia limpa da Pagila, por ordem e uma única vez, a partir da root:
--   ./scripts/create-db.sh ex04 --pagila --reset
--   docker compose exec -T postgres psql -U postgres -d ex04 -v ON_ERROR_STOP=1 < exercises/04-crud/exercise/queries.sql

-- 1. Filmes PG-13 com mais de 120 minutos, ordenados por título.
-- Esperado: 118 linhas, de APOLLO TEEN a WRONG BEHAVIOR.
select film_id, title, length
from film
where rating = 'PG-13'
  and length > 120
order by title;

-- 2. Atores cujo apelido contém 'son', em maiúsculas ou minúsculas.
-- Esperado: 9 linhas.
select actor_id, first_name, last_name
from actor
where last_name ilike '%son%'
order by last_name, first_name;

-- 3. Alugueres ainda não devolvidos.
-- Esperado: 241 linhas.
select rental_id, rental_date, inventory_id, customer_id
from rental
where return_date is null
order by rental_id;

-- 4. Valores distintos de rental_duration, por ordem crescente.
-- Esperado: 5 linhas, de 3 a 7.
select distinct rental_duration
from film
order by rental_duration;

-- 5. Terceira página de filmes por título, 10 filmes por página.
-- Esperado: 10 linhas, de AMERICAN CIRCUS a ANYTHING SAVANNAH.
select film_id, title
from film
order by title
limit 10 offset 20;

-- 6. Número de alugueres em janeiro de 2026, escrito de duas formas.
-- Esperado: 746 e 781.
--
-- Diferem porque rental_date é timestamptz. '2026-01-31' é convertido para
-- 2026-01-31 00:00:00, por isso o BETWEEN deixa de fora quase todo o dia 31
-- (os alugueres depois da meia-noite). A segunda forma é a correta: o
-- intervalo semiaberto [1 de janeiro, 1 de fevereiro) apanha o mês inteiro,
-- seja qual for a precisão da hora.
select count(*) as with_between
from rental
where rental_date between '2026-01-01' and '2026-01-31';

select count(*) as with_half_open
from rental
where rental_date >= '2026-01-01'
  and rental_date < '2026-02-01';

-- 7. Inserir o ator ADA LOVELACE e obter o actor_id gerado.
-- Esperado: 1 linha, actor_id 201.
insert into actor (first_name, last_name)
values ('ADA', 'LOVELACE')
returning actor_id;

-- 8. Aumentar 0.50 ao rental_rate dos filmes NC-17 com menos de 60 minutos.
-- Esperado: 21 linhas no SELECT e no UPDATE.
begin;

select count(*)
from film
where rating = 'NC-17'
  and length < 60;

update film
set rental_rate = rental_rate + 0.50
where rating = 'NC-17'
  and length < 60
returning film_id, title, rental_rate;

commit;

-- 9. Upsert: mais um prémio para o ator 1, corrido duas vezes.
-- Esperado: awards = 2.
create table actor_award (
    actor_id integer PRIMARY KEY REFERENCES actor,
    awards   integer NOT NULL DEFAULT 0
);

insert into actor_award (actor_id, awards)
values (1, 1)
on conflict (actor_id) do update
set awards = actor_award.awards + 1
returning *;

insert into actor_award (actor_id, awards)
values (1, 1)
on conflict (actor_id) do update
set awards = actor_award.awards + 1
returning *;

-- 10. Inserir o ator 2 com 5 prémios, sem tocar na linha se já existir.
-- Esperado: a 1.ª vez insere 1 linha, a 2.ª insere 0.
insert into actor_award (actor_id, awards)
values (2, 5)
on conflict do nothing;

insert into actor_award (actor_id, awards)
values (2, 5)
on conflict do nothing;

-- 11. Inserir 3 pagamentos de teste num só statement.
-- Esperado: 3 linhas.
insert into payment (customer_id, staff_id, rental_id, amount, payment_date)
values (1, 2, 76, 0.01, '2026-07-30 12:00+00'),
       (1, 2, 76, 0.01, '2026-07-30 12:00+00'),
       (1, 2, 76, 0.01, '2026-07-30 12:00+00')
returning payment_id;

-- 12. Apagar os 3 pagamentos de teste, verificando primeiro o WHERE.
-- Esperado: 3 linhas no SELECT e no DELETE.
begin;

select count(*)
from payment
where customer_id = 1
  and rental_id = 76
  and amount = 0.01
  and payment_date = '2026-07-30 12:00+00';

delete from payment
where customer_id = 1
  and rental_id = 76
  and amount = 0.01
  and payment_date = '2026-07-30 12:00+00'
returning payment_id;

commit;
