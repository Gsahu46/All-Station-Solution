-- Challenge 2: failed sign-ins in a row, and until when the account is locked.
ALTER TABLE candidates
    ADD COLUMN failed_sign_ins INTEGER NOT NULL DEFAULT 0 CONSTRAINT candidates_failed_sign_ins_range CHECK (failed_sign_ins BETWEEN 0 AND 100),
    ADD COLUMN locked_until TIMESTAMPTZ;
