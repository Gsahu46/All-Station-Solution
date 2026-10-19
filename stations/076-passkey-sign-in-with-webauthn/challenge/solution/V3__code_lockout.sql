ALTER TABLE customers ADD COLUMN failed_codes integer NOT NULL DEFAULT 0;
ALTER TABLE customers ADD COLUMN codes_locked_until timestamptz;
ALTER TABLE customers ADD CONSTRAINT customers_failed_codes_range CHECK (failed_codes BETWEEN 0 AND 5);
