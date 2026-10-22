-- A new provider is a new allowed name; existing payments keep the name of the provider that took them.
ALTER TABLE payments DROP CONSTRAINT payments_known_provider;
ALTER TABLE payments ADD CONSTRAINT payments_known_provider CHECK (provider IN ('sim-alpha', 'sim-beta', 'sim-gamma'));
