-- Hospital: esquema criado a partir do Mermaid.md.
-- CASE é uma palavra reservada do SQL, por isso a tabela chama-se clinical_case.

DROP TABLE IF EXISTS report, insurance_finance, shift, finance, episode,
                     room, medical_unit, insurance, clinical_case,
                     unit, staff, patient;

-- 1º grupo: tabelas sem FKs

CREATE TABLE patient (
    patient_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       text NOT NULL,
    birth_date date NOT NULL,
    gender     text CHECK (gender IN ('M', 'F')),
    address    text,
    phone      text
);

CREATE TABLE staff (
    staff_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name     text NOT NULL,
    role     text NOT NULL,
    phone    text,
    email    text NOT NULL UNIQUE
);

CREATE TABLE unit (
    unit_id   integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name      text NOT NULL,
    unit_type text NOT NULL,
    address   text NOT NULL
);

-- 2º grupo: apontam para o 1º grupo

CREATE TABLE clinical_case (
    case_id    integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    patient_id integer NOT NULL REFERENCES patient(patient_id),
    case_type  text NOT NULL,
    opened_on  date NOT NULL,
    closed_on  date             -- vazio enquanto o caso está aberto
);

CREATE TABLE insurance (
    insurance_id  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    patient_id    integer NOT NULL REFERENCES patient(patient_id),
    name          text NOT NULL,
    policy_number text NOT NULL UNIQUE,
    valid_from    date NOT NULL,
    valid_to      date          -- vazio se a apólice não tiver fim
);

CREATE TABLE medical_unit (
    medical_unit_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unit_id         integer NOT NULL REFERENCES unit(unit_id),
    name            text NOT NULL,
    unit_type       text NOT NULL
);

CREATE TABLE room (
    room_id     integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unit_id     integer NOT NULL REFERENCES unit(unit_id),
    room_number text NOT NULL,
    room_type   text,
    UNIQUE (unit_id, room_number)   -- o mesmo número só se repete em unidades diferentes
);

-- 3º grupo: apontam para o 2º grupo

CREATE TABLE episode (
    episode_id      integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id         integer NOT NULL REFERENCES clinical_case(case_id),
    medical_unit_id integer NOT NULL REFERENCES medical_unit(medical_unit_id),
    started_on      date NOT NULL,
    ended_on        date        -- vazio enquanto o episódio decorre
);

CREATE TABLE finance (
    finance_id   integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id      integer NOT NULL UNIQUE REFERENCES clinical_case(case_id),   -- UNIQUE: 1:1 com o caso
    finance_type text NOT NULL,
    amount       numeric(10,2) NOT NULL,
    billed_on    date NOT NULL
);

CREATE TABLE shift (
    shift_id        integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    medical_unit_id integer NOT NULL REFERENCES medical_unit(medical_unit_id),
    staff_id        integer NOT NULL REFERENCES staff(staff_id),
    shift_date      date NOT NULL,
    shift_type      text NOT NULL
);

-- 4º grupo: apontam para finance

CREATE TABLE insurance_finance (
    insurance_finance_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    finance_id           integer NOT NULL REFERENCES finance(finance_id),
    insurance_id         integer NOT NULL REFERENCES insurance(insurance_id),
    covered_amount       numeric(10,2) NOT NULL,
    UNIQUE (finance_id, insurance_id)   -- o mesmo seguro não cobre duas vezes a mesma fatura
);

CREATE TABLE report (
    report_id    integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    finance_id   integer NOT NULL REFERENCES finance(finance_id),
    report_type  text NOT NULL,
    generated_on date NOT NULL
);
