-- Exercise 07: Indexes and optimisation — índices mantidos
--
-- Corre depois de setup.sql: psql -d ex07 -v ON_ERROR_STOP=1 -f exercises/07-indexes/exercise/indexes.sql
--
-- Aqui ficam SÓ os índices que mostraram uma melhoria medida em analysis.sql.
-- Uma query que nenhum índice ajuda não tem entrada aqui (no README escreves "none").
--
-- Passo 1: para cada índice que mantiveste, copia o CREATE INDEX de analysis.sql
--          para a secção da query certa.
-- Passo 2: dá nomes claros aos índices (ex.: big_rental_<colunas>_idx) para os
--          reconheceres nos planos.
-- Passo 3: se um índice serve duas queries (ex.: Q2 e Q3 reescrita), escreve-o uma
--          vez só e indica no comentário as duas queries.
-- Passo 4: no fim fica o ANALYZE para o planner ter estatísticas dos índices novos.
-- Passo 5: testa: corre setup.sql e a seguir este ficheiro, e confirma com
--          \d big_rental que aparecem todos os índices.

-- Q1: índice parcial, só com as ~60 000 linhas por devolver (432 kB em vez de 14 MB).
--     Dá Index Only Scan: 20.2 ms -> 0.055 ms.
CREATE INDEX big_rental_customer_open_idx ON big_rental (customer_id) WHERE returned_at IS NULL;

-- Q2 e Q3 reescrita: intervalo em rented_at.
--     Q2: 52.4 ms -> 2.9 ms.  Q3 reescrita: 35.7 ms -> 2.6 ms.
CREATE INDEX big_rental_rented_at_idx ON big_rental (rented_at);

-- Q3: sem índice próprio. Como está escrita (rented_at::date) não usa nenhum índice,
--     e um índice de expressão em rented_at::date não pode ser criado (não é IMMUTABLE).
--     A versão reescrita usa big_rental_rented_at_idx.

-- Q4: none. Lê 97% da tabela; mesmo forçado, o melhor índice não ganha ao Seq Scan.

-- Q5: igualdade (customer_id IN) primeiro, intervalo (rented_at) depois.
--     34.9 ms -> 0.73 ms (a ordem inversa dá 1.9 ms).
CREATE INDEX big_rental_customer_rented_at_idx ON big_rental (customer_id, rented_at);

ANALYZE big_rental;
