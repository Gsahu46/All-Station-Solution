-- Where each merchant wants to hear about its payments. The secret signs every request (it cannot be hashed:
-- we need it to sign). shortcut: stored as is; encrypt it with a key from a KMS in production.
CREATE TABLE webhook_endpoints (
    id          bigserial PRIMARY KEY,
    merchant_id bigint      NOT NULL,
    url         text        NOT NULL,
    secret      text        NOT NULL,
    created_at  timestamptz NOT NULL,
    CONSTRAINT endpoints_url_once_per_merchant UNIQUE (merchant_id, url),
    CONSTRAINT endpoints_url_http CHECK (url ~ '^https?://[^/@]+' AND length(url) <= 2000),
    CONSTRAINT endpoints_secret_format CHECK (secret ~ '^whsec_[A-Za-z0-9+/]{32}$')
);

-- What happened, written once. A payment is captured once, so it makes one event, however often it is reported.
CREATE TABLE events (
    id           uuid        PRIMARY KEY,
    merchant_id  bigint      NOT NULL,
    type         text        NOT NULL,
    object_ref   text        NOT NULL,
    amount_paise bigint      NOT NULL,
    payload      text        NOT NULL,   -- the exact bytes we sign and send, not re-encoded JSON
    created_at   timestamptz NOT NULL,
    CONSTRAINT events_once_per_object UNIQUE (merchant_id, type, object_ref),
    CONSTRAINT events_type CHECK (type IN ('payment.captured')),
    CONSTRAINT events_amount_positive CHECK (amount_paise > 0)
);

-- One event to one endpoint: the outbox the dispatcher works through.
CREATE TABLE deliveries (
    id               bigserial   PRIMARY KEY,
    event_id         uuid        NOT NULL REFERENCES events,
    endpoint_id      bigint      NOT NULL REFERENCES webhook_endpoints,
    status           text        NOT NULL DEFAULT 'PENDING',
    attempts         int         NOT NULL DEFAULT 0,
    next_attempt_at  timestamptz,
    last_status_code int,
    last_error       text,
    delivered_at     timestamptz,
    CONSTRAINT deliveries_once_per_endpoint UNIQUE (event_id, endpoint_id),
    CONSTRAINT deliveries_status CHECK (status IN ('PENDING', 'DELIVERED', 'FAILED')),
    CONSTRAINT deliveries_attempts_range CHECK (attempts BETWEEN 0 AND 8),
    CONSTRAINT deliveries_pending_has_next CHECK ((status = 'PENDING') = (next_attempt_at IS NOT NULL)),
    CONSTRAINT deliveries_delivered_has_time CHECK ((status = 'DELIVERED') = (delivered_at IS NOT NULL))
);
CREATE INDEX deliveries_due ON deliveries (next_attempt_at) WHERE status = 'PENDING';

-- Every try, kept for the merchant to read: when, what came back, how long it took.
CREATE TABLE delivery_attempts (
    id           bigserial   PRIMARY KEY,
    delivery_id  bigint      NOT NULL REFERENCES deliveries,
    attempted_at timestamptz NOT NULL,
    status_code  int,
    error        text,
    duration_ms  int         NOT NULL,
    CONSTRAINT attempts_duration_positive CHECK (duration_ms >= 0)
);
CREATE INDEX delivery_attempts_by_delivery ON delivery_attempts (delivery_id, id);
