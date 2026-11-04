// Tarefas 1 a 4: pipelines.js
// Corre com: mongosh "$MONGO_URL" --quiet --file pipelines.js
//
// O QUE TENS DE FAZER
// Preenche o array de cada função abaixo com os estágios da pipeline. Não precisas de
// mexer no código do fim do ficheiro: ele corre as 4 pipelines e mostra, para cada uma,
// o número de documentos e os primeiros 3. Copia esse output para o README.md.
//
// Antes de começar: as coleções têm de estar como o load.py as deixa. A operação 6 do
// exercício 13 alterou preços em `films` e a operação 8 criou o filme 1001, por isso
// apaga e carrega de novo (os comandos estão no README.md).
//
// Lembra-te: `rental_rate` e `amount` são Decimal128 e as datas são datas BSON.
// `categories` é um array, e `actors` é um array de objetos.

db = db.getSiblingDB("pagila_docs");

// 1. Receita por categoria e por mês em 2025, a partir de `rentals`, usando `rental_date`.
//    Output: `category`, `month`, `revenue`, ordenado por categoria e por mês.
//    Esperado: 192 documentos; `Action` em janeiro de 2025 tem 333.87.
//    O que precisas de resolver:
//      - filtrar só os alugueres de 2025 (compara com datas, por exemplo com ISODate);
//      - cada aluguer pode ter várias categorias, por isso cada uma tem de contar;
//      - agrupar por categoria e mês, somar `amount`, e dar a forma final ao output.
//    Também tens de explicar no README porque é que 333.87 difere de 314.94, o valor da
//    pergunta 2 do exercício 05. Compara com ../../05-queries/exercise/queries.sql.


function revenue_per_category_per_month() {
    return [
        { $match: { rental_date: { $gte: ISODate("2025-01-01"), $lt: ISODate("2026-01-01") } } },
        { $unwind: "$categories" },
        { $group: { _id: { category: "$categories", month: { $month: "$rental_date" } }, revenue: { $sum: "$amount" } } },
        { $project: { _id: 0, category: "$_id.category", month: "$_id.month", revenue: 1 } },
        { $sort: { category: 1, month: 1 } }
    ];

}

// 2. O ator com mais filmes em cada categoria, a partir de `films`, incluindo empates.
//    Output: um documento por categoria com `category`, `films` (o número de filmes)
//    e um array `actors`.
//    Esperado: 16 documentos com 30 atores no total.
//    O que precisas de resolver:
//      - contar os filmes de cada par (categoria, ator);
//      - manter, em cada categoria, todos os atores com a contagem máxima, e não só um.
//        Um `$sort` seguido de `$first` perdia os empates e nunca chegava aos 30 atores.

function top_actors_per_category() {
    return [
        { $unwind: "$categories" },
        { $unwind: "$actors" },
        { $group: { _id: { category: "$categories", actor_id: "$actors.actor_id", name: "$actors.name" }, films: { $sum: 1 } } },
        { $sort: { "_id.name": 1 } },
        { $group: { _id: "$_id.category", maxFilms: { $max: "$films" }, actors: { $push: { name: "$_id.name", films: "$films" } } } },
        { $project: {
            _id: 0,
            category: "$_id",
            films: "$maxFilms",
            actors: {
                $map: {
                    input: { $filter: { input: "$actors", as: "a", cond: { $eq: ["$$a.films", "$maxFilms"] } } },
                    as: "a",
                    in: "$$a.name"
                }
            }
        } },
        { $sort: { category: 1 } }
    ];
}

// 3. Distribuição da duração dos filmes com `$bucket`, em `films`,
//    com os limites [0, 60, 90, 120, 150, 186].
//    Esperado: contagens 96, 224, 214, 216 e 250.

function film_length_distribution() {
    return [
        { $bucket: { groupBy: "$length", boundaries: [0, 60, 90, 120, 150, 186], output: { count: { $sum: 1 } } } }
    ];
}

// 4. Um único `$facet` sobre `films` com três resumos:
//      - o número total de filmes e o rental_rate médio;
//      - o número de filmes por rating;
//      - os 5 filmes mais longos (`title`, `length`), com empates desempatados por título.
//    Esperado:
//      - 1000 filmes com rental_rate médio de 2.98;
//      - G 178, PG 194, PG-13 223, R 195, NC-17 210;
//      - CHICAGO NORTH, CONTROL ANTHEM, DARN FORRESTER, GANGS PRIDE e HOME PITY,
//        todos com 185 minutos.
//    Devolve 1 só documento, com um campo (array) por cada resumo.

function films_summary_facet() {
    return [
        { $facet: {
                total_and_avg: [
                    { $group: { _id: null, total_films: { $sum: 1 }, avg_rental_rate: { $avg: "$rental_rate" } } },
                    { $project: { _id: 0, total_films: 1, avg_rental_rate: 1 } }
                ],
                count_by_rating: [
                    { $group: { _id: "$rating", count: { $sum: 1 } } },
                    { $project: { _id: 0, rating: "$_id", count: 1 } },
                    { $sort: { rating: 1 } }
                ],
                top_5_longest_films: [
                    { $sort: { length: -1, title: 1 } },
                    { $limit: 5 },
                    { $project: { _id: 0, title: 1, length: 1 } }
                ]
            } }
    ];
}

// Corre as pipelines e mostra o resultado. Não precisas de alterar nada daqui para baixo.
function report(label, collection, pipeline) {
    const docs = db[collection].aggregate(pipeline).toArray();
    print(`\n${label}: ${docs.length} documentos`);
    docs.slice(0, 3).forEach((doc) => printjson(doc));
}

report("1. Receita por categoria e mês", "rentals", revenue_per_category_per_month());
report("2. Ator com mais filmes por categoria", "films", top_actors_per_category());
report("3. Distribuição das durações", "films", film_length_distribution());
report("4. Resumo com $facet", "films", films_summary_facet());
