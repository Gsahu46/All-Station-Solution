-- A tip for the rider, in paise. Existing orders get 0.
ALTER TABLE orders ADD COLUMN tip_paise BIGINT NOT NULL DEFAULT 0;
ALTER TABLE orders ADD CONSTRAINT orders_tip_range CHECK (tip_paise BETWEEN 0 AND 50000);
