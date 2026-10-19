CREATE TABLE candidates (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email         VARCHAR(254) NOT NULL CONSTRAINT candidates_email_lower CHECK (email = lower(email)),
    full_name     VARCHAR(100) NOT NULL,
    password_hash VARCHAR(100) NOT NULL CONSTRAINT candidates_password_hash_shape
                  CHECK (password_hash ~ '^\{bcrypt\}\$2[aby]\$(1[0-9]|2[0-9]|3[01])\$[./A-Za-z0-9]{53}$'),
    status        VARCHAR(10)  NOT NULL DEFAULT 'ACTIVE' CONSTRAINT candidates_status_known CHECK (status IN ('ACTIVE', 'SUSPENDED')),
    CONSTRAINT candidates_email_unique UNIQUE (email)
);

-- Only a SHA-256 of each token is kept: a copy of this table cannot be used to reset anyone's password.
-- (A fast hash is right here, unlike for passwords: the token is 256 random bits, not something a person chose.)
CREATE TABLE password_resets (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    candidate_id BIGINT      NOT NULL CONSTRAINT password_resets_candidate_fk REFERENCES candidates (id) ON DELETE CASCADE,
    token_hash   CHAR(64)    NOT NULL CONSTRAINT password_resets_token_hash_unique UNIQUE
                             CONSTRAINT password_resets_token_hash_shape CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    created_at   TIMESTAMPTZ NOT NULL,
    expires_at   TIMESTAMPTZ NOT NULL,
    used_at      TIMESTAMPTZ,
    CONSTRAINT password_resets_expiry CHECK (expires_at > created_at AND expires_at <= created_at + interval '1 hour'),
    CONSTRAINT password_resets_used_in_time CHECK (used_at IS NULL OR (used_at >= created_at AND used_at < expires_at))
);
CREATE INDEX password_resets_candidate ON password_resets (candidate_id);

-- Simulated email: a row is written here; nothing is sent.
CREATE TABLE outbox_emails (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    to_email   VARCHAR(254) NOT NULL,
    subject    VARCHAR(200) NOT NULL,
    body       TEXT         NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL
);
