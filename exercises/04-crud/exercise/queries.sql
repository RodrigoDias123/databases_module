-- Exercise 04: 12 CRUD operations on Pagila
--
-- [x] Each operation with its expected result (row count or value)
-- Correr numa cópia limpa da Pagila, por ordem e uma única vez.

-- 1. Filmes com rating 'PG-13' e mais de 120 minutos, ordenados por título.
select title, length
from film
where rating = 'PG-13'
  and length > 120
order by title;
-- Resultado: 118 linhas.

-- 2. Clientes sem nenhum aluguer no último ano.
select c.customer_id, c.first_name, c.last_name
from customer c
where not exists (
    select 1
    from rental r
    where r.customer_id = c.customer_id
      and r.rental_date > (select max(rental_date) from rental) - interval '1 year'
)
order by c.customer_id;
-- Resultado: 2 clientes (647 JENNIFER MITCHELL, 978 SOFIA BAKER).

-- 3. Os 10 clientes que mais gastaram.
select c.customer_id, c.first_name, c.last_name, c.email, sum(p.amount) as total
from customer c
join payment p on p.customer_id = c.customer_id
group by c.customer_id
order by total desc
limit 10;
-- Resultado: 10 linhas; 1.º KARL SEAL, 358.12.

-- 4. Inserir um cliente novo e obter o id que lhe foi atribuído.
insert into customer (store_id, first_name, last_name, email, address_id, active)
values (1, 'RODRIGO', 'DIAS', 'rodrigo.dias@example.com', 1, 1)
returning customer_id;
-- Resultado: INSERT 0 1, customer_id = 1000.

-- 5. Inserir várias linhas num só INSERT: 3 atores no elenco do filme 1.
select count(*) from film_actor where film_id = 1;

insert into film_actor (actor_id, film_id)
values (2, 1), (3, 1), (4, 1);

select count(*) from film_actor where film_id = 1;
-- Resultado: INSERT 0 3 (10 -> 13 atores).

-- 6. INSERT ... SELECT: copiar os filmes com mais de 150 minutos para uma tabela nova.
create table film_long (
    film_id integer primary key references film (film_id),
    title   text not null,
    length  smallint not null
);

insert into film_long (film_id, title, length)
select film_id, title, length
from film
where length > 150;
-- Resultado: INSERT 0 242.

-- 7. Aumentar 1.00 ao rental_rate dos filmes de 'Horror', com RETURNING.
select count(*)
from film_category fc
join category c on c.category_id = fc.category_id
where c.name = 'Horror';

begin;

update film f
set rental_rate = f.rental_rate + 1.00
from film_category fc, category c
where fc.film_id = f.film_id
  and c.category_id = fc.category_id
  and c.name = 'Horror'
returning f.film_id, f.title, f.rental_rate;

commit;
-- Resultado: UPDATE 142.

-- 8. Desativar (active = 0) os clientes sem alugueres no último ano.
select count(*)
from customer c
where not exists (
    select 1
    from rental r
    where r.customer_id = c.customer_id
      and r.rental_date > (select max(rental_date) from rental) - interval '1 year'
);

begin;

update customer c
set active = 0
where not exists (
    select 1
    from rental r
    where r.customer_id = c.customer_id
      and r.rental_date > (select max(rental_date) from rental) - interval '1 year'
);

commit;
-- Resultado: UPDATE 3 (inclui o cliente 1000 da operação 4).

-- 9. Upsert de um ator.
-- Chave actor_id: o nome não é único (há dois SUSAN DAVIS).
insert into actor (actor_id, first_name, last_name)
values (201, 'RODRIGO', 'DIAS')
on conflict (actor_id) do update
set first_name = excluded.first_name,
    last_name = excluded.last_name;

insert into actor (actor_id, first_name, last_name)
values (201, 'RODRIGO', 'DIAS SILVA')
on conflict (actor_id) do update
set first_name = excluded.first_name,
    last_name = excluded.last_name;

select actor_id, first_name, last_name from actor where actor_id = 201;

select setval('actor_actor_id_seq', (select max(actor_id) from actor));
-- Resultado: 1.º insere, 2.º atualiza; fica 201 RODRIGO DIAS SILVA.

-- 10. Upsert que ignora duplicados: repetir o INSERT da operação 5.
insert into film_actor (actor_id, film_id)
values (2, 1), (3, 1), (4, 1)
on conflict do nothing;
-- Resultado: INSERT 0 0.

-- 11. Apagar pagamentos de teste, verificando o WHERE primeiro.
select count(*) from payment where amount = 0.01;

insert into payment (customer_id, staff_id, rental_id, amount, payment_date)
select customer_id, staff_id, rental_id, 0.01, '2026-07-15 12:00:00+00'
from rental
where customer_id = 1
order by rental_id
limit 3;

select count(*)
from payment
where amount = 0.01
  and payment_date = '2026-07-15 12:00:00+00';

begin;

delete from payment
where amount = 0.01
  and payment_date = '2026-07-15 12:00:00+00'
returning payment_id, customer_id, amount;

commit;
-- Resultado: INSERT 0 3, SELECT 3, DELETE 3.

-- 12. Tentar apagar um filme que tem alugueres.
-- Falha: film_actor, film_category e inventory referenciam o filme com ON DELETE RESTRICT.
delete from film where film_id = 1;
-- Resultado: ERROR, viola film_actor_film_id_fkey.

-- Filme sem inventário: falha na mesma por causa de film_actor.
delete from film
where film_id = (
    select min(f.film_id)
    from film f
    where not exists (select 1 from inventory i where i.film_id = f.film_id)
);
-- Resultado: ERROR, viola film_actor_film_id_fkey (film_id 14).
