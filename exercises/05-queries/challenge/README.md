# Challenge 05: Queries I, joins, aggregation, subqueries and CTEs

Obrigatório.

## Enunciado

Using a recursive CTE (`WITH RECURSIVE`), compute the "degrees of separation" between actors: two actors are at distance 1 if they appeared in the same film. Given one actor, list every actor reachable within 3 degrees and the shortest distance to each. Make sure the query terminates and does not revisit actors.

## Resposta

Ficheiro: [degrees.sql](degrees.sql). Corre na base `pagila`:

```bash
psql -d pagila -f degrees.sql                 # parte do ator 1 (PENELOPE GUINESS)
psql -d pagila -v actor_id=42 -f degrees.sql  # parte de outro ator
```

### O que o script faz

1. **`co_actor`**: as ligações do grafo. São os pares de atores distintos que entraram no mesmo filme, obtidos com um self join de `film_actor`. O `DISTINCT` deixa cada par uma só vez. Sem ele, dois atores com 4 filmes em comum davam 4 caminhos iguais em cada passo da recursão.
2. **`reach`** (`WITH RECURSIVE`):
   - **caso base**: o ator inicial, com `distance = 0` e `path = {actor_id}`;
   - **passo recursivo**: a partir de cada ator do passo anterior, segue uma ligação de `co_actor`, soma 1 à distância e junta o novo ator ao `path`.
3. **Resultado**: o mesmo ator pode ser alcançado por vários caminhos, por isso o `GROUP BY actor_id` com `min(distance)` fica com a distância mais curta. O ator inicial é excluído.

### Porque é que a query termina

O PostgreSQL repete o passo recursivo até ele não devolver nenhuma linha. A condição `r.distance < 3` garante que isso acontece: as linhas com distância 3 já não geram novas linhas, por isso há no máximo 3 passos.

### Como evita revisitar atores

O `path` guarda os atores do caminho atual. A condição `not c.other_actor_id = any(r.path)` impede o passo recursivo de voltar a um ator que já lá está, por exemplo A → B → A. Sem isto não havia ciclos infinitos, porque o limite da distância já os corta, mas havia muitos caminhos inúteis.

O `path` só evita repetições dentro de um caminho. O mesmo ator pode aparecer em caminhos diferentes, e é por isso que o resultado final precisa do `min(distance)`.

### Resultado

Para o ator 1: 199 atores, 79 à distância 1 e 120 à distância 2, em cerca de 0,35 s.

Não aparece nenhum ator à distância 3, e isto não é um erro. Na Pagila, quaisquer dois atores estão ligados em no máximo 2 graus, ou seja, o grafo tem diâmetro 2. Cada ator entra em cerca de 27 filmes, que têm em média 5 atores, por isso só a distância 1 já cobre perto de 40% dos 200 atores. O limite de 3 continua a ser necessário: é ele que garante que a query termina num grafo com ciclos.
