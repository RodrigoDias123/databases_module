// Challenge, tarefa 3: test_daily_revenue.js
// Corre com: mongosh "$MONGO_URL" --quiet --file test_daily_revenue.js
// (a partir da pasta challenge/, para o load() encontrar o daily_revenue.js)
//
// O QUE TENS DE FAZER
// Escreve um teste que corre o relatório três vezes e confirma que ele é incremental.
// Em cada passo, usa check() e deixa o script falhar se o resultado não for o esperado.
//
// Passos:
//   0. Começa do zero: apaga `daily_revenue` e `report_state`.
//   1. Corre o relatório sobre a coleção completa: load("daily_revenue.js").
//   2. Insere 5 alugueres novos em `rentals`, com `_id` acima do máximo atual:
//      3 em 2026-07-28 (um dia que já tem alugueres) e 2 em 2026-07-29 (um dia novo).
//      Usa a mesma forma dos outros alugueres, com `amount` em Decimal128.
//   3. Guarda uma cópia de `daily_revenue`, corre o relatório outra vez e confirma que só
//      esses 2 dias mudaram.
//   4. Compara `daily_revenue` com um recálculo completo, feito de raiz sobre `rentals`.
//      Têm de ser iguais.
//   5. Corre o relatório uma terceira vez e confirma que não mudou nada.
//   6. No fim, mesmo que o teste falhe (try/finally), apaga os 5 alugueres. Caso contrário,
//      os totais de `rentals` deixam de bater certo com o exercício.
//
// Copia o output do teste para o README.md.

db = db.getSiblingDB("pagila_docs");

function check(condition, message) {
    if (!condition) {
        throw new Error(`FALHOU: ${message}`);
    }
    print(`ok: ${message}`);
}

// Uma cópia de `daily_revenue` em { dia: documento em texto }. O revenue é Decimal128, e o
// === entre dois objetos dá sempre falso, por isso a comparação é feita sobre o texto EJSON.
function snapshot(docs) {
    const result = {};
    docs.forEach((doc) => {
        result[doc._id] = EJSON.stringify(doc);
    });
    return result;
}

// Os dias que foram criados, apagados ou alterados entre duas cópias.
function changed_days(before, after) {
    const all_days = new Set([...Object.keys(before), ...Object.keys(after)]);
    return [...all_days].filter((day) => before[day] !== after[day]).sort();
}

function read_report() {
    return snapshot(db.daily_revenue.find().toArray());
}

// Escrito de propósito sem nada do daily_revenue.js: é um recálculo de raiz, sem marca de água.
function full_recomputation() {
    return snapshot(db.rentals.aggregate([
        { $group: {
            _id: { $dateToString: { date: "$rental_date", format: "%Y-%m-%d", timezone: "UTC" } },
            rentals: { $sum: 1 },
            revenue: { $sum: "$amount" }
        } }
    ]).toArray());
}

function same_days(actual, expected) {
    return JSON.stringify(actual) === JSON.stringify(expected);
}

function revenue_of(doc) {
    return parseFloat(doc.revenue.toString());
}

function new_rental(id, rental_date, amount) {
    return {
        _id: id,
        customer_id: 3,
        film_id: 670,
        title: "PELICAN COMFORTS",
        categories: ["Family", "Sci-Fi"],
        store_id: 2,
        rental_date: ISODate(rental_date),
        return_date: null,
        amount: Decimal128.fromString(amount)
    };
}

const EXISTING_DAY = "2026-07-28";
const NEW_DAY = "2026-07-29";
let new_ids = [];

try {
    // Passo 0
    db.daily_revenue.drop();
    db.report_state.drop();

    // Passo 1
    print("\n1. Primeira execução, sobre a coleção completa");
    load("daily_revenue.js");
    const first = read_report();
    const total_rentals = db.rentals.countDocuments();
    const max_id = db.rentals.find().sort({ _id: -1 }).limit(1).toArray()[0]._id;
    const counted = db.daily_revenue.aggregate([{ $group: { _id: null, n: { $sum: "$rentals" } } }]).toArray()[0].n;
    check(counted === total_rentals, `daily_revenue conta os ${total_rentals} alugueres`);
    check(first[EXISTING_DAY] !== undefined, `${EXISTING_DAY} já tem alugueres`);
    check(first[NEW_DAY] === undefined, `${NEW_DAY} ainda não existe`);
    check(db.report_state.findOne({ _id: "daily_revenue" }).last_rental_id === max_id, `marca de água em ${max_id}`);

    // Passo 2
    print("\n2. Inserir 5 alugueres novos");
    new_ids = [1, 2, 3, 4, 5].map((n) => max_id + n);
    const existing_before = db.daily_revenue.findOne({ _id: EXISTING_DAY });
    db.rentals.insertMany([
        new_rental(new_ids[0], "2026-07-28T23:00:00Z", "2.99"),
        new_rental(new_ids[1], "2026-07-28T23:10:00Z", "4.99"),
        new_rental(new_ids[2], "2026-07-28T23:20:00Z", "0.99"),
        new_rental(new_ids[3], "2026-07-29T10:00:00Z", "2.99"),
        new_rental(new_ids[4], "2026-07-29T11:00:00Z", "3.99")
    ]);
    check(db.rentals.countDocuments() === total_rentals + 5, "rentals tem mais 5 documentos");

    // Passo 3
    print("\n3. Segunda execução");
    load("daily_revenue.js");
    const second = read_report();
    const expected_days = [EXISTING_DAY, NEW_DAY];
    check(same_days(last_report_days, expected_days), `só recalculou ${expected_days.join(" e ")}`);
    check(same_days(changed_days(first, second), expected_days), "só esses 2 dias mudaram");
    const existing_after = db.daily_revenue.findOne({ _id: EXISTING_DAY });
    const new_day = db.daily_revenue.findOne({ _id: NEW_DAY });
    check(existing_after.rentals === existing_before.rentals + 3, `${EXISTING_DAY} tem mais 3 alugueres`);
    check(Math.abs(revenue_of(existing_after) - revenue_of(existing_before) - 8.97) < 0.001, `${EXISTING_DAY} tem mais 8.97 de receita`);
    check(new_day.rentals === 2 && revenue_of(new_day) === 6.98, `${NEW_DAY} tem 2 alugueres e 6.98 de receita`);
    check(db.report_state.findOne({ _id: "daily_revenue" }).last_rental_id === new_ids[4], `marca de água em ${new_ids[4]}`);

    // Passo 4
    print("\n4. Comparar com um recálculo completo");
    const differences = changed_days(second, full_recomputation());
    check(differences.length === 0, `daily_revenue é igual ao recálculo completo (${Object.keys(second).length} dias)`);

    // Passo 5
    print("\n5. Terceira execução");
    load("daily_revenue.js");
    check(last_report_days.length === 0, "não recalculou nenhum dia");
    check(changed_days(second, read_report()).length === 0, "daily_revenue não mudou");
    check(db.report_state.findOne({ _id: "daily_revenue" }).last_rental_id === new_ids[4], "marca de água não mudou");

    print("\nTESTE PASSOU");
} finally {
    // Passo 6. O relatório também tem de sair: depois de apagar os 5 alugueres, ficava com
    // dados que já não existem e com a marca de água acima do maior _id de `rentals`.
    db.rentals.deleteMany({ _id: { $in: new_ids } });
    db.daily_revenue.drop();
    db.report_state.drop();
    print(`limpeza: ${new_ids.length} alugueres de teste apagados, rentals tem ${db.rentals.countDocuments()} documentos`);
}
