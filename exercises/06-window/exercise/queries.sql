-- Exercise 06: Queries II, window functions and views
--
-- Corre numa cópia limpa: ./scripts/create-db.sh ex06 --pagila --reset
-- Depois: psql -d ex06 -v ON_ERROR_STOP=1 -f exercises/06-window/exercise/queries.sql
--
-- Escreve cada query por baixo do comentário da tarefa respetiva.
-- Confirma sempre o número de linhas e os valores esperados.

-- 1. Os 3 filmes mais alugados de cada categoria, por número de alugueres.
--    Filmes empatados partilham a posição; todos os filmes nas posições 1 a 3 aparecem.
--    Esperado: 56 linhas.
--
--    Passo 1: junta category -> film_category -> film -> inventory -> rental.
--    Passo 2: agrupa por categoria e filme e conta os alugueres (count(r.rental_id)).
--    Passo 3: num CTE, calcula a posição com uma window function
--             partition by categoria, order by alugueres desc.
--    Passo 4: escolhe entre rank() e dense_rank(): "partilham a posição e todos os
--             filmes nas posições 1 a 3 aparecem" -> testa os dois e vê qual dá 56.
--    Passo 5: na query exterior, filtra posição <= 3 (não dá para filtrar a window
--             function no WHERE da mesma query).
--    Passo 6: ordena por categoria, posição e título.

Select category, title, rentals, position
from (
    Select c.name as category, f.title, count(r.rental_id) as rentals,
           dense_rank() over (partition by c.category_id order by count(r.rental_id) desc) as position
    from category c
    join film_category fc on c.category_id = fc.category_id
    join film f on fc.film_id = f.film_id
    join inventory i on f.film_id = i.film_id
    join rental r on i.inventory_id = r.inventory_id
    group by c.category_id, f.film_id
) as ranked_films
where position <= 3
order by category, position, title;



-- 2. Receita por dia em julho de 2026, com o total acumulado do mês.
--    Colunas: day, revenue, running_total.
--    Esperado: 28 linhas; o último running_total é 2409.88.
--
--    Passo 1: filtra payment com payment_date >= '2026-07-01' e < '2026-08-01'.
--    Passo 2: agrupa por payment_date::date as day e calcula sum(amount) as revenue.
--    Passo 3: adiciona sum(sum(amount)) over (order by day) as running_total
--             (a window function corre depois do GROUP BY, por isso soma as somas).
--    Passo 4: ordena por day e confirma que a última linha tem 2409.88.

Select payment_date::date as day, sum(amount) as revenue,
       sum(sum(amount)) over (order by payment_date::date) as running_total
from payment 
where payment_date >= '2026-07-01' and payment_date < '2026-08-01'
group by payment_date::date 
order by day;



-- 3. Receita por mês para todo o conjunto de dados, com a variação face ao mês
--    anterior em valor e em percentagem (1 casa decimal).
--    Esperado: 55 linhas; julho de 2026 tem 2409.88, o mês anterior 2105.73,
--    variação de 304.15 e 14.4%.
--
--    Passo 1: num CTE, agrupa payment por date_trunc('month', payment_date)::date
--             as month e calcula sum(amount) as revenue.
--    Passo 2: na query exterior, usa lag(revenue) over (order by month) para obter
--             a receita do mês anterior.
--    Passo 3: variação em valor = revenue - lag(...).
--    Passo 4: variação em % = round(100 * (revenue - lag) / lag, 1).
--             O primeiro mês fica a NULL (não tem anterior), e isso está certo.
--    Passo 5: ordena por month e confirma a linha de 2026-07-01.

select month, revenue,
       revenue - lag(revenue) over (order by month) as variation_value,
       round(100 * (revenue - lag(revenue) over (order by month)) / lag(revenue) over (order by month), 1) as variation_percentage
from (
    select date_trunc('month', payment_date)::date as month, sum(amount) as revenue
    from payment
    group by date_trunc('month', payment_date)::date
) as monthly_revenue
order by month;


-- 4. A posição de cada cliente no ranking da sua loja por total pago.
--    Clientes sem pagamentos contam como 0; clientes empatados partilham a posição.
--    Esperado: 999 linhas; o cliente 468 é o primeiro da loja 1 (344.06) e o
--    cliente 526 é o primeiro da loja 2 (358.12).
--
--    Passo 1: parte de customer e faz LEFT JOIN a payment (para não perder clientes
--             sem pagamentos).
--    Passo 2: agrupa por customer_id e store_id e usa coalesce(sum(p.amount), 0)
--             as total_paid.
--    Passo 3: adiciona rank() over (partition by store_id order by total_paid desc)
--             as position.
--    Passo 4: ordena por store_id, position, customer_id.
--    Passo 5: confirma 999 linhas e os clientes 468 e 526 em primeiro.
--    Dica: guarda esta query num CTE ou numa view, porque a tarefa 5 reutiliza-a.

Select c.customer_id, c.store_id, coalesce(sum(p.amount), 0) as total_paid,
       rank() over (partition by c.store_id order by coalesce(sum(p.amount), 0) desc) as position
from customer c
left join payment p on c.customer_id = p.customer_id
group by c.customer_id, c.store_id
order by c.store_id, position, c.customer_id;



-- 5. Os 5 melhores clientes de cada loja por total pago.
--    Esperado: 10 linhas.
--
--    Passo 1: reutiliza o cálculo da tarefa 4 (copia-o para um CTE).
--    Passo 2: para garantir exatamente 5 por loja, usa row_number() em vez de rank()
--             (com rank() um empate na 5.ª posição dava mais linhas).
--    Passo 3: filtra posição <= 5 na query exterior.
--    Passo 4: ordena por store_id e posição e confirma 10 linhas.

Select customer_id, store_id, total_paid, position
from (
    Select c.customer_id, c.store_id, coalesce(sum(p.amount), 0) as total_paid,
           row_number() over (partition by c.store_id order by coalesce(sum(p.amount), 0) desc) as position
    from customer c
    left join payment p on c.customer_id = p.customer_id
    group by c.customer_id, c.store_id
) as ranked_customers
where position <= 5
order by store_id, position, customer_id; 


-- 6. Vista materializada da receita mensal, com refresh.
--    Done when: a vista materializada só muda depois do refresh.
--    O output destes passos vai para o README.md.
--
--    Passo 1: drop materialized view if exists monthly_revenue; (para o script
--             poder correr mais do que uma vez).
--    Passo 2: create materialized view monthly_revenue as
--             select date_trunc('month', payment_date)::date as month,
--                    sum(amount) as revenue
--             from payment group by 1;
--    Passo 3: cria um unique index em monthly_revenue (month)
--             (é obrigatório para o REFRESH ... CONCURRENTLY).
--    Passo 4: lê a receita de um mês (ex.: 2026-07-01) da vista -> 2409.88.
--    Passo 5: dentro de uma transação (begin), insere um pagamento novo nesse mês
--             em payment (usa um customer_id, staff_id e rental_id existentes).
--    Passo 6: lê outra vez a vista -> o valor NÃO mudou (está desatualizada).
--    Passo 7: refresh materialized view concurrently monthly_revenue;
--    Passo 8: lê outra vez a vista -> agora o valor já inclui o pagamento novo.
--    Passo 9: rollback (ou apaga o pagamento e faz refresh outra vez) para deixar
--             a base de dados como estava.
--             Atenção: REFRESH ... CONCURRENTLY não pode correr dentro de uma
--             transação; se usares begin/rollback, usa o REFRESH sem CONCURRENTLY
--             nesse passo, ou faz o insert fora da transação e apaga-o no fim.

drop materialized view if exists monthly_revenue;

create materialized view monthly_revenue as
select date_trunc('month', payment_date)::date as month, sum(amount) as revenue
from payment
group by 1;

create unique index on monthly_revenue (month);

-- Antes: 2409.88
select month, revenue from monthly_revenue where month = '2026-07-01';

-- Pagamento novo de 10.00 em julho de 2026, num aluguer que já existe
insert into payment (customer_id, staff_id, rental_id, amount, payment_date)
select customer_id, staff_id, rental_id, 10.00, '2026-07-15 12:00'
from rental
order by rental_id
limit 1
returning payment_id \gset

-- Sem refresh: continua 2409.88
select month, revenue from monthly_revenue where month = '2026-07-01';

refresh materialized view concurrently monthly_revenue;

-- Depois do refresh: 2419.88
select month, revenue from monthly_revenue where month = '2026-07-01';

-- Limpeza: apaga o pagamento e volta a 2409.88
delete from payment where payment_id = :payment_id;
refresh materialized view concurrently monthly_revenue;
select month, revenue from monthly_revenue where month = '2026-07-01';





