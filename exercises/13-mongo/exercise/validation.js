// Tarefa 3: validation.js
// Corre com: mongosh "$MONGO_URL" --quiet --file validation.js
// Usa a base `pagila_docs`.

db = db.getSiblingDB("pagila_docs");

// 1. Adicionar validação $jsonSchema à coleção `films`, com
//    validationLevel: "strict" e validationAction: "error":
//    - title: string
//    - rating: um de "G", "PG", "PG-13", "R", "NC-17"
//    - length: inteiro entre 1 e 999
//    - rental_rate: decimal
//    - categories: array de strings
//    - actors: array de objetos com actor_id inteiro e name string
//    A coleção já existe, por isso usa-se collMod (createCollection falharia).

function add_validation_to_films() {
    return db.runCommand({
        collMod: "films",
        validator: {
            $jsonSchema: {
                bsonType: "object",
                required: ["title", "rating", "length", "rental_rate", "categories", "actors"],
                properties: {
                    title: { bsonType: "string" },
                    rating: { enum: ["G", "PG", "PG-13", "R", "NC-17"] },
                    length: { bsonType: "int", minimum: 1, maximum: 999 },
                    rental_rate: { bsonType: "decimal" },
                    categories: { bsonType: "array", items: { bsonType: "string" } },
                    actors: {
                        bsonType: "array",
                        items: {
                            bsonType: "object",
                            required: ["actor_id", "name"],
                            properties: {
                                actor_id: { bsonType: "int" },
                                name: { bsonType: "string" }
                            }
                        }
                    }
                }
            }
        },
        validationLevel: "strict",
        validationAction: "error"
    });
}

// 2. Mostrar que o load.py continua a correr com a validação ativa.
//    O load.py é Python, por isso corre-se na shell depois deste ficheiro:
//    uv run --env-file ../../../.env python load.py

// 3. Tentar inserir um documento com rating: "XXX" e mostrar que é rejeitado.

function test_insert_invalid_rating() {
    try {
        db.films.insertOne({
            title: "Invalid Movie",
            rating: "XXX",
            length: 100,
            rental_rate: NumberDecimal("2.99"),
            categories: ["Action"],
            actors: [{ actor_id: 1, name: "Actor One" }]
        });
    } catch (e) {
        return e;
    }
}

// 4. Tentar inserir um documento com length: "long" e mostrar que é rejeitado.

function test_insert_invalid_length() {
    try {
        db.films.insertOne({
            title: "Invalid Length Movie",
            rating: "PG",
            length: "long",
            rental_rate: NumberDecimal("2.99"),
            categories: ["Comedy"],
            actors: [{ actor_id: 2, name: "Actor Two" }]
        });
    } catch (e) {
        return e;
    }
}

printjson(add_validation_to_films());

for (const [label, test] of [["rating XXX", test_insert_invalid_rating], ["length long", test_insert_invalid_length]]) {
    const error = test();
    print(`\n${label}: rejeitado, ${error.name} ${error.code}: ${error.message}`);
    printjson(error.errInfo.details.schemaRulesNotSatisfied);
}
