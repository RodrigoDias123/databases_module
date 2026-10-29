-- Exercise 07: Indexes and optimisation — análise das queries
--
-- Antes: corre setup.sql (a tabela começa sem índices).
-- Corre este ficheiro por partes no psql (copia secção a secção), não de uma vez:
-- precisas de ver cada plano e de correr cada EXPLAIN 3 vezes.
--
-- Para cada query (Q1 a Q5) segue sempre os mesmos passos:
--   Passo A: lê a query e escreve no README, em 1 ou 2 frases, o que ela devolve.
--   Passo B: corre o EXPLAIN (ANALYZE, BUFFERS) SEM índices, 3 vezes.
--            Guarda a "Execution Time" das 3 e fica com a mediana (o valor do meio).
--            Copia para o README as linhas-chave do plano: o nó (Seq Scan, ...),
--            o "Rows Removed by Filter" e o "Buffers: shared hit/read".
--   Passo C: pensa que colunas aparecem no WHERE e no ORDER BY e cria o índice
--            (escreve o CREATE INDEX aqui E em indexes.sql se o mantiveres).
--   Passo D: corre o mesmo EXPLAIN mais 3 vezes, mediana outra vez,
--            e anota o nó usado depois (Index Scan, Index Only Scan, Bitmap Heap Scan...).
--   Passo E: se o plano não mudou ou o tempo não melhorou, apaga o índice
--            (DROP INDEX ...) e explica no README porquê, com o plano como prova.
--
-- Dica: a seguir a criar um índice corre ANALYZE big_rental; para o planner
--       ter estatísticas atualizadas.

\timing on


-- =====================================================================
-- Q1
-- =====================================================================
--    Passo 1: o que devolve? (um número: alugueres do cliente 42 que ainda...?)
--    Passo 2: EXPLAIN sem índice, 3 vezes, mediana.
--    Passo 3: o WHERE filtra por duas colunas. Pensa:
--             - um índice só em customer_id chega?
--             - um índice com as duas colunas?
--             - um índice parcial (CREATE INDEX ... WHERE returned_at IS NULL),
--               já que só 3% das linhas têm returned_at a NULL?
--             Experimenta pelo menos duas opções e compara o tamanho
--             (SELECT pg_size_pretty(pg_relation_size('nome_do_indice'));) e o tempo.
--    Passo 4: repara se o plano final é Index Only Scan ou Bitmap Heap Scan e porquê.
--    Passo 5: fica só com o índice que ganhou e apaga os outros.

EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM big_rental WHERE customer_id = 42 AND returned_at IS NULL;

-- Opções testadas (uma de cada vez, com DROP INDEX entre elas):
--   (customer_id)                              14 MB   Bitmap Heap Scan   3.7 ms
--   (customer_id, returned_at)                 14 MB   Index Only Scan    0.045 ms
--   (customer_id) WHERE returned_at IS NULL   432 kB   Index Only Scan    0.055 ms  <- mantido
CREATE INDEX big_rental_customer_open_idx ON big_rental (customer_id) WHERE returned_at IS NULL;
ANALYZE big_rental;

EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM big_rental WHERE customer_id = 42 AND returned_at IS NULL;



-- =====================================================================
-- Q2
-- =====================================================================
--    Passo 1: o que devolve? (alugueres de que período? por que ordem?)
--    Passo 2: EXPLAIN sem índice, 3 vezes, mediana.
--             Repara que, além do Seq Scan, aparece um nó Sort.
--    Passo 3: cria um índice na coluna do WHERE, que é também a do ORDER BY.
--    Passo 4: EXPLAIN outra vez: o nó Sort desapareceu? Porquê?
--             (o índice já guarda os valores ordenados)

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental WHERE rented_at >= now() - interval '1 day' ORDER BY rented_at;

CREATE INDEX big_rental_rented_at_idx ON big_rental (rented_at);
ANALYZE big_rental;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental WHERE rented_at >= now() - interval '1 day' ORDER BY rented_at;
-- Resultado: Bitmap Heap Scan + Sort (as ~1 900 linhas estão espalhadas por ~1 700
-- páginas, por isso o planner prefere o bitmap e ordenar 122 kB em memória).



-- =====================================================================
-- Q3
-- =====================================================================
--    Passo 1: o que devolve? (os alugueres de que dia?)
--    Passo 2: EXPLAIN sem índice, 3 vezes, mediana.
--    Passo 3: já tens o índice em rented_at da Q2. Corre o EXPLAIN outra vez:
--             o planner usa-o? Repara no rented_at::date no WHERE — o índice guarda
--             rented_at, não rented_at::date.
--    Passo 4: tenta criar um índice de expressão: CREATE INDEX ... ((rented_at::date));
--             Lê o erro. Dica: rented_at é timestamptz, e a conversão para date
--             depende do fuso horário da sessão (a função não é IMMUTABLE).
--    Passo 5: reescreve a query sem mexer na coluna: troca o cast por um intervalo
--             rented_at >= <início do dia> AND rented_at < <início do dia seguinte>.
--    Passo 6: confirma que a query reescrita devolve o MESMO número de linhas que
--             a original (SELECT count(*) ... nas duas versões).
--    Passo 7: EXPLAIN da query reescrita, 3 vezes, mediana. Que nó aparece agora?

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental WHERE rented_at::date = current_date - 10;

-- Com big_rental_rented_at_idx criado, a original continua em Parallel Seq Scan:
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental WHERE rented_at::date = current_date - 10;

-- Índice de expressão: falha com
-- ERROR:  functions in index expression must be marked IMMUTABLE
-- CREATE INDEX big_rental_rented_date_idx ON big_rental ((rented_at::date));

-- Query reescrita (mesmas 1838 linhas, confirmado com count(*)):
SELECT count(*) FROM big_rental WHERE rented_at::date = current_date - 10;
SELECT count(*) FROM big_rental
WHERE rented_at >= (current_date - 10)::timestamptz
  AND rented_at <  (current_date - 9)::timestamptz;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental
WHERE rented_at >= (current_date - 10)::timestamptz
  AND rented_at <  (current_date - 9)::timestamptz;



-- =====================================================================
-- Q4
-- =====================================================================
--    Passo 1: o que devolve? (uma linha por cliente com...?)
--    Passo 2: EXPLAIN sem índice, 3 vezes, mediana.
--    Passo 3: calcula quantas linhas passam no filtro:
--             SELECT count(*) FROM big_rental WHERE returned_at IS NOT NULL;
--             Que percentagem da tabela é? (lembra-te: só 3% são NULL)
--    Passo 4: cria um índice que te pareça útil (por exemplo em returned_at,
--             ou em (customer_id) WHERE returned_at IS NOT NULL) e corre o EXPLAIN.
--    Passo 5: o planner usou o índice? Se não, força-o só para comparar:
--             SET enable_seqscan = off;  EXPLAIN ...;  RESET enable_seqscan;
--             Compara o tempo e os buffers com o Seq Scan.
--    Passo 6: explica no README: quando a query lê quase a tabela toda, ler o
--             índice + saltar para a tabela custa mais do que ler a tabela seguida.
--    Passo 7: se o índice não melhorou nada, apaga-o e escreve "none" no README.

EXPLAIN (ANALYZE, BUFFERS)
SELECT customer_id, count(*) FROM big_rental WHERE returned_at IS NOT NULL GROUP BY customer_id;

-- 1 939 920 de 2 000 000 linhas (97%) passam no filtro.
CREATE INDEX q4_partial ON big_rental (customer_id) WHERE returned_at IS NOT NULL;
VACUUM ANALYZE big_rental;

-- O planner continua a escolher o Parallel Seq Scan:
EXPLAIN (ANALYZE, BUFFERS)
SELECT customer_id, count(*) FROM big_rental WHERE returned_at IS NOT NULL GROUP BY customer_id;

-- Forçado: Parallel Index Only Scan, ~67 ms contra ~70 ms do Seq Scan (ruído).
-- Com (returned_at) forçado: Parallel Index Scan, ~79 ms (pior).
SET enable_seqscan = off;
EXPLAIN (ANALYZE, BUFFERS)
SELECT customer_id, count(*) FROM big_rental WHERE returned_at IS NOT NULL GROUP BY customer_id;
RESET enable_seqscan;

DROP INDEX q4_partial;   -- none



-- =====================================================================
-- Q5
-- =====================================================================
--    Passo 1: o que devolve? (alugueres de que clientes, em que período, por que ordem?)
--    Passo 2: EXPLAIN sem índice, 3 vezes, mediana.
--             (atenção: se já tens índices da Q1/Q2, o plano "antes" pode já usá-los.
--              Para um "antes" justo, corre setup.sql de novo ou faz DROP desses índices.)
--    Passo 3: o WHERE tem uma igualdade (customer_id IN ...) e um intervalo (rented_at >= ...).
--             Cria um índice composto. Qual coluna vem primeiro? Regra: primeiro a
--             coluna da igualdade, depois a do intervalo/ORDER BY.
--    Passo 4: EXPLAIN outra vez. Experimenta também a ordem inversa das colunas
--             e compara os buffers lidos.
--    Passo 5: ainda há um nó Sort? Porquê? (o IN junta 3 "fatias" do índice)

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental
WHERE customer_id IN (7, 42, 99) AND rented_at >= now() - interval '30 days'
ORDER BY rented_at DESC;

-- (customer_id, rented_at): 0.73 ms, 11 buffers no índice  <- mantido
-- (rented_at, customer_id): 1.9 ms, 222 buffers no índice
CREATE INDEX big_rental_customer_rented_at_idx ON big_rental (customer_id, rented_at);
ANALYZE big_rental;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental
WHERE customer_id IN (7, 42, 99) AND rented_at >= now() - interval '30 days'
ORDER BY rented_at DESC;



-- =====================================================================
-- Tarefa 5: custo de escrita
-- =====================================================================
--    Passo 1: corre setup.sql (tabela sem índices).
--    Passo 2: com \timing on, corre o INSERT abaixo e anota o tempo.
--             Repete 3 vezes (setup.sql -> INSERT, sempre a partir da tabela limpa,
--             porque o INSERT usa sempre os mesmos ids) e fica com a mediana.
--    Passo 3: corre setup.sql, depois indexes.sql (todos os índices que mantiveste).
--    Passo 4: corre o INSERT outra vez e anota o tempo (de novo 3 vezes, recriando
--             a tabela e os índices entre cada uma).
--    Passo 5: explica no README a diferença: cada linha inserida obriga a atualizar
--             todos os índices da tabela, não só a tabela.

--    Resultado: sem índices 28 ms (27.3 / 28.2 / 27.9); com os 3 índices 134 ms
--    (131.1 / 134.5 / 133.5).

-- INSERT INTO big_rental SELECT g, 1, now(), NULL FROM generate_series(2000001, 2100000) g;
