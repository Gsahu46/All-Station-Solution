-- One counter row per outlet per day. The next token is taken by one atomic upsert; the row lock it takes makes
-- parallel orders at one outlet wait for each other for a moment, and never share a value.
CREATE TABLE daily_tokens (
    outlet_id  VARCHAR(5) NOT NULL,
    day        DATE       NOT NULL,
    last_token INT        NOT NULL,
    PRIMARY KEY (outlet_id, day),
    CONSTRAINT daily_tokens_positive CHECK (last_token > 0)
);
ALTER TABLE orders ADD COLUMN token INT;   -- empty for orders placed before tokens existed
