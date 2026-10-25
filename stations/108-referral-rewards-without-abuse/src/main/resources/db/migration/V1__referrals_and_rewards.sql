-- Customers, referrals, rewards, and the outbox of wallet credits. Money in paise.
CREATE TABLE customers (
    id            BIGSERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    phone         TEXT NOT NULL CONSTRAINT customers_phone_unique UNIQUE,   -- normalised: +91 and 10 digits
    device_id     TEXT NOT NULL,
    referral_code TEXT NOT NULL CONSTRAINT customers_code_unique UNIQUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX customers_by_device ON customers (device_id);

CREATE TABLE referrals (
    id          BIGSERIAL PRIMARY KEY,
    referrer_id BIGINT NOT NULL REFERENCES customers (id),
    -- A new customer is referred once, by one person.
    referee_id  BIGINT NOT NULL REFERENCES customers (id) CONSTRAINT referrals_one_per_referee UNIQUE,
    -- The device the new customer signed up on: one referral per device, ever. This is what stops one person
    -- referring himself with sixty new phone numbers.
    device_id   TEXT   NOT NULL CONSTRAINT referrals_one_per_device UNIQUE,
    status      TEXT   NOT NULL CONSTRAINT referrals_status CHECK (status IN ('PENDING', 'REWARDED')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT referrals_not_self CHECK (referrer_id <> referee_id)
);

CREATE TABLE rewards (
    id           BIGSERIAL PRIMARY KEY,
    -- One reward per referral, and one per qualifying order: a second delivery of the same event finds it taken.
    referral_id  BIGINT NOT NULL REFERENCES referrals (id) CONSTRAINT rewards_one_per_referral UNIQUE,
    order_id     BIGINT NOT NULL CONSTRAINT rewards_one_per_order UNIQUE,
    referrer_id  BIGINT NOT NULL REFERENCES customers (id),
    amount_paise BIGINT NOT NULL CONSTRAINT rewards_amount_positive CHECK (amount_paise > 0),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Wallet credits waiting to be sent, written in the same transaction as the reward (a transactional outbox).
CREATE TABLE wallet_outbox (
    id              BIGSERIAL PRIMARY KEY,
    reward_id       BIGINT NOT NULL REFERENCES rewards (id) CONSTRAINT wallet_outbox_one_per_reward UNIQUE,
    status          TEXT   NOT NULL DEFAULT 'PENDING' CONSTRAINT wallet_outbox_status CHECK (status IN ('PENDING', 'SENT', 'DEAD')),
    attempts        INT    NOT NULL DEFAULT 0 CONSTRAINT wallet_outbox_attempts CHECK (attempts >= 0),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    claimed_until   TIMESTAMPTZ,
    last_error      TEXT,
    sent_at         TIMESTAMPTZ
);
CREATE INDEX wallet_outbox_due ON wallet_outbox (next_attempt_at) WHERE status = 'PENDING';
