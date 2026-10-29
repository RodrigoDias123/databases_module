-- Exercise 07: Indexes and optimisation — setup
--
-- Cria a base de dados vazia: ./scripts/create-db.sh ex07 --reset
-- Depois: psql -d ex07 -v ON_ERROR_STOP=1 -f exercises/07-indexes/exercise/setup.sql
--
-- Passo 1: corre este ficheiro uma vez para criar a big_rental (2 000 000 linhas, sem índices).
-- Passo 2: confirma com \d big_rental que a tabela não tem nenhum índice.
-- Passo 3: confirma o número de linhas: SELECT count(*) FROM big_rental;  -> 2000000
-- Passo 4: volta a correr este ficheiro sempre que precisares de recomeçar
--          (por exemplo entre as duas medições da tarefa 5). O DROP no início
--          apaga a tabela e todos os índices dela.

DROP TABLE IF EXISTS big_rental;

SELECT setseed(0.1);
CREATE TABLE big_rental AS
SELECT g AS id,
       (random() * 599 + 1)::int                 AS customer_id,
       now() - random() * interval '3 years'      AS rented_at,
       CASE WHEN random() < 0.03 THEN NULL ELSE now() END AS returned_at
FROM generate_series(1, 2000000) AS g;
VACUUM ANALYZE big_rental;




