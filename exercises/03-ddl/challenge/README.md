# Challenge 03: SQL DDL, data types and constraints

Obrigatório.

## Enunciado

Make the database reject invalid ISBNs. Create a `DOMAIN isbn13` over `text` whose `CHECK` validates both the format (13 digits, optional hyphens) and the check digit, using an `IMMUTABLE` SQL function. Use the domain in your `book` table. Prove that a valid ISBN is accepted, and that one with a wrong check digit is rejected. Explain why the function should be `IMMUTABLE`.

## Resposta

Ficheiro: [isbn13.sql](isbn13.sql). Corre depois do [schema.sql](../schema.sql):

```bash
psql -v ON_ERROR_STOP=1 -f ../schema.sql
psql -f isbn13.sql
```

### O que o script faz

1. **`isbn13_is_valid(text)`**: uma função SQL `IMMUTABLE` que devolve `true` só quando:
   - o formato está certo: só dígitos, com hífenes opcionais entre eles (nunca no início, no fim, nem dois seguidos);
   - há exatamente 13 dígitos;
   - o dígito de controlo está certo: os 13 dígitos, multiplicados alternadamente por 1 e 3, somam um múltiplo de 10.

   O `CASE` só faz a soma quando o formato já está validado. Com `AND`, o PostgreSQL não garante a ordem de avaliação, e converter uma letra para `int` dava um erro em vez de `false`.
2. **`DOMAIN isbn13`**: é um `text` com `CHECK (isbn13_is_valid(VALUE))`.
3. **`ALTER TABLE book ALTER COLUMN isbn TYPE isbn13`**: a coluna `isbn` do `book` passa a usar o domínio.

### Prova

| ISBN | Resultado |
|------|-----------|
| `978-0-306-40615-7` | aceite |
| `9781861972712` | aceite |
| `978-0-306-40615-8` (dígito de controlo errado) | `ERROR: value for domain isbn13 violates check constraint "isbn13_valid"` |
| `978030640615` (12 dígitos) | `ERROR: ... "isbn13_valid"` |
| `978-0-306-4061X-7` (letra) | `ERROR: ... "isbn13_valid"` |

No fim, o `SELECT` mostra só os dois livros válidos.

Com o domínio, o ISBN `1234567890123` usado no [invalid.sql](../invalid.sql) seria rejeitado, porque o dígito de controlo certo é 8. Por isso o domínio fica neste script e não no `schema.sql`.

### Porque é que a função deve ser `IMMUTABLE`

`IMMUTABLE` é uma promessa ao PostgreSQL: com os mesmos argumentos, a função devolve sempre o mesmo resultado. Não lê tabelas, não depende da data, da hora, do fuso horário nem de outras configurações.

Para um `CHECK`, isto é importante, porque o PostgreSQL só verifica a constraint quando uma linha é inserida ou alterada. Nunca volta a verificar as linhas que já estão guardadas. Se o resultado da função pudesse mudar com o tempo:

- Linhas que foram aceites podiam passar a ser inválidas sem ninguém dar por isso, e a constraint deixava de garantir o que diz.
- Um `pg_dump` seguido de restore podia falhar, porque o restore volta a verificar todas as linhas com o resultado de hoje.

A validação de um ISBN só depende do próprio texto, por isso a função é mesmo `IMMUTABLE`. Isto traz duas vantagens:
- Pode ser usada num índice, por exemplo `CREATE INDEX ... ON book (isbn13_is_valid(isbn))`. Os índices só aceitam funções `IMMUTABLE`.
- O planner pode calcular o resultado de antemão quando o argumento é uma constante.

O PostgreSQL não verifica se a promessa é verdadeira. Se uma função que consulta uma tabela for marcada como `IMMUTABLE`, cria precisamente os problemas acima.
