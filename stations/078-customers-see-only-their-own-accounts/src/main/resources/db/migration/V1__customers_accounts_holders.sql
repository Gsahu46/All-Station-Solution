CREATE TABLE customers (
    id            bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT customers_pk PRIMARY KEY,
    email         text NOT NULL,
    name          text NOT NULL,
    password_hash text NOT NULL,
    CONSTRAINT customers_email_lower CHECK (email = lower(email)),
    CONSTRAINT customers_email_unique UNIQUE (email),
    CONSTRAINT customers_password_hash_shape CHECK (password_hash ~ '^\{bcrypt\}\$2[aby]\$(1[0-9]|2[0-9]|3[01])\$[./A-Za-z0-9]{53}$')
);

-- Account numbers count up, as at most banks: anyone can guess the next one. Guessing must get nobody anywhere.
CREATE TABLE accounts (
    id            bigint CONSTRAINT accounts_pk PRIMARY KEY,
    kind          text NOT NULL,
    name          text NOT NULL,
    balance_paise bigint NOT NULL,
    CONSTRAINT accounts_kind CHECK (kind IN ('savings', 'current')),
    CONSTRAINT accounts_balance_nonnegative CHECK (balance_paise >= 0)
);

-- Who may see which account. 'full': balance and statements. 'balance_only': the balance, nothing else
-- (a shop assistant checking the shop's account, say).
CREATE TABLE account_holders (
    account_id  bigint NOT NULL CONSTRAINT account_holders_account_fk REFERENCES accounts ON DELETE CASCADE,
    customer_id bigint NOT NULL CONSTRAINT account_holders_customer_fk REFERENCES customers ON DELETE CASCADE,
    access      text NOT NULL,
    CONSTRAINT account_holders_pk PRIMARY KEY (account_id, customer_id),
    CONSTRAINT account_holders_access CHECK (access IN ('full', 'balance_only'))
);
CREATE INDEX account_holders_by_customer ON account_holders (customer_id);

-- Statement lines. Credits positive, debits negative, in paise; written in the same transaction as the balance change.
CREATE TABLE transactions (
    id           bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT transactions_pk PRIMARY KEY,
    account_id   bigint NOT NULL CONSTRAINT transactions_account_fk REFERENCES accounts ON DELETE CASCADE,
    booked_on    date NOT NULL,
    description  text NOT NULL,
    amount_paise bigint NOT NULL,
    CONSTRAINT transactions_amount_nonzero CHECK (amount_paise <> 0),
    CONSTRAINT transactions_description_length CHECK (char_length(description) BETWEEN 1 AND 140)
);
CREATE INDEX transactions_by_account_date ON transactions (account_id, booked_on);
