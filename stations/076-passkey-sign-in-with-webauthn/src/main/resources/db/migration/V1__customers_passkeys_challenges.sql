CREATE TABLE customers (
    id             bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT customers_pk PRIMARY KEY,
    email          text NOT NULL,
    name           text NOT NULL,
    -- WebAuthn's user.id: random bytes, never the email, so a passkey reveals nothing about who it belongs to.
    user_handle    bytea NOT NULL,
    password_hash  text NOT NULL,
    totp_secret    bytea NOT NULL,
    -- The last 30-second step whose code was accepted: a code works once.
    totp_last_step bigint,
    balance_paise  bigint NOT NULL,
    CONSTRAINT customers_email_lower CHECK (email = lower(email)),
    CONSTRAINT customers_email_unique UNIQUE (email),
    CONSTRAINT customers_user_handle_unique UNIQUE (user_handle),
    CONSTRAINT customers_user_handle_length CHECK (octet_length(user_handle) = 32),
    CONSTRAINT customers_password_hash_shape CHECK (password_hash ~ '^\{bcrypt\}\$2[aby]\$(1[0-9]|2[0-9]|3[01])\$[./A-Za-z0-9]{53}$'),
    CONSTRAINT customers_totp_secret_length CHECK (octet_length(totp_secret) >= 20),
    CONSTRAINT customers_balance_nonnegative CHECK (balance_paise >= 0)
);

CREATE TABLE passkeys (
    credential_id            bytea CONSTRAINT passkeys_pk PRIMARY KEY,
    customer_id              bigint NOT NULL CONSTRAINT passkeys_customer_fk REFERENCES customers ON DELETE CASCADE,
    -- The authenticator's AAGUID, the credential id and the COSE public key, as the authenticator sent them.
    attested_credential_data bytea NOT NULL,
    sign_count               bigint NOT NULL,
    label                    text NOT NULL,
    created_at               timestamptz NOT NULL,
    last_used_at             timestamptz,
    CONSTRAINT passkeys_credential_id_length CHECK (octet_length(credential_id) BETWEEN 16 AND 1023),
    CONSTRAINT passkeys_sign_count_range CHECK (sign_count BETWEEN 0 AND 4294967295),
    CONSTRAINT passkeys_label_length CHECK (char_length(label) BETWEEN 1 AND 60)
);

-- Every ceremony starts with a random challenge from the server; each is good once, for 5 minutes.
CREATE TABLE webauthn_challenges (
    challenge   bytea CONSTRAINT webauthn_challenges_pk PRIMARY KEY,
    purpose     text NOT NULL,
    customer_id bigint CONSTRAINT webauthn_challenges_customer_fk REFERENCES customers ON DELETE CASCADE,
    created_at  timestamptz NOT NULL,
    expires_at  timestamptz NOT NULL,
    used_at     timestamptz,
    CONSTRAINT webauthn_challenges_length CHECK (octet_length(challenge) = 32),
    CONSTRAINT webauthn_challenges_purpose CHECK (purpose IN ('registration', 'authentication')),
    CONSTRAINT webauthn_challenges_registration_has_customer CHECK (purpose <> 'registration' OR customer_id IS NOT NULL),
    CONSTRAINT webauthn_challenges_expiry CHECK (expires_at > created_at AND expires_at <= created_at + interval '5 minutes'),
    CONSTRAINT webauthn_challenges_used_in_time CHECK (used_at IS NULL OR used_at >= created_at)
);
