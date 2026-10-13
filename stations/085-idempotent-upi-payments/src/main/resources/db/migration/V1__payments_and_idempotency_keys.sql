-- The same business rules as PaymentRequest, enforced again by the database.
-- Java validation gives friendly messages; these constraints hold even when Java is bypassed
-- (a script, another service, a bug). They are partners, not alternatives.
CREATE TABLE payments (
    id           UUID         PRIMARY KEY,
    payer_vpa    VARCHAR(255) NOT NULL,
    payee_vpa    VARCHAR(255) NOT NULL,
    amount_paise BIGINT       NOT NULL,
    note         VARCHAR(80),
    status       VARCHAR(16)  NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL,
    CONSTRAINT payments_amount_range      CHECK (amount_paise BETWEEN 1 AND 10000000), -- Rs 0.01 to Rs 1,00,000 (demo rule)
    CONSTRAINT payments_different_parties CHECK (lower(payer_vpa) <> lower(payee_vpa))
);

-- One row per (payer, key). The primary key is the lock: a second insert of the
-- same pair waits for the first transaction, then sees its committed row.
CREATE TABLE idempotency_keys (
    payer_vpa       VARCHAR(255) NOT NULL,
    idem_key        VARCHAR(64)  NOT NULL,
    request_hash    CHAR(64)     NOT NULL,
    payment_id      UUID         REFERENCES payments (id),
    response_status SMALLINT,
    response_body   TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (payer_vpa, idem_key),
    -- The three result columns are empty while the claiming transaction runs, and all filled before it commits.
    -- Never half-filled: a replay must always find a complete stored response.
    CONSTRAINT idempotency_keys_result_complete CHECK (
        (payment_id IS NULL AND response_status IS NULL AND response_body IS NULL)
        OR (payment_id IS NOT NULL AND response_status IS NOT NULL AND response_body IS NOT NULL))
);

-- Lets a cleanup job delete keys older than the retention window without a full scan.
CREATE INDEX idx_idempotency_keys_created_at ON idempotency_keys (created_at);
