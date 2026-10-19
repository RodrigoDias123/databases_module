# Challenge 01: Database engines and diagnosis

Opcional.

## Enunciado

Write a Python script that starts 10 processes, each appending 1,000 records to the same JSON file (read, append, write back). Count how many records end up in the file. Then do the same against a PostgreSQL table with 10 concurrent connections and compare. Explain in a few sentences why the numbers differ.

## Resposta

Script: [race.py](race.py). Cria a base de dados com `./scripts/create-db.sh ex01_challenge` (a partir da raiz do repositório) e depois corre:

```bash
cd exercises/01-diagnosis/challenge
uv run race.py
```

10 processos escrevem 1 000 registos cada um, o que dá 10 000 no total. Resultado de três execuções:

| Execução | JSON (read, append, write) | Ficheiro corrompido e reiniciado | PostgreSQL (10 ligações) |
|----------|---------------------------:|---------------------------------:|-------------------------:|
| 1 | 285 / 10 000 | 190 vezes | 10 000 / 10 000 |
| 2 | 174 / 10 000 | 202 vezes | 10 000 / 10 000 |
| 3 | 189 / 10 000 | 213 vezes | 10 000 / 10 000 |

O ficheiro JSON perde mais de 97 % dos registos, e o PostgreSQL não perde nenhum.

### Porque é que os números são diferentes

O ficheiro JSON não tem controlo de concorrência. Cada processo lê o ficheiro inteiro, acrescenta um registo e volta a escrevê-lo inteiro. Se dois processos lerem a mesma versão, o último a escrever apaga o registo do outro (*lost update*). Pior ainda, `write_text` primeiro trunca o ficheiro e só depois escreve. Um leitor pode apanhar o ficheiro vazio ou a meio, e duas escritas sobrepostas deixam lixo no fim (`Extra data`). O ficheiro fica corrompido de vez e os dados que tinha perdem-se. Numa primeira versão do script, os workers ficavam para sempre a tentar ler esse ficheiro corrompido.

O PostgreSQL trata cada `INSERT` como uma transação atómica. Os processos não reescrevem a tabela: cada um acrescenta só a sua linha. Os locks e o WAL do motor garantem que escritas concorrentes não se apagam umas às outras e que um commit sobrevive a um crash. Por isso as 10 000 linhas ficam todas gravadas, e ainda por cima o processo é 10 vezes mais rápido (0,5 s contra ~5 s), porque não reescreve o ficheiro inteiro a cada registo.

### Nota sobre o método de medição

Quando um processo lê o ficheiro a meio de outra escrita, tenta outra vez até 50 vezes ([race.py:30-37](race.py#L30-L37)). Se o ficheiro continuar ilegível, está corrompido para sempre. Nesse caso o processo recomeça de `[]`, e tudo o que o ficheiro tinha perde-se ([race.py:43-48](race.py#L43-L48)). Sem esta regra, os workers ficavam bloqueados indefinidamente a tentar ler um ficheiro corrompido. Foi isso que aconteceu na primeira versão do script.

Por isso, o número de registos perdidos no JSON junta duas causas:

1. **Lost updates**: dois processos leem a mesma versão do ficheiro, e o último a escrever apaga o registo do outro.
2. **Corrupção**: escritas sobrepostas deixam o ficheiro com JSON inválido, e o conteúdo inteiro perde-se.

O script mostra quantas vezes o ficheiro foi reiniciado ("file corrupt and reset N times"), para se ver o peso da segunda causa.

Os números mudam de execução para execução, porque dependem de como o sistema operativo distribui o tempo pelos processos. O padrão repete-se sempre: o JSON perde mais de 97 % dos registos, e o PostgreSQL grava os 10 000.
