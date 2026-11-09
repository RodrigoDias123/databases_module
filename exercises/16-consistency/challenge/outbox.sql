CREATE TABLE outbox (
    outbox_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id  integer NOT NULL,
    film_id      integer NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    processed_at timestamptz
);

-- the worker looks only at unprocessed rows, in order
CREATE INDEX outbox_unprocessed ON outbox (outbox_id) WHERE processed_at IS NULL;
