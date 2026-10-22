-- Demo rules, not RBI's: how much a wallet may be topped up per day (IST), by KYC tier.
CREATE TABLE kyc_tiers (
    tier              text CONSTRAINT kyc_tiers_pk PRIMARY KEY,
    daily_limit_paise bigint NOT NULL,
    CONSTRAINT kyc_tiers_limit_positive CHECK (daily_limit_paise > 0)
);

CREATE TABLE wallets (
    id            bigint CONSTRAINT wallets_pk PRIMARY KEY,
    owner         text NOT NULL,
    tier          text NOT NULL CONSTRAINT wallets_tier_fk REFERENCES kyc_tiers,
    balance_paise bigint NOT NULL DEFAULT 0,
    CONSTRAINT wallets_balance_not_negative CHECK (balance_paise >= 0)
);

CREATE TABLE top_ups (
    id           bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT top_ups_pk PRIMARY KEY,
    wallet_id    bigint NOT NULL CONSTRAINT top_ups_wallet_fk REFERENCES wallets,
    amount_paise bigint NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT top_ups_amount_positive CHECK (amount_paise > 0)
);
CREATE INDEX top_ups_wallet_time ON top_ups (wallet_id, created_at);

-- The rule for every writer: a wallet's top-ups on one IST day stay within its tier's daily limit. It spans rows, so it
-- is a trigger. It locks the wallet row first, like the application does, so two writers cannot both sum the old total.
-- Its limits: it watches inserts only (changing an amount or a wallet's tier later is not checked), and its day is IST.
CREATE FUNCTION top_ups_within_daily_limit() RETURNS trigger AS $$
DECLARE
    day_start timestamptz := date_trunc('day', NEW.created_at AT TIME ZONE 'Asia/Kolkata') AT TIME ZONE 'Asia/Kolkata';
    total     bigint;
    day_limit bigint;
BEGIN
    SELECT t.daily_limit_paise INTO day_limit FROM wallets w JOIN kyc_tiers t ON t.tier = w.tier WHERE w.id = NEW.wallet_id FOR UPDATE OF w;
    SELECT coalesce(sum(amount_paise), 0) INTO total FROM top_ups
    WHERE wallet_id = NEW.wallet_id AND created_at >= day_start AND created_at < day_start + interval '1 day';
    IF total + NEW.amount_paise > day_limit THEN
        RAISE EXCEPTION 'top_ups_within_daily_limit: wallet % would reach % paise on %, limit %', NEW.wallet_id, total + NEW.amount_paise, day_start, day_limit
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER top_ups_within_daily_limit BEFORE INSERT ON top_ups FOR EACH ROW EXECUTE FUNCTION top_ups_within_daily_limit();
