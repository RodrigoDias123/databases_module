# Exercício 01: Database engines and diagnosis

Ficheiros entregues:

- `README.md`: este ficheiro, com o screenshot e as respostas às tarefas 2 a 5.
- [shop.json](shop.json): os dados da loja, copiados do enunciado sem alterações.
- [docker-compose-ps.png](docker-compose-ps.png): o screenshot da tarefa 1.

## 1. `docker compose ps`

![docker compose ps](docker-compose-ps.png)

Os três motores (`postgres:18`, `mongo:8`, `redis:8`) estão `Up (healthy)`.

## 2. Modelo de dados do `shop.json`

**Entidades e campos**

| Entidade | Campos | Identificador |
|----------|--------|---------------|
| `customers` | `id`, `name`, `email`, `city` | `id` |
| `orders` | `id`, `customer_id`, `customer_name`, `customer_email`, `items`, `total`, `date` | `id` (mas repete-se, ver problema 3) |
| `products` | `name`, `price`, `stock` | nenhum, só o `name` |

**Relações**

- **Cliente 1:N encomendas.** `orders.customer_id` aponta para `customers.id`. Nada obriga o cliente a existir. Além disso, `customer_name` e `customer_email` são cópias dos dados do cliente dentro de cada encomenda.
- **Encomenda N:M produtos.** Está escondida dentro da string `items` (`"Keyboard x1; Mouse x2"`). Cada parte liga a encomenda a um produto pelo **nome** e tem uma quantidade. Num modelo relacional isto seria uma entidade `order_item (order_id, product_id, quantity, unit_price)`.

## 3. Problemas no `shop.json`

| # | Linha | Tipo de problema | O que pode correr mal |
|---|-------|------------------|-----------------------|
| 1 | 7, 9, 11 | **Dados duplicados** (`customer_name` e `customer_email` copiados para cada encomenda) | Na linha 11 o email do cliente 1 é `ana.silva@example.com`, mas na linha 3 é `ana@example.com`. Os dados já divergiram e não se sabe qual está certo. Se a cliente mudar de email, é preciso atualizar todas as encomendas. |
| 2 | 9 | **Falta uma regra de integridade** (chave estrangeira): `customer_id: 3` não existe em `customers` | É uma encomenda órfã. A "Marta Reis" só existe dentro desta encomenda, por isso não se consegue listar como cliente nem contactar de forma fiável. O email `marta@example` nem sequer é válido. |
| 3 | 11 | **Falta uma regra de integridade** (chave primária): `id: 2` repetido | "A encomenda 2" passa a significar duas encomendas. Um update ou um delete pelo `id` pode afetar a errada, ou as duas. |
| 4 | 8, 10, 12 | **Lista guardada num único campo** (`items` em texto) | Para saber quantos ratos se venderam é preciso fazer *parse* da string em cada encomenda. Não há ligação a `products`: o `Monitor` (linha 10) nem existe no catálogo. A quantidade `x-1` (linha 12) é negativa e nada a impede. |
| 5 | 8, 10, 12 | **Tipo errado**: `total` é a string `"59.90"`, a string `"abc"` e o número `12.5` | Somar o total das vendas falha ou concatena texto. `"abc"` não é um valor monetário. Na linha 12 o total também não bate com os itens (-1 rato a 15 dá -15, não 12.5), porque é um valor calculado guardado sem nenhuma regra. |
| 6 | 8, 10, 12 | **Formato inconsistente** nas datas: `07/10/2026` contra `2026-10-08` | `07/10/2026` tanto pode ser 7 de outubro como 10 de julho. Ordenar ou filtrar por data como texto dá resultados errados (`"07/10..."` fica antes de `"2026-..."`). |
| 7 | 16 | **Tipo errado** e **falta uma regra de integridade**: `price: "15"` é string e `stock: -2` é negativo | O preço não entra em contas sem conversão. O stock negativo mostra que se vendeu o que não havia, porque nada verifica `stock >= 0`. |
| 8 | 15, 16 | **Falta uma chave primária** nos produtos (só o `name` os identifica) | Mudar o nome de um produto (por exemplo de "Mouse" para "Rato") parte a ligação com todas as encomendas que o referem. |

## 4. 100 000 encomendas e dois pedidos ao mesmo tempo

**Com 100 000 encomendas.** Cada encomenda ocupa cerca de 200 bytes, por isso o ficheiro passa a ter uns 20 MB.

- **Encontrar as encomendas de um cliente:** a aplicação tem de ler e fazer *parse* dos 20 MB inteiros e depois percorrer as 100 000 encomendas uma a uma, porque não há índice por `customer_id`. O custo cresce com o tamanho do ficheiro (O(n)), mesmo que o cliente só tenha 2 encomendas. Numa tabela PostgreSQL com índice em `customer_id`, a pesquisa vai diretamente às linhas desse cliente.
- **Acrescentar uma encomenda:** para escrever 200 bytes, a aplicação lê 20 MB, carrega tudo em memória, acrescenta a encomenda e volta a escrever os 20 MB. Cada pedido fica mais lento à medida que a loja cresce. Se o processo falhar a meio da escrita, o ficheiro fica truncado e perdem-se **todas** as encomendas, não só a nova. Um `INSERT` no PostgreSQL escreve só a linha nova, e o WAL garante que um commit sobrevive a um crash.

**Dois pedidos a acrescentar uma encomenda ao mesmo tempo.**

1. O pedido A lê o ficheiro, que tem as encomendas 1 e 2.
2. O pedido B lê a mesma versão do ficheiro.
3. A acrescenta a encomenda 3 e escreve o ficheiro.
4. B acrescenta a sua encomenda (também com `id` 3, porque calculou `max(id) + 1` sobre a mesma versão) e escreve o ficheiro por cima.

A encomenda de A desaparece sem nenhum erro (*lost update*). Se os ids forem gerados assim, aparecem ids repetidos, como o `id: 2` da linha 11. Um pedido pode também ler o ficheiro enquanto outro o está a escrever e apanhar JSON inválido. O PostgreSQL evita isto porque cada `INSERT` é uma transação que acrescenta só a sua linha, o `GENERATED ALWAYS AS IDENTITY` dá ids únicos mesmo com pedidos em simultâneo, e o MVCC deixa os leitores ver sempre uma versão consistente. O challenge mostra isto com números.

## 5. Que motor para cada dado

Para cada dado fiz as perguntas da sessão: não se pode perder nem contradizer? É lido como um todo e a forma varia? Muda muitas vezes por segundo e pode ser reconstruído ou expirar?

| Dado | Motor | Porquê |
|------|-------|--------|
| Clientes | **PostgreSQL** | Não se podem perder nem contradizer. A estrutura é fixa e as encomendas referem-nos, por isso precisam de chave primária, `email` com `UNIQUE` e chaves estrangeiras a apontar para eles. |
| Encomendas | **PostgreSQL** | São dinheiro: não se podem perder. Precisam de chave estrangeira para o cliente, uma tabela `order_item` com chave estrangeira para o produto, `numeric` para o total, `date` para a data e `CHECK (quantity > 0)`. Criar a encomenda e baixar o stock tem de acontecer numa **transação**: ou tudo ou nada. |
| Produtos | **PostgreSQL** | São referidos pelas linhas das encomendas e precisam de `CHECK (price >= 0)` e `CHECK (stock >= 0)`, que teriam evitado o `stock: -2`. Só faria sentido passar o catálogo para MongoDB se cada categoria tivesse atributos diferentes (tamanho, voltagem, cor). Aqui todos têm os mesmos três campos. |
| Últimos 10 produtos vistos por um cliente | **Redis** | Muda a cada clique, é lido como um todo, e perdê-lo não faz mal (no pior caso a lista fica vazia). Uma lista por cliente resolve: `LPUSH viewed:<customer_id> <product_id>` seguido de `LTRIM viewed:<customer_id> 0 9`, com `EXPIRE` para limpar clientes inativos. |
| Visualizações de cada página de produto hoje | **Redis** | É um contador incrementado muitas vezes por segundo, e o `INCR` é atómico e corre em memória. Uma chave por dia, por exemplo `views:2026-10-28:<product_id>` com `EXPIRE` de alguns dias, ou um hash por dia com `HINCRBY`. Se for preciso histórico, guarda-se o total do dia no PostgreSQL no fim do dia. |
