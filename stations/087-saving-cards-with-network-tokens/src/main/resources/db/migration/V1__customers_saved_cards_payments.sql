CREATE TABLE customers (
    id       bigint CONSTRAINT customers_pk PRIMARY KEY,
    username text NOT NULL CONSTRAINT customers_username_unique UNIQUE
);

-- What a merchant may keep: the token service's reference, and what the customer needs to recognise the card.
-- No card number, no CVV, ever. The shape rules make a card number impossible to store in any of these columns.
CREATE TABLE saved_cards (
    id           bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT saved_cards_pk PRIMARY KEY,
    customer_id  bigint NOT NULL CONSTRAINT saved_cards_customer_fk REFERENCES customers,
    token_ref    text NOT NULL CONSTRAINT saved_cards_token_unique UNIQUE,
    network      text NOT NULL,
    last4        text NOT NULL,
    expiry_month smallint NOT NULL,
    expiry_year  smallint NOT NULL,
    status       text NOT NULL DEFAULT 'active',
    consent_at   timestamptz NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT saved_cards_token_shape CHECK (token_ref ~ '^tkn_[a-z]{20}$'),
    CONSTRAINT saved_cards_last4_shape CHECK (last4 ~ '^[0-9]{4}$'),
    CONSTRAINT saved_cards_network CHECK (network IN ('VISA', 'MASTERCARD', 'RUPAY')),
    CONSTRAINT saved_cards_expiry CHECK (expiry_month BETWEEN 1 AND 12 AND expiry_year BETWEEN 2000 AND 2100),
    CONSTRAINT saved_cards_status CHECK (status IN ('active', 'deleted'))
);

CREATE TABLE payments (
    id            bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT payments_pk PRIMARY KEY,
    customer_id   bigint NOT NULL CONSTRAINT payments_customer_fk REFERENCES customers,
    saved_card_id bigint NOT NULL CONSTRAINT payments_saved_card_fk REFERENCES saved_cards,
    order_id      text NOT NULL CONSTRAINT payments_order_once UNIQUE,
    amount_paise  bigint NOT NULL,
    status        text NOT NULL,
    network_ref   text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT payments_amount_positive CHECK (amount_paise > 0),
    -- pending: sent to the network; failed: the network refused the token, nothing was charged.
    CONSTRAINT payments_status CHECK (status IN ('pending', 'succeeded', 'declined', 'failed')),
    CONSTRAINT payments_succeeded_has_ref CHECK (status <> 'succeeded' OR network_ref IS NOT NULL)
);
