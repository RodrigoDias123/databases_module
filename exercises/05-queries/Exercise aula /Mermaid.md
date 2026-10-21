```mermaid
erDiagram
    PATIENT ||--o{ CLINICAL_CASE : opens
    PATIENT ||--o{ INSURANCE : holds
    CLINICAL_CASE ||--o{ EPISODE : has
    CLINICAL_CASE ||--|| FINANCE : "is billed in"
    FINANCE ||--o{ INSURANCE_FINANCE : "is covered by"
    INSURANCE ||--o{ INSURANCE_FINANCE : covers
    FINANCE ||--o{ REPORT : produces
    MEDICAL_UNIT ||--o{ EPISODE : treats
    MEDICAL_UNIT ||--o{ SHIFT : "is staffed in"
    STAFF ||--o{ SHIFT : works
    UNIT ||--o{ MEDICAL_UNIT : contains
    UNIT ||--o{ ROOM : has

    PATIENT {
        int patient_id PK
        text name
        date birth_date
        text gender
        text address
        text phone
    }

    CLINICAL_CASE {
        int case_id PK
        int patient_id FK
        text case_type
        date opened_on
        date closed_on
    }

    EPISODE {
        int episode_id PK
        int case_id FK
        int medical_unit_id FK
        date started_on
        date ended_on
    }

    FINANCE {
        int finance_id PK
        int case_id FK, UK
        text finance_type
        numeric amount
        date billed_on
    }

    INSURANCE_FINANCE {
        int insurance_finance_id PK
        int finance_id FK
        int insurance_id FK
        numeric covered_amount
    }

    INSURANCE {
        int insurance_id PK
        int patient_id FK
        text name
        text policy_number UK
        date valid_from
        date valid_to
    }

    REPORT {
        int report_id PK
        int finance_id FK
        text report_type
        date generated_on
    }

    MEDICAL_UNIT {
        int medical_unit_id PK
        int unit_id FK
        text name
        text unit_type
    }

    SHIFT {
        int shift_id PK
        int medical_unit_id FK
        int staff_id FK
        date shift_date
        text shift_type
    }

    STAFF {
        int staff_id PK
        text name
        text role
        text phone
        text email UK
    }

    UNIT {
        int unit_id PK
        text name
        text unit_type
        text address
    }

    ROOM {
        int room_id PK
        int unit_id FK
        text room_number
        text room_type
    }

```

`CASE` é uma palavra reservada do SQL, por isso a entidade chama-se `CLINICAL_CASE`.

Regras que o diagrama não consegue mostrar (estão no [hospital.sql](hospital.sql)):

- `ROOM`: `UNIQUE (unit_id, room_number)`. O número da sala só se pode repetir em unidades diferentes.
- `INSURANCE_FINANCE`: `UNIQUE (finance_id, insurance_id)`. O mesmo seguro não cobre duas vezes a mesma fatura.
- `PATIENT`: `CHECK (gender IN ('M', 'F'))`.
