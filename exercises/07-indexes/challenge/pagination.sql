-- Challenge 07: Indexes and optimisation — paginação OFFSET vs keyset
--
-- Base de dados própria, com a big_rental do exercício:
--   ./scripts/create-db.sh ch07 --reset
--   psql -d ch07 -v ON_ERROR_STOP=1 -f exercises/07-indexes/exercise/setup.sql
-- Depois: psql -d ch07 -v ON_ERROR_STOP=1 -f exercises/07-indexes/challenge/pagination.sql
--
-- Tem de correr com o psql, porque a tarefa 3 usa \gset.
-- Escreve cada comando por baixo do comentário da tarefa respetiva.
-- Páginas de 20 linhas, ordenadas por rented_at DESC, id DESC.
-- A página 5 000 começa depois de 4 999 * 20 = 99 980 linhas.

\timing on


-- 1. Cria um índice com a mesma ordem da paginação.
--
--    Passo 1: começa com DROP INDEX IF EXISTS <nome>; para o ficheiro poder
--             correr mais do que uma vez.
--    Passo 2: cria o índice nas duas colunas do ORDER BY, pela mesma ordem e com
--             o mesmo sentido: (rented_at DESC, id DESC).
--    Passo 3: corre ANALYZE big_rental; para o planner ter estatísticas atualizadas.
--    Passo 4: confirma com \d big_rental que o índice aparece.

DROP INDEX IF EXISTS big_rental_rented_at_id_idx;
CREATE INDEX big_rental_rented_at_id_idx
ON big_rental (rented_at DESC, id DESC);
ANALYZE big_rental;



-- 2. Página 5 000 com OFFSET.
--
--    Passo 1: escreve a query: SELECT id, rented_at, customer_id FROM big_rental
--             ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20;
--             (usa as mesmas colunas da query keyset da tarefa 3, para comparar)
--    Passo 2: corre-a com EXPLAIN (ANALYZE, BUFFERS) 3 vezes e fica com a mediana
--             do "Execution Time".
--    Passo 3: copia para o README o nó do plano (Limit -> Index Scan ...) e repara
--             no "rows" do Index Scan: quantas linhas leu para devolver 20?
--    Passo 4: para a explicação do README, corre também com OFFSET 0 e com
--             OFFSET 999980 e compara os tempos. O que acontece quando a página cresce?
--    Passo 5: corre a query sem EXPLAIN e guarda as 20 linhas (vais compará-las na tarefa 3).

Select id, rented_at, customer_id FROM big_rental
ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20;
EXPLAIN (ANALYZE, BUFFERS) SELECT id, rented_at, customer_id FROM big_rental
ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20;


-- 3. Página 5 000 com keyset pagination.
--
--    Passo 1: guarda a última linha da página 4 999 em variáveis do psql
--             (é a linha 99 980, por isso OFFSET 99979 LIMIT 1). O \gset cria as
--             variáveis :last_rented_at e :last_id. O comando já está escrito abaixo.
--    Passo 2: confirma os valores com \echo :last_rented_at :last_id
--    Passo 3: corre a query keyset (já escrita abaixo) sem EXPLAIN e compara as
--             20 linhas com as da tarefa 2. Têm de ser exatamente as mesmas.
--             Dica: para provar no SQL, usa EXCEPT entre as duas queries
--             (nos dois sentidos) e confirma que dá 0 linhas.
--    Passo 4: corre a query keyset com EXPLAIN (ANALYZE, BUFFERS) 3 vezes e fica com
--             a mediana. Repara no "Index Cond" e no "rows" do Index Scan: quantas
--             linhas leu agora?
--    Passo 5: compara no README os planos, os buffers e os tempos das tarefas 2 e 3.

SELECT rented_at AS last_rented_at, id AS last_id
FROM big_rental ORDER BY rented_at DESC, id DESC OFFSET 99979 LIMIT 1 \gset
\echo :last_rented_at :last_id

SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;

-- As duas EXCEPT têm de dar 0 linhas: as duas páginas são iguais.
(SELECT id, rented_at, customer_id FROM big_rental
 ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20)
EXCEPT
(SELECT id, rented_at, customer_id FROM big_rental
 WHERE (rented_at, id) < (:'last_rented_at', :last_id)
 ORDER BY rented_at DESC, id DESC LIMIT 20);

(SELECT id, rented_at, customer_id FROM big_rental
 WHERE (rented_at, id) < (:'last_rented_at', :last_id)
 ORDER BY rented_at DESC, id DESC LIMIT 20)
EXCEPT
(SELECT id, rented_at, customer_id FROM big_rental
 ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20);

EXPLAIN (ANALYZE, BUFFERS) SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;






-- 4. Recria o índice com INCLUDE (customer_id) para ter um Index Only Scan.
--
--    Passo 1: faz DROP INDEX do índice da tarefa 1.
--    Passo 2: cria-o outra vez, com as mesmas colunas e INCLUDE (customer_id).
--             O INCLUDE guarda a coluna no índice sem a usar na ordenação.
--    Passo 3: corre VACUUM ANALYZE big_rental; para o visibility map ficar
--             atualizado (sem isto o Index Only Scan pode ter Heap Fetches > 0).
--    Passo 4: corre a query keyset com EXPLAIN (ANALYZE, BUFFERS) e confirma que o
--             nó é "Index Only Scan" e que "Heap Fetches: 0".
--    Passo 5: anota no README o tempo e os buffers, e compara com a tarefa 3.

Drop INDEX IF EXISTS big_rental_rented_at_id_idx;
CREATE INDEX big_rental_rented_at_id_idx
ON big_rental (rented_at DESC, id DESC) INCLUDE (customer_id);
VACUUM ANALYZE big_rental;
EXPLAIN (ANALYZE, BUFFERS) SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;

-- 5. Heap Fetches antes e depois do VACUUM.
--
--    Passo 1: corre o UPDATE (já escrito abaixo). Não muda nenhum valor, mas cria
--             uma nova versão de 1 em cada 50 linhas, e as páginas alteradas deixam
--             de estar marcadas como "toda visível" no visibility map.
--    Passo 2: corre a query keyset com EXPLAIN (ANALYZE, BUFFERS) e anota a linha
--             "Heap Fetches" (tem de ser > 0) e o tempo.
--    Passo 3: corre VACUUM big_rental;
--    Passo 4: corre outra vez o mesmo EXPLAIN e anota "Heap Fetches" (tem de ser 0)
--             e o tempo.
--    Passo 5: no README explica o que o VACUUM muda no visibility map e porque é
--             que isso faz os Heap Fetches descerem para 0.
--    Atenção: o autovacuum pode correr sozinho entre o UPDATE e o EXPLAIN. Se o
--             Heap Fetches já der 0 no passo 2, corre o EXPLAIN logo a seguir ao
--             UPDATE (ou desliga-o na tabela com
--             ALTER TABLE big_rental SET (autovacuum_enabled = off); e volta a ligar no fim).

UPDATE big_rental SET customer_id = customer_id WHERE id % 50 = 0;
EXPLAIN (ANALYZE, BUFFERS) SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;

VACUUM big_rental;
EXPLAIN (ANALYZE, BUFFERS) SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;  


