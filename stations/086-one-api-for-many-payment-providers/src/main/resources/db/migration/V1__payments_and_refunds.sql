CREATE TABLE payments (
    id             bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT payments_pk PRIMARY KEY,
    order_id       text NOT NULL,
    amount_paise   bigint NOT NULL,
    provider       text NOT NULL,
    status         text NOT NULL,
    provider_ref   text,
    decline_reason text,
    refunded_paise bigint NOT NULL DEFAULT 0,
    created_at     timestamptz NOT NULL DEFAULT now(),
    -- One payment per order, whoever retries: the replay rule.
    CONSTRAINT payments_order_once UNIQUE (order_id),
    CONSTRAINT payments_order_shape CHECK (order_id ~ '^[A-Z0-9-]{3,40}$'),
    CONSTRAINT payments_amount_positive CHECK (amount_paise > 0),
    CONSTRAINT payments_known_provider CHECK (provider IN ('sim-alpha', 'sim-beta')),
    -- pending: being sent; unknown: a provider may have charged and could not say; failed: no provider was reached.
    CONSTRAINT payments_status CHECK (status IN ('pending', 'succeeded', 'declined', 'unknown', 'failed')),
    CONSTRAINT payments_succeeded_has_ref CHECK (status <> 'succeeded' OR provider_ref IS NOT NULL),
    CONSTRAINT payments_declined_has_reason CHECK ((status = 'declined') = (decline_reason IS NOT NULL)),
    CONSTRAINT payments_refunds_within_amount CHECK (refunded_paise BETWEEN 0 AND amount_paise),
    CONSTRAINT payments_refunds_only_when_paid CHECK (refunded_paise = 0 OR status = 'succeeded')
);

CREATE TABLE refunds (
    id           bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT refunds_pk PRIMARY KEY,
    payment_id   bigint NOT NULL CONSTRAINT refunds_payment_fk REFERENCES payments,
    amount_paise bigint NOT NULL,
    status       text NOT NULL,
    provider_ref text,
    created_at   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT refunds_amount_positive CHECK (amount_paise > 0),
    CONSTRAINT refunds_status CHECK (status IN ('requested', 'succeeded', 'failed')),
    CONSTRAINT refunds_succeeded_has_ref CHECK (status <> 'succeeded' OR provider_ref IS NOT NULL)
);
