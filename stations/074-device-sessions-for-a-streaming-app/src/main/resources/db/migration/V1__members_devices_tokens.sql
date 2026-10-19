CREATE TABLE members (
    id            bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT members_pk PRIMARY KEY,
    email         text NOT NULL,
    password_hash text NOT NULL,
    CONSTRAINT members_email_lower CHECK (email = lower(email)),
    CONSTRAINT members_email_unique UNIQUE (email),
    CONSTRAINT members_password_hash_shape CHECK (password_hash ~ '^\{bcrypt\}\$2[aby]\$(1[0-9]|2[0-9]|3[01])\$[./A-Za-z0-9]{53}$')
);

-- One row per signed-in device. Revoking it ends the device's refresh tokens and, through the access-token check,
-- its access tokens at once.
CREATE TABLE device_sessions (
    id             uuid CONSTRAINT device_sessions_pk PRIMARY KEY,
    member_id      bigint NOT NULL CONSTRAINT device_sessions_member_fk REFERENCES members ON DELETE CASCADE,
    device_name    text NOT NULL,
    device_type    text NOT NULL,
    created_at     timestamptz NOT NULL,
    last_used_at   timestamptz NOT NULL,
    revoked_at     timestamptz,
    revoked_reason text,
    CONSTRAINT device_sessions_name_length CHECK (char_length(device_name) BETWEEN 1 AND 60),
    CONSTRAINT device_sessions_type CHECK (device_type IN ('phone', 'tv', 'web')),
    CONSTRAINT device_sessions_revoked_reason CHECK (revoked_reason IN ('logout', 'removed', 'reuse')),
    CONSTRAINT device_sessions_revoked_with_reason CHECK ((revoked_at IS NULL) = (revoked_reason IS NULL))
);
CREATE INDEX device_sessions_active_by_member ON device_sessions (member_id) WHERE revoked_at IS NULL;

-- Only the SHA-256 of each refresh token is stored. A used token stays, marked, so a second use is recognised.
CREATE TABLE refresh_tokens (
    token_hash char(64) CONSTRAINT refresh_tokens_pk PRIMARY KEY,
    session_id uuid NOT NULL CONSTRAINT refresh_tokens_session_fk REFERENCES device_sessions ON DELETE CASCADE,
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    used_at    timestamptz,
    CONSTRAINT refresh_tokens_hash_shape CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT refresh_tokens_expiry CHECK (expires_at > created_at AND expires_at <= created_at + interval '30 days'),
    CONSTRAINT refresh_tokens_used_in_time CHECK (used_at IS NULL OR used_at >= created_at)
);
-- Rotation as a rule: a device has at most one refresh token that has not been used.
CREATE UNIQUE INDEX refresh_tokens_one_live_per_session ON refresh_tokens (session_id) WHERE used_at IS NULL;
