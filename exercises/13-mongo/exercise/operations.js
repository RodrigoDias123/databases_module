// Tarefa 2: operations.js
// Corre com: mongosh "$MONGO_URL" --quiet --file operations.js
// Usa a base `pagila_docs` e regista no README o resultado de cada operação.
// As operações devem dar o resultado esperado sobre coleções acabadas de carregar (load.py).

db = db.getSiblingDB("pagila_docs");

// 1. Filmes com rating "PG-13" e length maior que 120 minutos.
//    Esperado: 118 documentos.

function find_pg13_long_movies() {
    return db.films.find({
        "rating": "PG-13",
        "length": { $gt: 120 }
    });
}

// 2. Filmes em que aparece o ator 1.
//    Esperado: 19 documentos.

function find_movies_with_actor_1() {
    return db.films.find({
        "actors.actor_id": 1
    });
}

// 3. Filmes da categoria "Horror" com rental_rate 0.99.
//    Esperado: 43 documentos.
//    rental_rate é Decimal128, por isso o valor tem de ser NumberDecimal (0.99 em double não é igual).

function find_horror_movies_with_rental_rate_099() {
    return db.films.find({
        "categories": "Horror",
        "rental_rate": NumberDecimal("0.99")
    });
}

// 4. Clientes com pelo menos um aluguer por devolver em recent_rentals (usa $elemMatch).
//    Esperado: 56 documentos.

function find_customers_with_unreturned_rentals() {
    return db.customers.find({
        "recent_rentals": {
            $elemMatch: { "return_date": null }
        }
    });
}

// 5. Cliente 1 só com first_name, last_name e os títulos de recent_rentals (projeção).
//    Esperado: 1 documento com 10 títulos.

function find_customer_1_with_recent_rentals() {
    return db.customers.find({
        "_id": 1
    }, {
        "_id": 0,
        "first_name": 1,
        "last_name": 1,
        "recent_rentals.title": 1
    });
}

// 6. Aumentar em 0.50 o rental_rate dos filmes NC-17 com menos de 60 minutos
//    (updateMany com $inc).
//    Esperado: 21 documentos modificados.

function increase_rental_rate_nc17_short_movies() {
    return db.films.updateMany({
        "rating": "NC-17",
        "length": { $lt: 60 }
    }, {
        $inc: { "rental_rate": NumberDecimal("0.50") }
    });
}

// 7. Adicionar um aluguer à frente de recent_rentals do cliente 1 e manter só 10
//    ($push com $each, $position e $slice).
//    Esperado: recent_rentals continua com 10 itens e o primeiro é o novo aluguer.

function add_rental_to_customer_1() {
    const newRental = {
        "rental_id": 99999,
        "film_id": 1,
        "title": "ACADEMY DINOSAUR",
        "rental_date": new Date(),
        "return_date": null
    };

    return db.customers.updateOne({
        "_id": 1
    }, {
        $push: {
            "recent_rentals": {
                $each: [newRental],
                $position: 0,
                $slice: 10
            }
        }
    });
}

// 8. updateOne com upsert: true e $setOnInsert que cria o filme
//    {_id: 1001, title: "TEST FILM"}. Corre-o duas vezes.
//    Esperado: a primeira faz upsert de 1 documento; a segunda faz match de 1 e modifica 0.

function upsert_test_film() {
    return db.films.updateOne({
        "_id": 1001
    }, {
        $setOnInsert: { "title": "TEST FILM" }
    }, {
        upsert: true
    });
}

print("1. PG-13 e mais de 120 minutos:", find_pg13_long_movies().count());
print("2. filmes do ator 1:", find_movies_with_actor_1().count());
print("3. Horror com rental_rate 0.99:", find_horror_movies_with_rental_rate_099().count());
print("4. clientes com aluguer por devolver:", find_customers_with_unreturned_rentals().count());

const customer1 = find_customer_1_with_recent_rentals().toArray();
print("5. projeção do cliente 1:", customer1.length, "documento,", customer1[0].recent_rentals.length, "títulos");
printjson(customer1[0]);

const inc = increase_rental_rate_nc17_short_movies();
print("6. $inc 0.50 em NC-17 < 60 min: matched", inc.matchedCount, "modified", inc.modifiedCount);

add_rental_to_customer_1();
const recent = db.customers.findOne({ "_id": 1 }).recent_rentals;
print("7. $push: recent_rentals tem", recent.length, "itens; o primeiro é o rental_id", recent[0].rental_id);

const first = upsert_test_film();
print("8. primeira execução: matched", first.matchedCount, "modified", first.modifiedCount, "upserted", first.upsertedCount);
const second = upsert_test_film();
print("8. segunda execução: matched", second.matchedCount, "modified", second.modifiedCount, "upserted", second.upsertedCount);
