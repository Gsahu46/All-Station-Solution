-- Challenges 1 and 2: a paid hold is CONFIRMED, a hold the guest gave up is CANCELLED.
ALTER TABLE holds DROP CONSTRAINT holds_status,
    ADD CONSTRAINT holds_status CHECK (status IN ('HELD', 'EXPIRED', 'CONFIRMED', 'CANCELLED'));
