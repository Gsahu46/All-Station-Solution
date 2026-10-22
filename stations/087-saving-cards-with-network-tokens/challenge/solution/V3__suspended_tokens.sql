-- The network can suspend a token (for example while the bank checks a fraud report) and resume it later.
ALTER TABLE saved_cards DROP CONSTRAINT saved_cards_status;
ALTER TABLE saved_cards ADD CONSTRAINT saved_cards_status CHECK (status IN ('active', 'suspended', 'deleted'));
