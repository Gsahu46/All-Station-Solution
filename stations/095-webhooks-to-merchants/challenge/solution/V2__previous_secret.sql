-- Challenge 2: after a rotation the old secret keeps signing for a while, so the merchant can switch without
-- rejecting a payment.
ALTER TABLE webhook_endpoints
    ADD COLUMN previous_secret       text,
    ADD COLUMN previous_secret_until timestamptz,
    ADD CONSTRAINT endpoints_previous_secret_pair CHECK ((previous_secret IS NULL) = (previous_secret_until IS NULL)),
    ADD CONSTRAINT endpoints_previous_secret_format CHECK (previous_secret ~ '^whsec_[A-Za-z0-9+/]{32}$');
