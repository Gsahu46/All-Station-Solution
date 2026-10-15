-- The code is the primary key: two links can never share one, whoever writes. A collision is refused, never merged.
CREATE TABLE links (
    code       VARCHAR(7)    NOT NULL,
    target_url VARCHAR(2048) NOT NULL,
    clicks     BIGINT        NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT links_pkey                PRIMARY KEY (code),
    CONSTRAINT links_code_base62         CHECK (code ~ '^[0-9A-Za-z]{7}$'),
    CONSTRAINT links_target_web          CHECK (target_url ~* '^https?://'),
    CONSTRAINT links_clicks_non_negative CHECK (clicks >= 0)
);
