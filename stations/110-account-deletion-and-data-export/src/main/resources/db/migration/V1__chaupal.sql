-- Chaupal, a community app. Every table that holds personal data is listed in PersonalData.java with what happens to
-- it when a person deletes their account; PersonalDataInventoryTest fails the build when a table is not listed.
CREATE TABLE users (
    id                    BIGSERIAL PRIMARY KEY,
    login                 TEXT UNIQUE,
    password_hash         TEXT,
    role                  TEXT NOT NULL DEFAULT 'MEMBER' CONSTRAINT users_role CHECK (role IN ('MEMBER', 'SUPPORT')),
    name                  TEXT,
    phone                 TEXT CONSTRAINT users_phone_unique UNIQUE,
    email                 TEXT,
    status                TEXT NOT NULL DEFAULT 'ACTIVE' CONSTRAINT users_status CHECK (status IN ('ACTIVE', 'DELETION_REQUESTED', 'DELETED')),
    deletion_requested_at TIMESTAMPTZ,
    deleted_at            TIMESTAMPTZ,
    -- The id stays, so others' rows that point at it stay valid; nothing that identifies the person does.
    CONSTRAINT users_deleted_holds_nothing CHECK (status <> 'DELETED'
        OR (login IS NULL AND password_hash IS NULL AND name IS NULL AND phone IS NULL AND email IS NULL AND deleted_at IS NOT NULL))
);

CREATE TABLE profiles (
    user_id       BIGINT PRIMARY KEY REFERENCES users (id),
    bio           TEXT,
    city          TEXT,
    date_of_birth DATE
);

CREATE TABLE posts (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users (id),
    body       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE comments (
    id         BIGSERIAL PRIMARY KEY,
    post_id    BIGINT NOT NULL REFERENCES posts (id) ON DELETE CASCADE,
    user_id    BIGINT NOT NULL REFERENCES users (id),
    body       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tax invoices for paid memberships: the law says how long they must be kept, deletion or not.
CREATE TABLE invoices (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users (id),
    buyer_name   TEXT NOT NULL,
    buyer_phone  TEXT NOT NULL,
    amount_paise BIGINT NOT NULL CONSTRAINT invoices_amount_positive CHECK (amount_paise > 0),
    issued_on    DATE NOT NULL,
    retain_until DATE NOT NULL,
    CONSTRAINT invoices_retained_after_issue CHECK (retain_until > issued_on)
);

-- Sign-in records, kept for security for 180 days (demo rule; see the Production tab).
CREATE TABLE login_events (
    id      BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users (id),
    ip      TEXT NOT NULL,
    at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Keyed by phone, not by user: a lookup by user id never finds these.
CREATE TABLE otp_requests (
    id        BIGSERIAL PRIMARY KEY,
    phone     TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Other members' address books: this person's number may be in someone else's upload.
CREATE TABLE contact_uploads (
    id            BIGSERIAL PRIMARY KEY,
    uploader_id   BIGINT NOT NULL REFERENCES users (id),
    contact_name  TEXT,
    contact_phone TEXT NOT NULL
);

CREATE TABLE support_tickets (
    id      BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users (id),
    phone   TEXT,
    message TEXT NOT NULL
);

CREATE TABLE notification_outbox (
    id     BIGSERIAL PRIMARY KEY,
    phone  TEXT NOT NULL,
    text   TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING'
);

CREATE TABLE data_exports (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users (id),
    status       TEXT NOT NULL DEFAULT 'PENDING' CONSTRAINT data_exports_status CHECK (status IN ('PENDING', 'READY')),
    content      JSONB,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ready_at     TIMESTAMPTZ,
    CONSTRAINT data_exports_ready_has_content CHECK (status <> 'READY' OR content IS NOT NULL)
);

-- The record of each erasure, with no personal data: proof it was done, and the list to re-apply after a backup
-- is restored. Demo rule: done within 90 days of the request.
CREATE TABLE erasures (
    user_id      BIGINT PRIMARY KEY REFERENCES users (id),
    requested_at TIMESTAMPTZ NOT NULL,
    due_by       TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    CONSTRAINT erasures_within_90_days CHECK (due_by <= requested_at + interval '90 days')
);
