-- Challenge 05: graus de separação entre atores (WITH RECURSIVE)
--
-- Corre numa cópia limpa da Pagila (ch05). Por omissão parte do ator 1 e
-- procura o caminho até ao ator 200; as variáveis from_actor e to_actor mudam-nos:
--   psql -d ch05 -v ON_ERROR_STOP=1 -f degrees.sql
--   psql -d ch05 -v ON_ERROR_STOP=1 -v from_actor=42 -v to_actor=7 -f degrees.sql

\if :{?from_actor}
\else
\set from_actor 1
\endif
\if :{?to_actor}
\else
\set to_actor 200
\endif

-- Tarefa 2: atores a no máximo 3 graus do ator inicial, com a distância mais curta.

with recursive
-- Tarefa 1. Ligações do grafo: dois atores estão ligados se entraram juntos
-- em pelo menos 3 filmes. Cada par aparece nos dois sentidos (A, B) e (B, A),
-- e o GROUP BY deixa-o uma só vez, seja qual for o número de filmes em comum.
edge (actor_id, other_actor_id) as (
    select fa1.actor_id, fa2.actor_id
    from film_actor fa1
    join film_actor fa2 on fa2.film_id = fa1.film_id
                       and fa2.actor_id <> fa1.actor_id
    group by fa1.actor_id, fa2.actor_id
    having count(*) >= 3
),
-- Caminhos a partir do ator inicial.
reach (actor_id, distance, path) as (
    -- Caso base: o próprio ator, a distância 0.
    select a.actor_id, 0, array[a.actor_id]
    from actor a
    where a.actor_id = :from_actor

    union all

    -- Passo recursivo: avança uma ligação a partir dos atores do passo anterior.
    select e.other_actor_id, r.distance + 1, r.path || e.other_actor_id
    from reach r
    join edge e on e.actor_id = r.actor_id
    where r.distance < 3                        -- termina: no máximo 3 graus
      and not e.other_actor_id = any(r.path)    -- não revisita atores do caminho
)
-- O mesmo ator pode ser alcançado por vários caminhos: fica o mais curto.
select a.actor_id, a.first_name, a.last_name, min(r.distance) as distance
from reach r
join actor a on a.actor_id = r.actor_id
where r.actor_id <> :from_actor
group by a.actor_id
order by distance, a.actor_id;

-- Tarefa 3: caminho mais curto do ator inicial ao ator final, no máximo 5 graus.
-- Sem caminho, o resultado fica vazio.

with recursive
edge (actor_id, other_actor_id) as (
    select fa1.actor_id, fa2.actor_id
    from film_actor fa1
    join film_actor fa2 on fa2.film_id = fa1.film_id
                       and fa2.actor_id <> fa1.actor_id
    group by fa1.actor_id, fa2.actor_id
    having count(*) >= 3
),
reach (actor_id, distance, path) as (
    select a.actor_id, 0, array[a.actor_id]
    from actor a
    where a.actor_id = :from_actor

    union all

    select e.other_actor_id, r.distance + 1, r.path || e.other_actor_id
    from reach r
    join edge e on e.actor_id = r.actor_id
    where r.distance < 5                        -- termina: no máximo 5 graus
      and r.actor_id <> :to_actor               -- um caminho que já chegou não continua
      and not e.other_actor_id = any(r.path)    -- não revisita atores do caminho
),
shortest as (
    select distance, path
    from reach
    where actor_id = :to_actor
    order by distance, path                     -- em caso de empate, um caminho fixo
    limit 1
)
select s.distance,
       array(
           select a.first_name || ' ' || a.last_name
           from unnest(s.path) with ordinality as p(actor_id, step)
           join actor a on a.actor_id = p.actor_id
           order by p.step
       ) as path
from shortest s;
