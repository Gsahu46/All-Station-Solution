ALTER TABLE holds DROP CONSTRAINT holds_status;
ALTER TABLE holds ADD CONSTRAINT holds_status CHECK (status IN ('held', 'confirmed', 'refunded', 'released', 'expired'));
ALTER TABLE holds DROP CONSTRAINT holds_confirmed_paid;
ALTER TABLE holds ADD CONSTRAINT holds_confirmed_paid CHECK (status NOT IN ('confirmed', 'refunded') OR payment_ref IS NOT NULL);
