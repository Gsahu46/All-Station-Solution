-- A reversed top-up stays on record, marked, and no longer counts towards the day's limit.
ALTER TABLE top_ups ADD COLUMN reversed_at timestamptz;

CREATE OR REPLACE FUNCTION top_ups_within_daily_limit() RETURNS trigger AS $$
DECLARE
    day_start timestamptz := date_trunc('day', NEW.created_at AT TIME ZONE 'Asia/Kolkata') AT TIME ZONE 'Asia/Kolkata';
    total     bigint;
    day_limit bigint;
BEGIN
    IF NEW.reversed_at IS NOT NULL THEN
        RETURN NEW;
    END IF;
    SELECT t.daily_limit_paise INTO day_limit FROM wallets w JOIN kyc_tiers t ON t.tier = w.tier WHERE w.id = NEW.wallet_id FOR UPDATE OF w;
    SELECT coalesce(sum(amount_paise), 0) INTO total FROM top_ups
    WHERE wallet_id = NEW.wallet_id AND reversed_at IS NULL AND created_at >= day_start AND created_at < day_start + interval '1 day';
    IF total + NEW.amount_paise > day_limit THEN
        RAISE EXCEPTION 'top_ups_within_daily_limit: wallet % would reach % paise on %, limit %', NEW.wallet_id, total + NEW.amount_paise, day_start, day_limit
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;
