# Challenge 05: Queries I, joins, aggregation, subqueries and CTEs

Obrigatório.

## Enunciado

Folder: `exercises/05-queries/challenge/`

**Goal.** Walk a graph stored in tables with a recursive CTE.

**Starting point.** A fresh copy of Pagila (`./scripts/create-db.sh ch05 --pagila --reset`). Two actors are connected when they appeared together in at least 3 films. The distance between two actors is the smallest number of connections between them ("degrees of separation").

**Tasks.**

1. Write a CTE `edge(actor_id, other_actor_id)` with every connected pair, in both directions.
2. Write a query with `WITH RECURSIVE` that, starting from actor 1, lists every actor reachable within 3 degrees with columns `actor_id`, `first_name`, `last_name`, `distance` (the shortest one), ordered by distance and `actor_id`. Actor 1 is not in the result. The query must stop on its own and must never revisit an actor on the same path (keep the path in an array).
3. Change the query to return the shortest path from actor 1 to actor 200 as the list of actor names, or an empty result if there is no path within 5 degrees.

**Deliverables.**

- `degrees.sql` with the queries of tasks 2 and 3.
- `README.md` with the number of actors at each distance, the result of task 3, and an explanation of how the query avoids running forever.

**Done when.** Task 2 returns data where you can identify relationships and you verify that there's no issues.

## Resposta

Ficheiro: [degrees.sql](degrees.sql). A partir da root do repositório:

```bash
./scripts/create-db.sh ch05 --pagila --reset
psql -d ch05 -v ON_ERROR_STOP=1 -f exercises/05-queries/challenge/degrees.sql
```

Por omissão parte do ator 1 e procura o caminho até ao ator 200. Para outros atores: `-v from_actor=42 -v to_actor=7`.

### O que o script faz

1. **`edge`** (tarefa 1): um self join de `film_actor` dá todos os pares de atores distintos que entraram no mesmo filme. `group by` com `having count(*) >= 3` deixa só os pares com pelo menos 3 filmes em comum, e cada par fica uma só vez. Como o self join junta (A, B) e (B, A), a ligação existe nos dois sentidos. São 1650 linhas, ou seja, 825 pares.
2. **`reach`** (`WITH RECURSIVE`):
   - **caso base**: o ator inicial, com `distance = 0` e `path = {1}`;
   - **passo recursivo**: a partir de cada ator do passo anterior, segue uma ligação de `edge`, soma 1 à distância e junta o novo ator ao `path`.
3. **Tarefa 2**: o mesmo ator pode ser alcançado por vários caminhos, por isso `group by actor_id` com `min(distance)` fica com a distância mais curta. O ator inicial é excluído, e o resultado é ordenado por `distance` e `actor_id`.
4. **Tarefa 3**: a mesma recursão, com limite de 5 e uma condição extra: um caminho que já chegou ao ator 200 não continua. Dos caminhos que acabam no ator 200 fica o mais curto (`order by distance, path limit 1`, para que um empate dê sempre o mesmo caminho). O `unnest(path) with ordinality` transforma os ids em nomes pela ordem do caminho. Se nenhum caminho chegar ao ator 200, o `limit 1` não recebe linhas e o resultado fica vazio.

### Porque é que a query termina

O PostgreSQL repete o passo recursivo até ele não devolver nenhuma linha. A condição `r.distance < 3` (ou `< 5` na tarefa 3) garante que isso acontece: as linhas com a distância máxima já não geram novas linhas, por isso há no máximo 3 (ou 5) passos.

O `path` guarda os atores do caminho atual, e `not e.other_actor_id = any(r.path)` impede o passo recursivo de voltar a um ator que já lá está, por exemplo A → B → A. Este grafo tem ciclos. Sem o `path`, o limite de distância continuava a cortar a recursão, mas a cada passo apareciam caminhos que só andam para trás e para a frente. Sem o limite e sem o `path`, a recursão nunca parava.

O `path` só evita repetições dentro de um caminho. O mesmo ator pode aparecer em caminhos diferentes, e é por isso que a tarefa 2 precisa do `min(distance)`.

### Resultado da tarefa 2

141 atores a no máximo 3 graus do ator 1 (PENELOPE GUINESS):

| distance | atores |
|---------:|-------:|
| 1 | 3 |
| 2 | 23 |
| 3 | 115 |

Início e fim do resultado:

```
 actor_id | first_name  |  last_name   | distance
----------+-------------+--------------+----------
        4 | JENNIFER    | DAVIS        |        1
       20 | LUCILLE     | TRACY        |        1
       64 | RAY         | JOHANSSON    |        1
        7 | GRACE       | MOSTEL       |        2
       13 | UMA         | WOOD         |        2
...
      196 | BELA        | WALKEN       |        3
(141 rows)
```

### Resultado da tarefa 3

```
 distance |                                          path
----------+-----------------------------------------------------------------------------------------
        4 | {"PENELOPE GUINESS","LUCILLE TRACY","GINA DEGENERES","ANGELINA ASTAIRE","THORA TEMPLE"}
(1 row)
```

### Verificação

- **Distância 1.** Os 3 atores à distância 1 são os únicos que fizeram pelo menos 3 filmes com o ator 1: JENNIFER DAVIS (4), LUCILLE TRACY (3) e RAY JOHANSSON (3). Os 18 atores seguintes têm só 2 filmes em comum com ele, por isso não estão ligados ao ator 1 e só podem aparecer a distância 2 ou mais.
- **Caminho da tarefa 3.** Cada passo é uma ligação real. Filmes em comum: GUINESS e TRACY 3, TRACY e DEGENERES 4, DEGENERES e ASTAIRE 3, ASTAIRE e TEMPLE 3.
- **O ator 200 está mesmo a 4 graus.** Não aparece no resultado da tarefa 2, por isso não há caminho com 3 ligações ou menos.
- **Contagem independente.** Um BFS em Python sobre as mesmas 1650 ligações dá as mesmas contagens (3, 23 e 115) e o ator 200 à distância 4. Fora do limite de 3 graus ficam 53 atores a distância 4 e 4 a distância 5. RUSSELL CLOSE (183) não tem nenhuma ligação: não fez 3 filmes com nenhum outro ator.
