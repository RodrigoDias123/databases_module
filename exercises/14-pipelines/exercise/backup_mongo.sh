#!/usr/bin/env bash
# Tarefa 5: backup_mongo.sh
# Corre com: ./backup_mongo.sh
#
# O QUE TENS DE FAZER
# Faz o dump da base `pagila_docs` para a pasta backups/ como um arquivo comprimido, com
# a data no nome, como no tutorial. Por exemplo:
#   backups/mongo_pagila_docs_2026-11-03_101500.archive.gz
#
# Passos:
#   1. Cria a pasta backups/ se ainda não existir (mkdir -p).
#   2. Monta o nome do ficheiro com a data: $(date +%F_%H%M%S).
#   3. Corre o mongodump dentro do contentor e redireciona o stdout para o ficheiro:
#        docker compose --project-directory "$repo_root" exec -T mongo mongodump ...
#      Opções a usar: --uri, --db, --archive (sem nome escreve no stdout) e --gzip.
#      Dentro do contentor o servidor é localhost:27017, por isso usa $container_url
#      (definido abaixo) e não o MONGO_URL.
#   4. Escreve primeiro num nome temporário (.part) e só faz mv no fim, se correr bem.
#      Assim, um dump falhado não deixa um arquivo vazio que o restore escolheria como
#      o mais recente.
#   5. Mostra o caminho e o tamanho do arquivo criado.
#
# Referência: sessions/14-mongodb-pipelines/fastapi/scripts/backup_mongo.sh
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
set -a; source "$repo_root/.env"; set +a

db_name="pagila_docs"
backup_dir="$script_dir/backups"
container_url="mongodb://${MONGO_ROOT_USER}:${MONGO_ROOT_PASSWORD}@localhost:27017/?authSource=admin"

create_backup_dir() {
    mkdir -p "$backup_dir"
    date_str=$(date +%F_%H%M%S)
}

run_mongodump() {
    temp_file="$backup_dir/mongo_${db_name}_${date_str}.archive.gz.part"
    final_file="${temp_file%.part}"
    trap 'rm -f "$temp_file"' EXIT

    docker compose --project-directory "$repo_root" exec -T mongo mongodump \
        --uri="$container_url" \
        --db="$db_name" \
        --archive \
        --gzip > "$temp_file"

    mv "$temp_file" "$final_file"
}

show_result() {
    echo "Backup criado: $final_file ($(du -h "$final_file" | cut -f1))"
}

create_backup_dir
run_mongodump
show_result



