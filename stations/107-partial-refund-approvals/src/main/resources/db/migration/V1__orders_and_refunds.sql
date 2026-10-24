-- Orders and their refunds. All money in paise.
CREATE TABLE orders (
    id             BIGINT PRIMARY KEY,
    customer       TEXT   NOT NULL,
    total_paise    BIGINT NOT NULL CONSTRAINT orders_total_positive CHECK (total_paise > 0),
    -- Approved refunds plus those waiting for approval: what may no longer be refunded.
    reserved_paise BIGINT NOT NULL DEFAULT 0,
    -- The rule itself, for every writer: never more refunded (or promised) than was paid.
    CONSTRAINT orders_refunds_within_total CHECK (reserved_paise BETWEEN 0 AND total_paise)
);

CREATE TABLE refunds (
    id           BIGSERIAL PRIMARY KEY,
    order_id     BIGINT      NOT NULL REFERENCES orders (id),
    amount_paise BIGINT      NOT NULL CONSTRAINT refunds_amount_positive CHECK (amount_paise > 0),
    reason       VARCHAR(200) NOT NULL,
    status       TEXT        NOT NULL CONSTRAINT refunds_status CHECK (status IN ('PENDING_APPROVAL', 'APPROVED', 'REJECTED')),
    -- Above the limit, the amount at the time of the request: kept with the row so a later change of the limit
    -- does not change what this refund needed.
    needs_second_approval BOOLEAN NOT NULL,
    requested_by TEXT        NOT NULL,
    decided_by   TEXT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at   TIMESTAMPTZ,
    -- Four eyes: whoever decides a refund that needs approval is not the person who asked for it.
    CONSTRAINT refunds_second_person CHECK (NOT needs_second_approval OR decided_by IS NULL OR decided_by <> requested_by),
    -- A refund that needs approval is APPROVED or REJECTED only with a decider; one that does not is approved at once.
    CONSTRAINT refunds_decided_by_someone CHECK (status = 'PENDING_APPROVAL' OR decided_by IS NOT NULL),
    CONSTRAINT refunds_small_not_pending CHECK (needs_second_approval OR status = 'APPROVED')
);
CREATE INDEX refunds_by_order ON refunds (order_id);
