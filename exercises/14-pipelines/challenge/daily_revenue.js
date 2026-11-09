// Challenge, tarefas 1 e 2: daily_revenue.js
// Corre com: mongosh "$MONGO_URL" --quiet --file daily_revenue.js
//
// O QUE TENS DE FAZER
// Mantém a coleção `daily_revenue` atualizada de forma incremental: cada execução só
// recalcula os dias que têm alugueres novos, e correr de novo sem dados novos não muda nada.
//
// Forma de cada documento de `daily_revenue` (um por dia):
//   { _id: <o dia>, rentals: <número de alugueres>, revenue: <soma de amount> }
//
// Passos de cada execução:
//   1. Lê a marca de água (watermark) de `report_state`: o maior `rentals._id` já processado.
//      Na primeira execução ainda não existe, por isso são processados todos os alugueres.
//   2. Encontra os dias distintos dos alugueres com `_id` acima da marca de água.
//      Se não houver nenhum, termina sem escrever nada.
//   3. Recalcula esses dias a partir de TODOS os alugueres desses dias, e não só dos novos.
//   4. Escreve o resultado em `daily_revenue` com `$merge` e `whenMatched: "replace"`.
//   5. Só no fim, move a marca de água. Se a execução falhar a meio, a seguinte volta a
//      processar os mesmos dias.
//
// Este ficheiro é carregado pelo test_daily_revenue.js com load(), e cada load() é uma
// execução do relatório. Por isso usa só `function` e evita `const` no topo do ficheiro.

db = db.getSiblingDB("pagila_docs");

// O dia de um aluguer, sempre em UTC, para os limites dos dias serem iguais em todos os passos.
function day_of_rental() {
    return { $dateToString: { date: "$rental_date", format: "%Y-%m-%d", timezone: "UTC" } };
}

function read_watermark() {
    const state = db.report_state.findOne({ _id: "daily_revenue" });
    return state ? state.last_rental_id : null;
}

// O maior _id é lido no início da execução. Assim, um aluguer inserido enquanto o relatório
// corre fica acima da marca de água e é processado na execução seguinte.
function read_max_rental_id() {
    const newest = db.rentals.find({}, { _id: 1 }).sort({ _id: -1 }).limit(1).toArray();
    return newest.length > 0 ? newest[0]._id : null;
}

function find_changed_days(watermark, max_rental_id) {
    const id_range = { $lte: max_rental_id };
    if (watermark !== null) {
        id_range.$gt = watermark;
    }
    return db.rentals.aggregate([
        { $match: { _id: id_range } },
        { $group: { _id: day_of_rental() } },
        { $sort: { _id: 1 } }
    ]).toArray().map((doc) => doc._id);
}

// Filtra por intervalos de `rental_date` (um por dia, em UTC) em vez de calcular o dia de
// cada aluguer com $expr. Assim o $match usa o índice em `rental_date` e só lê os alugueres
// desses dias, em vez de percorrer a coleção toda.
function day_ranges(days) {
    return days.map((day) => {
        const start = new Date(`${day}T00:00:00Z`);
        const end = new Date(start.getTime() + 24 * 60 * 60 * 1000);
        return { rental_date: { $gte: start, $lt: end } };
    });
}

function merge_days(days, full_run) {
    // Na primeira execução são todos os dias, por isso não vale a pena filtrar.
    const filter = full_run ? {} : { $or: day_ranges(days) };
    db.rentals.aggregate([
        { $match: filter },
        { $group: { _id: day_of_rental(), rentals: { $sum: 1 }, revenue: { $sum: "$amount" } } },
        { $merge: { into: "daily_revenue", on: "_id", whenMatched: "replace", whenNotMatched: "insert" } }
    ]).toArray();
}

function save_watermark(max_rental_id) {
    db.report_state.updateOne(
        { _id: "daily_revenue" },
        { $set: { last_rental_id: max_rental_id } },
        { upsert: true }
    );
}

function run_report() {
    // O teste usa esta variável para confirmar que dias cada execução recalculou.
    globalThis.last_report_days = [];
    db.rentals.createIndex({ rental_date: 1 });

    const watermark = read_watermark();
    const max_rental_id = read_max_rental_id();
    if (max_rental_id === null || (watermark !== null && max_rental_id <= watermark)) {
        print("daily_revenue: sem alugueres novos, nada a fazer");
        return;
    }

    const days = find_changed_days(watermark, max_rental_id);
    merge_days(days, watermark === null);
    save_watermark(max_rental_id);

    globalThis.last_report_days = days;
    print(`daily_revenue: ${days.length} dia(s) recalculado(s), marca de água em ${max_rental_id}`);
}

run_report();
