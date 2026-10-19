CREATE TABLE candidates (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email         VARCHAR(254) NOT NULL CONSTRAINT candidates_email_lower CHECK (email = lower(email)),
    full_name     VARCHAR(100) NOT NULL,
    -- Only a bcrypt hash (cost 10 or more), or a legacy {MD5} hash from the old system that is replaced at the next sign-in.
    -- Plain text and bare digests are refused, whoever writes the row.
    password_hash VARCHAR(100) NOT NULL CONSTRAINT candidates_password_hash_shape
                  CHECK (password_hash ~ '^\{bcrypt\}\$2[aby]\$(1[0-9]|2[0-9]|3[01])\$[./A-Za-z0-9]{53}$' OR password_hash ~ '^\{MD5\}[0-9a-f]{32}$'),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT candidates_email_unique UNIQUE (email)
);
