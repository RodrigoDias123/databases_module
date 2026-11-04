#!/usr/bin/env bash
# Tarefa 5: restore_mongo.sh
# Corre com: ./restore_mongo.sh (depois de correr o backup_mongo.sh)
#
# O QUE TENS DE FAZER
# Restaura o arquivo mais recente de backups/ para uma base chamada `pagila_docs_restored`
# e mostra a contagem de documentos de cada coleção nas duas bases. A base original
# `pagila_docs` não pode ser alterada.
#
# Passos:
#   1. Encontra o arquivo mais recente (ls -t ... | head -n 1). Se não houver nenhum,
#      termina com uma mensagem de erro.
#   2. Corre o mongorestore dentro do contentor, com o arquivo a entrar pelo stdin:
#        docker compose --project-directory "$repo_root" exec -T mongo mongorestore ... < "$file"
#      Opções a usar: --uri, --archive, --gzip, --drop e
#        --nsFrom 'pagila_docs.*' --nsTo 'pagila_docs_restored.*'
#      O --drop substitui as coleções restauradas, para o script poder correr várias vezes.
#   3. Com o mongosh, percorre as coleções de `pagila_docs` e mostra countDocuments() de
#      cada uma nas duas bases. Usa getSiblingDB() e getCollectionNames().
#      Podes correr o mongosh dentro do contentor com $container_url e --eval.
#
# O exercício só está feito quando as contagens são iguais em todas as coleções.
# Copia o output deste script para o README.md.
#
# Referência: sessions/14-mongodb-pipelines/fastapi/scripts/restore_mongo.sh
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
set -a; source "$repo_root/.env"; set +a

source_db="pagila_docs"
target_db="pagila_docs_restored"
backup_dir="$script_dir/backups"
container_url="mongodb://${MONGO_ROOT_USER}:${MONGO_ROOT_PASSWORD}@localhost:27017/?authSource=admin"

restore_backup() {
    latest_file=$(ls -t "$backup_dir"/mongo_"$source_db"_*.archive.gz 2>/dev/null | head -n 1 || true)
    if [[ -z "$latest_file" ]]; then
        echo "Erro: nenhum arquivo de backup encontrado em $backup_dir" >&2
        exit 1
    fi
    echo "A restaurar $(basename "$latest_file") para $target_db"

    docker compose --project-directory "$repo_root" exec -T mongo mongorestore \
        --uri="$container_url" \
        --archive \
        --gzip \
        --drop \
        --nsFrom "${source_db}.*" \
        --nsTo "${target_db}.*" < "$latest_file"
}

show_counts() {
    docker compose --project-directory "$repo_root" exec -T mongo mongosh "$container_url" --quiet --eval "
        const source = db.getSiblingDB('$source_db');
        const target = db.getSiblingDB('$target_db');
        print('coleção: ' + source.getName() + ' / ' + target.getName());
        source.getCollectionNames().sort().forEach((name) => {
            print(name + ': ' + source.getCollection(name).countDocuments({}) + ' / ' + target.getCollection(name).countDocuments({}));
        });
    "
}

restore_backup
show_counts

