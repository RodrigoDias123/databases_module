-- Challenge 06: gaps and islands
--
-- Corre numa cópia limpa: ./scripts/create-db.sh ch06 --pagila --reset
-- Depois: psql -d ch06 -v ON_ERROR_STOP=1 -f exercises/06-window/challenge/islands.sql
--
-- Uma ilha é uma sequência de meses de calendário consecutivos em que o cliente
-- alugou pelo menos um filme. Março e abril de 2022 não têm alugueres nenhuns.
-- Só window functions e operações de conjuntos: sem código procedural nem CTE recursivo.
--
-- Esperado: a 1.ª linha é o cliente 70 com 19 meses (2023-06 a 2024-12);
-- a 10.ª linha é o cliente 556 com 16 meses.
--
-- Passo 1: meses com atividade por cliente.
--          select distinct customer_id, date_trunc('month', rental_date)::date as month
--          from rental
--          (distinct é importante: um cliente com 3 alugueres no mesmo mês conta 1 vez).
--
-- Passo 2: transforma cada mês num número inteiro sequencial, para que meses
--          consecutivos difiram exatamente 1:
--          month_n = extract(year from month) * 12 + extract(month from month)
--          (assim dezembro -> janeiro também dá +1).
-- Passo 3: numera os meses de cada cliente por ordem:
--          rn = row_number() over (partition by customer_id order by month)
--
-- Passo 4: a técnica: grp = month_n - rn.
--          Em meses consecutivos, month_n e rn sobem os dois 1 -> a diferença fica igual.
--          Quando há um buraco, month_n salta mais do que rn -> a diferença muda.
--          Cada valor de grp (por cliente) é uma ilha.
--
-- Passo 5: agrupa por customer_id e grp:
--          min(month) as first_month, max(month) as last_month, count(*) as months.
--
-- Passo 6: fica com a ilha mais longa de cada cliente; em empate, a mais antiga:
--          row_number() over (partition by customer_id order by months desc, first_month)
--          e filtra = 1.
--
-- Passo 7: ordena por months desc, customer_id e limit 10.
--          Mostra first_month e last_month no formato 'YYYY-MM' (to_char) se quiseres
--          igual ao enunciado.
--
-- Passo 8: confirma o cliente 70 em 1.º (19 meses) e o 556 em 10.º (16 meses),
--          e copia as 10 linhas para o README.md com a explicação do passo 4.

select customer_id, to_char(first_month, 'YYYY-MM') as first_month,
       to_char(last_month, 'YYYY-MM') as last_month, months
from (
    select customer_id, first_month, last_month, months,
           row_number() over (partition by customer_id order by months desc, first_month) as rn
    from (
        select customer_id, min(month) as first_month, max(month) as last_month, count(*) as months
        from (
            select customer_id, month,
                   extract(year from month) * 12 + extract(month from month) as month_n,
                   row_number() over (partition by customer_id order by month) as rn
            from (
                select distinct customer_id, date_trunc('month', rental_date)::date as month
                from rental
            ) as months_per_customer
        ) as numbered_months
        group by customer_id, month_n - rn
    ) as islands
) as longest_islands
where rn = 1
order by months desc, customer_id
limit 10;

