// Tarefa 4: index.js
// Corre com: mongosh "$MONGO_URL" --quiet --file index.js
// Usa a base `pagila_docs`.

db = db.getSiblingDB("pagila_docs");

const query = { "actors.actor_id": 1 };

function summary(explain) {
    const stats = explain.executionStats;
    let stage = stats.executionStages;
    while (stage.inputStage) {
        stage = stage.inputStage;
    }
    return { stage: stage.stage, totalDocsExamined: stats.totalDocsExamined, nReturned: stats.nReturned };
}

// 1. Correr find({"actors.actor_id": 1}).explain("executionStats") sem índice
//    e anotar stage, totalDocsExamined e nReturned.
//    O índice é apagado primeiro para o "antes" ser sempre sem índice.

if (db.films.getIndexes().some(index => index.name === "actors.actor_id_1")) {
    db.films.dropIndex("actors.actor_id_1");
}

const explain_without_index = db.films.find(query).explain("executionStats");
print("antes:");
printjson(summary(explain_without_index));

// 2. Criar um índice em actors.actor_id.

db.films.createIndex({ "actors.actor_id": 1 });

// 3. Correr o mesmo explain outra vez e anotar stage, totalDocsExamined e nReturned.

const explain_with_index = db.films.find(query).explain("executionStats");
print("depois:");
printjson(summary(explain_with_index));

// Esperado: o plano passa de COLLSCAN para IXSCAN, com 19 documentos examinados.
// No README: compara os dois resumos do explain.
