-- Challenge 1: exports expire. Challenge 2: when the inactivity notice was sent.
ALTER TABLE data_exports DROP CONSTRAINT data_exports_status;
ALTER TABLE data_exports ADD CONSTRAINT data_exports_status CHECK (status IN ('PENDING', 'READY', 'EXPIRED'));
ALTER TABLE users ADD COLUMN inactivity_notice_at TIMESTAMPTZ;
