-- Challenge 05: graus de separação entre atores (WITH RECURSIVE)
--
-- Corre na base pagila. O ator de partida vem da variável actor_id (por omissão 1):
--   psql -d pagila -f degrees.sql
--   psql -d pagila -v actor_id=42 -f degrees.sql

\if :{?actor_id}
\else
\set actor_id 1
\endif

with recursive
-- 1. Ligações do grafo: pares de atores distintos que entraram no mesmo filme.
--
-- O DISTINCT deixa cada par uma só vez, mesmo que tenham vários filmes em
-- comum. Sem ele, cada filme partilhado gerava mais um caminho igual em cada
-- passo da recursão.
co_actor as (
    select distinct fa1.actor_id, fa2.actor_id as other_actor_id
    from film_actor fa1
    join film_actor fa2 on fa2.film_id = fa1.film_id
                       and fa2.actor_id <> fa1.actor_id
),
-- 2. Caminhos a partir do ator inicial.
reach (actor_id, distance, path) as (
    -- Caso base: o próprio ator, a distância 0.
    select a.actor_id, 0, array[a.actor_id]
    from actor a
    where a.actor_id = :actor_id

    union all

    -- Passo recursivo: avança uma ligação a partir dos atores do passo anterior.
    select c.other_actor_id, r.distance + 1, r.path || c.other_actor_id
    from reach r
    join co_actor c on c.actor_id = r.actor_id
    where r.distance < 3                        -- termina: no máximo 3 graus
      and not c.other_actor_id = any(r.path)    -- não revisita atores do caminho
)
-- 3. O mesmo ator pode ser alcançado por vários caminhos: fica o mais curto.
select a.actor_id, a.first_name, a.last_name, min(r.distance) as distance
from reach r
join actor a on a.actor_id = r.actor_id
where r.actor_id <> :actor_id
group by a.actor_id
order by distance, a.last_name, a.first_name;
